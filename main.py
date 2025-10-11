import os
import time
import smtplib
from email.mime.text import MIMEText
from typing import List, Dict, Any, Tuple
from fastapi import FastAPI, Query
import requests

APP_VERSION = "0.4.0"

app = FastAPI(title="Hedge Fund API", description="Signals + scanner + alerts (Marketaux)", version=APP_VERSION)

# ---------- ENV helpers ----------
def env_str(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()

def env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except Exception:
        return default

def env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key, None)
    if v is None:
        return default
    return str(v).lower() in ("1","true","yes","on")

def env_list(key: str) -> List[str]:
    raw = os.getenv(key, "")
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]

# ---------- Config ----------
DATA_PROVIDER = env_str("DATA_PROVIDER", "AUX").upper()
AUX_KEY = env_str("MARKETAUX_API_KEY")
LOOKBACK_MIN = env_int("LOOKBACK_MIN", 60)
TIMEOUT = env_int("GLOBAL_TIMEOUT_SEC", 30)

THRESHOLD_A = float(os.getenv("THRESHOLD_A", "-0.10"))
THRESHOLD_B = float(os.getenv("THRESHOLD_B", "-0.05"))

KEYWORDS_NEG = [k.strip() for k in os.getenv("KEYWORDS_NEG","").split(",") if k.strip()]
KEYWORDS_POS = [k.strip() for k in os.getenv("KEYWORDS_POS","").split(",") if k.strip()]

ALERT_AUTO = env_bool("ALERT_AUTO", True)
ALERT_COOLDOWN_MIN = env_int("ALERT_COOLDOWN_MIN", 15)
ALERT_MIN_GRADE = env_str("ALERT_MIN_GRADE", "A").upper()
ALERT_TO = env_str("ALERT_TO")
SUBJECT_PREFIX = env_str("SUBJECT_PREFIX", "[HedgeFund]")
DEDUP_HOURS = env_int("DEDUP_HOURS", 24)

SMTP_HOST = env_str("SMTP_HOST")
SMTP_PORT = env_int("SMTP_PORT", 587)
SMTP_USER = env_str("SMTP_USER")
SMTP_PASS = env_str("SMTP_PASS")

# Memory dedup/cooldown
_recent_sent: Dict[str, float] = {}    # key -> last_ts
_recent_seen: Dict[str, float] = {}    # article_uuid -> ts

def _now() -> float:
    return time.time()

def _cooldown_key(symbol: str, title: str) -> str:
    return f"{symbol}|{title}".lower()

def _within(ts: float, minutes: int) -> bool:
    return (_now() - ts) <= minutes * 60

def _within_hours(ts: float, hours: int) -> bool:
    return (_now() - ts) <= hours * 3600

# ---------- Email ----------
def send_email(subject: str, body: str) -> bool:
    if not ALERT_TO:
        return False
    # no-op mode if no SMTP creds
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        # log-only mode
        print(f"[ALERT][NO-SMTP] {subject}\n{body[:300]}...")
        return True
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = ALERT_TO

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, [ALERT_TO], msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

# ---------- Marketaux ----------
def fetch_aux(symbols: List[str], limit: int = 3, language: str = "en") -> Dict[str, Any]:
    assert DATA_PROVIDER == "AUX"
    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "symbols": ",".join(symbols),
        "filter_entities": "true",
        "language": language,
        "limit": str(limit),
        "api_token": AUX_KEY,
    }
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# ---------- Grading ----------
def contains_any(text: str, words: List[str]) -> bool:
    t = text.lower()
    return any(w.lower() in t for w in words)

def grade_item(item: Dict[str, Any]) -> Tuple[str, float]:
    """
    Return (grade, sentiment_score). Grades: 'A','B','C','-'
    Logic: strong negative -> A, mild negative -> B, else '-'
    """
    s = float(item.get("sentiment_score") or 0.0)
    title = (item.get("title") or "") + " " + (item.get("description") or "") + " " + (item.get("snippet") or "")
    neg_hit = contains_any(title, KEYWORDS_NEG)
    # Grades by thresholds & keywords
    if s <= THRESHOLD_A or neg_hit and s <= THRESHOLD_B:
        return "A", s
    if s <= THRESHOLD_B or neg_hit:
        return "B", s
    return "-", s

def passes_min_grade(g: str, min_g: str) -> bool:
    order = {"A":3,"B":2,"C":1,"-":0}
    return order.get(g,0) >= order.get(min_g,3)

# ---------- Subject / Body ----------
def build_subject(symbol: str, g: str, s: float, title: str) -> str:
    s_pct = f"{s:+.3f}"
    return f"{SUBJECT_PREFIX} {symbol} {s_pct} | {g} | {title[:60]}"

def build_body(item: Dict[str, Any]) -> str:
    parts = [
        f"Title: {item.get('title','')}",
        f"Sentiment: {item.get('sentiment_score')}",
        f"Source: {item.get('source')}",
        f"Symbols: {', '.join([e.get('symbol') for e in item.get('entities',[]) if e.get('symbol')])}",
        f"URL: {item.get('url')}",
        "",
        (item.get('description') or item.get('snippet') or "")[:1000],
    ]
    return "\n".join(parts)

# ---------- API ----------
@app.get("/")
def root():
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut. Nézd meg a /docs oldalt a próbákhoz.",
        "endpoints": {"health": "/health", "scan": "/scan", "alerts_test": "/alerts/test"},
        "version": APP_VERSION,
    }

@app.get("/health")
def health():
    return {"status": "running", "marketaux_key_present": bool(AUX_KEY)}

@app.get("/scan")
def scan(symbols: str = Query(..., description="Pl.: AAPL,MSFT,NVDA"),
         limit: int = 3,
         language: str = "en"):
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if DATA_PROVIDER != "AUX":
        return {"detail": "Only AUX is supported now."}
    data = fetch_aux(syms, limit=limit, language=language)
    return data

@app.get("/alerts/test")
def alerts_test(symbols: str = Query("AAPL,MSFT,NVDA,AVGO"),
                limit: int = 5,
                language: str = "en"):
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    res = fetch_aux(syms, limit=limit, language=language)

    alerts = []
    now_ts = _now()

    for item in res.get("data", []):
        # dedup by uuid age
        uuid = item.get("uuid") or item.get("url") or ""
        last_seen = _recent_seen.get(uuid)
        if last_seen and _within_hours(last_seen, DEDUP_HOURS):
            continue
        _recent_seen[uuid] = now_ts

        # pick one primary symbol (fallback)
        symbol = ""
        ents = item.get("entities") or []
        for e in ents:
            if e.get("type") == "equity" and e.get("symbol"):
                symbol = e["symbol"].upper()
                break
        if not symbol and syms:
            symbol = syms[0]

        grade, sent = grade_item(item)
        if not passes_min_grade(grade, ALERT_MIN_GRADE):
            continue

        key = _cooldown_key(symbol, item.get("title",""))
        last = _recent_sent.get(key)
        if last and _within(last, ALERT_COOLDOWN_MIN):
            continue

        alert_obj = {
            "symbol": symbol,
            "grade": grade,
            "sentiment": sent,
            "title": item.get("title"),
            "url": item.get("url"),
            "source": item.get("source"),
        }
        alerts.append(alert_obj)

        if ALERT_AUTO:
            subject = build_subject(symbol, grade, sent, item.get("title",""))
            body = build_body(item)
            if send_email(subject, body):
                _recent_sent[key] = now_ts

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now_ts)),
        "symbol_set": ",".join(syms),
        "alerts_count": len(alerts),
        "alerts": alerts,
    }