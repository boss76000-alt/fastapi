from fastapi import FastAPI
import os, datetime as dt
import httpx

app = FastAPI(title="Hedge Fund – minimal")

# --- helpers -------------------------------------------------
def getenv(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name, default)
    return v.strip() if isinstance(v, str) else v

async def send_telegram(text: str) -> bool:
    token = getenv("TELEGRAM_BOT_TOKEN")
    chat_id = getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    timeout = httpx.Timeout(10.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as cli:
        r = await cli.post(url, json=payload)
        return r.status_code == 200

async def fetch_marketaux(limit: int) -> dict:
    base = "https://api.marketaux.com/v1/news/all"
    token = getenv("MARKETAUX_API_TOKEN")
    symbols = getenv("NEWS_SYMBOLS", "")
    search = getenv("NEWS_SEARCH", "")
    language = getenv("NEWS_LANGUAGE", "en")
    since = getenv("NEWS_SINCE", "24h")  # pl. 24h, 7d, 2025-10-01

    if not token:
        return {"detail": {"marketaux_error": {"code": "missing_token", "message": "MARKETAUX_API_TOKEN is empty"}}}

    # published_after: ha relatív értéket adtál meg (pl. 24h), konvertáljuk ISO időbélyegre
    def since_to_iso(v: str) -> str | None:
        try:
            v = v.strip().lower()
            if v.endswith("h"):
                hours = int(v[:-1])
                t = dt.datetime.utcnow() - dt.timedelta(hours=hours)
                return t.replace(microsecond=0).isoformat() + "Z"
            if v.endswith("d"):
                days = int(v[:-1])
                t = dt.datetime.utcnow() - dt.timedelta(days=days)
                return t.replace(microsecond=0).isoformat() + "Z"
            # ha konkrét dátum/idő jön, hagyjuk a felhasználóra
            return v
        except Exception:
            return None

    params = {
        "api_token": token,
        "limit": str(max(1, min(limit, 5))),  # biztonságból 1..5
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

def format_items_to_message(items: list[dict]) -> str:
    lines = []
    for it in items[:3]:  # max 3 üzenetben
        title = it.get("title", "").strip()
        src = it.get("source", "")
        url = it.get("url", "")
        when = it.get("published_at", "")[:19].replace("T", " ")
        lines.append(f"• {title}\n  ({src} • {when})\n  {url}")
    return "🗞  Latest headlines:\n" + "\n\n".join(lines)

# --- minimal endpoints --------------------------------------
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
    }

@app.post("/test/telegram")
async def test_telegram():
    ok = await send_telegram("✅ Telegram test OK")
    return {"ok": ok}

# --- NEW: /news/auto ----------------------------------------
@app.get("/news/auto")
async def news_auto(limit: int = 1):
    """
    Egyszerű automata Marketaux hírlehívás az env változókkal.
    limit: 1..5 (alap:1)
    """
    data = await fetch_marketaux(limit)
    # ha hiba objektum
    if isinstance(data, dict) and "detail" in data and "marketaux_error" in data["detail"]:
        return data

    items = []
    # a Marketaux válasz szerkezete: {"data":[...]} vagy {"count":..,"items":[...]}
    if isinstance(data, dict):
        items = data.get("data") or data.get("items") or []
    if not items:
        return {"count": 0, "items": []}

    text = format_items_to_message(items)
    await send_telegram(text)
    # Visszaadjuk a kivonatot HTTP-ben is
    return {
        "count": len(items),
        "items": [
            {"title": it.get("title"), "source": it.get("source"), "published_at": it.get("published_at"), "url": it.get("url")}
            for it in items
        ],
    }