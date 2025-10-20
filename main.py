import os
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
import requests

app = FastAPI()

def normalize_since(raw: str | None) -> str:
    # ISO dátumot ad vissza; ha üres/rossz/jövőbeni, akkor 30 nappal ezelőtt.
    try:
        if not raw:
            raise ValueError("empty")
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc) - timedelta(days=30)
    now = datetime.now(timezone.utc)
    if dt > now:
        dt = now - timedelta(days=30)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

@app.get("/")
def root():
    return {"endpoints": ["/health", "/status", "/test/marketaux"]}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/status")
def status():
    return {
        "status": "running",
        "telegram_bot": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "chat_id_set": bool(os.getenv("TELEGRAM_CHAT_ID")),
        "marketaux_key": bool(os.getenv("MARKETAUX_API_KEY")),
    }

@app.get("/test/marketaux")
def test_marketaux():
    api = "https://api.marketaux.com/v1/news/all"
    params = {
        "api_token": os.getenv("MARKETAUX_API_KEY", ""),
        "symbols": os.getenv("NEWS_SYMBOLS", "AAPL,MSFT"),
        "language": os.getenv("NEWS_LANGUAGE", "en"),
        "limit": os.getenv("NEWS_LIMIT", "5"),
        "published_after": normalize_since(os.getenv("NEWS_SINCE")),
        "filter_entities": "true",
    }

    if not params["api_token"]:
        return {"ok": False, "error": "Missing MARKETAUX_API_KEY env var."}

    try:
        r = requests.get(api, params=params, timeout=20)
    except Exception as e:
        return {"ok": False, "error": f"request failed: {e.__class__.__name__}: {e}"}

    if r.status_code >= 400:
        return {
            "ok": False,
            "status_code": r.status_code,
            "reason": r.reason,
            "url": r.url,
            "body": r.text[:2000],
        }

    try:
        data = r.json()
    except Exception as e:
        return {"ok": False, "error": f"invalid json: {e}", "raw": r.text[:2000]}

    items = data.get("data") or []
    sample = items[0] if items else None
    return {"ok": True, "count": len(items), "sample": sample, "api_url": r.url}