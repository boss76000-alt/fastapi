import os
from fastapi import FastAPI
import requests

app = FastAPI()

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
        "api_token": os.getenv("MARKETAUX_API_KEY"),
        "symbols": os.getenv("NEWS_SYMBOLS", "AAPL,MSFT"),
        "language": os.getenv("NEWS_LANGUAGE", "en"),
        "limit": os.getenv("NEWS_LIMIT", "5"),
        "published_after": os.getenv("NEWS_SINCE", "2025-10-17T00:00:00Z"),
        "filter_entities": "true",
    }
    r = requests.get(api, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    sample = data["data"][0] if ("data" in data and data["data"]) else None
    return {"ok": True, "count": len(data.get("data", [])), "sample": sample}