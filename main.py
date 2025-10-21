from fastapi import FastAPI
import os, datetime as dt
import httpx
from typing import List, Dict, Any, Optional
from collections import deque
import urllib.parse

app = FastAPI(title="Hedge Fund – minimal")

# ======================================================================
# Helpers / env
# ======================================================================

def getenv(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name, default)
    return v.strip() if isinstance(v, str) else v

def getenv_int(name: str, default: int) -> int:
    try:
        return int(str(getenv(name, str(default))))
    except Exception:
        return default

def getenv_list(name: str, default: str = "") -> List[str]:
    raw = getenv(name, default) or ""
    return [x.strip().lower() for x in raw.split(",") if x.strip()]

# ======================================================================
# Telegram
# ======================================================================

async def send_telegram(text: str) -> bool:
    token = getenv("TELEGRAM_BOT_TOKEN")
    chat_id = getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    timeout = httpx.Timeout(10.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as cli:
        r = await cli.post(url, json=payload)
        return r.status_code == 200

# ======================================================================
# Marketaux hívás
# ======================================================================

async def fetch_marketaux(limit: int) -> Dict[str, Any]:
    base = "https://api.marketaux.com/v1/news/all"
    token = getenv("MARKETAUX_API_TOKEN")
    symbols = getenv("NEWS_SYMBOLS", "")
    search = getenv("NEWS_SEARCH", "")
    language = getenv("NEWS_LANGUAGE", "en")
    since = getenv("NEWS_SINCE", "24h")  # pl. 24h, 7d, 2025-10-01

    if not token:
        return {"detail": {"marketaux_error": {"code": "missing_token", "message": "MARKETAUX_API_TOKEN is empty"}}}

    # published_after: ha relatív értéket adtál meg (pl. 24h), konvertáljuk ISO időbélyegre
    def since_to_iso(v: str) -> Optional[str]:
        try:
            v = (v or "").strip().lower()
            if not v:
                return None
            if v.endswith("h"):
                hours = int(v[:-1])
                t = dt.datetime.utcnow() - dt.timedelta(hours=hours)
                return t.replace(microsecond=0).isoformat() + "Z"
            if v.endswith("d"):
                days = int(v[:-1])
                t = dt.datetime.utcnow() - dt.timedelta(days=days)
                return t.replace(microsecond=0).isoformat() + "Z"
            # ha konkrét dátum/idő jön, hagyjuk a felhasználóra (Marketaux ISO-t vár)
            return v
        except Exception:
            return None

    # biztonság: 1..5
    safe_limit = max(1, min(int(limit or 1), 5))

    params = {
        "api_token": token,
        "limit": str(safe_limit),
        "language": language,
        "filter_entities": "true",
    }

    pa = since_to_iso(since)
    if pa:
        params["published_after"] = pa
    if symbols:
        params["symbols"] = symbols
    if search:
        params["search"] = search

    timeout = httpx.Timeout(15.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as cli:
        r = await cli.get(base, params=params)
        try:
            data = r.json()
        except Exception:
            data = {"status_code": r.status_code, "text": r.text}

    # Marketaux hiba átadása (pl. invalid_api_token)
    if isinstance(data, dict) and "error" in data:
        return {"detail": {"marketaux_error": data["error"]}}
    return data

# ======================================================================
# Dedupe + szűrés (URL normalizálás, domain tiltás, életkor)
# ======================================================================

# Memóriás dedupe az utoljára küldött linkekre
LAST_SENT = deque(maxlen=100)
LAST_SENT_SET = set()

def _norm_url(u: str) -> str:
    """Normalizált URL az ismétlődések kiszűrésére."""
    try:
        if not u:
            return ""
        p = urllib.parse.urlsplit(u)
        # csak a lényeges query paramétereket tartsuk meg
        q = urllib.parse.parse_qsl(p.query, keep_blank_values=False)
        keep = [(k, v) for (k, v) in q if k.lower() in {"utm_source", "utm_medium", "utm_campaign"}]
        new_q = urllib.parse.urlencode(keep, doseq=True)
        cleaned = urllib.parse.urlunsplit((p.scheme, p.netloc.lower(), p.path, new_q, ""))  # fragment drop
        return cleaned
    except Exception:
        return (u or "").strip()

def _blocked_domain(u: str) -> bool:
    """Domain blokkolás env alapján."""
    blocked = set(getenv_list("NEWS_BLOCKED_DOMAINS", ""))
    if not blocked:
        return False
    try:
        netloc = urllib.parse.urlsplit(u).netloc.lower()
        return any(netloc.endswith(dom) for dom in blocked)
    except Exception:
        return False

def _parse_dt(s: str) -> Optional[dt.datetime]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        # Marketaux pl. "2025-10-21T17:55:15.000000Z"
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None

def _age_ok(published_at: str) -> bool:
    """Ne küldjünk túl régi cikket. NEWS_MAX_AGE_HOURS (alap: 48)."""
    max_h = getenv_int("NEWS_MAX_AGE_HOURS", 48)
    t = _parse_dt(published_at)
    if not t:
        return True  # ha nincs időbélyeg, nem dobjuk ki
    now = dt.datetime.now(dt.timezone.utc)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    age_h = (now - t).total_seconds() / 3600.0
    return age_h <= max_h

def _mark_sent(url: str) -> None:
    u = _norm_url(url)
    if not u:
        return
    if u in LAST_SENT_SET:
        return
    LAST_SENT.append(u)
    LAST_SENT_SET.add(u)
    # ha túlnőtt a set, szinkronizáljuk
    if len(LAST_SENT_SET) > LAST_SENT.maxlen:
        LAST_SENT_SET.clear()
        LAST_SENT_SET.update(LAST_SENT)

# ======================================================================
# Formázás
# ======================================================================

def format_items_to_message(items: List[Dict[str, Any]]) -> str:
    lines = []
    for it in items[:3]:  # max 3 elem üzenetben
        title = (it.get("title") or "").strip()
        src = it.get("source", "")
        url = it.get("url", "")
        when = (it.get("published_at") or "")[:19].replace("T", " ")
        lines.append(f"• {title}\n  ({src} • {when})\n  {url}")
    return "🗞  Latest headlines:\n" + "\n\n".join(lines)

# ======================================================================
# Minimal endpoints
# ======================================================================

@app.get("/")
def root():
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/status")
def status():
    return {
        "status": "running",
        "telegram_bot": bool(getenv("TELEGRAM_BOT_TOKEN")),
        "chat_id_set": bool(getenv("TELEGRAM_CHAT_ID")),
        "marketaux_key": bool(getenv("MARKETAUX_API_TOKEN")),
        "blocked_domains": getenv_list("NEWS_BLOCKED_DOMAINS"),
        "max_age_hours": getenv_int("NEWS_MAX_AGE_HOURS", 48),
        "cache_size": len(LAST_SENT),
    }

@app.post("/test/telegram")
async def test_telegram():
    ok = await send_telegram("✅ Telegram test OK")
    return {"ok": ok}

# ======================================================================
# NEW: /news/auto  (duplikátum-, domain-, életkor-szűrés + limit védelem)
# ======================================================================

@app.get("/news/auto")
async def news_auto(limit: int = 1):
    """
    Egyszerű automata Marketaux hírlehívás az env változókkal.
    Param: limit 1..5 (alap: 1).
    Szűrés: duplikált URL, tiltott domain, túl régi cikkek (NEWS_MAX_AGE_HOURS).
    """
    data = await fetch_marketaux(limit)

    # ha Marketaux hibát jelez
    if isinstance(data, dict) and "detail" in data and "marketaux_error" in data["detail"]:
        return data

    # kinyerjük a listát
    items: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        items = data.get("data") or data.get("items") or []
    if not items:
        return {"count": 0, "items": []}

    # limit védett 1..5
    safe_limit = max(1, min(int(limit or 1), 5))

    # szűrés
    filtered: List[Dict[str, Any]] = []
    for it in items:
        url = _norm_url(it.get("url", ""))
        if not url:
            continue
        if _blocked_domain(url):
            continue
        if not _age_ok(it.get("published_at", "")):
            continue
        if url in LAST_SENT_SET:
            continue
        filtered.append(it)

    # ha üres a szűrt lista, térjünk vissza üresen (nem küldünk ismétlést)
    if not filtered:
        return {"count": 0, "items": []}

    selected = filtered[:safe_limit]

    # cache-be rakjuk, hogy ne menjen újra
    for it in selected:
        _mark_sent(it.get("url", ""))

    # Telegram üzenet (max 3 elem formázva)
    msg = format_items_to_message(selected)
    await send_telegram(msg)

    # HTTP válasz
    return {
        "count": len(selected),
        "items": [
            {
                "title": it.get("title"),
                "source": it.get("source"),
                "published_at": it.get("published_at"),
                "url": it.get("url"),
            }
            for it in selected
        ],
    }