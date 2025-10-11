# === Hedge Fund AI Core (MarketAux-only edition) ===
# Simplified, stable, self-contained base
# Author: GPT-5 + Deaga

import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging

app = FastAPI(title="Hedge Fund AI – MarketAux Core")

# === ENV ===
MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")

if not MARKETAUX_API_KEY:
    raise ValueError("⚠️ Missing MARKETAUX_API_KEY in Railway Variables!")

# === LOGGER ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hedgefund")

# === HEALTH ===
@app.get("/health")
def health():
    return {"status": "running", "provider": "MarketAux", "key_present": bool(MARKETAUX_API_KEY)}

# === SIMPLE TEST ===
@app.get("/test")
def test():
    return {"msg": "✅ Hedge Fund AI core online (MarketAux mode)"}

# === FETCH LATEST NEWS ===
@app.get("/news/{symbol}")
def get_news(symbol: str):
    """Fetch recent MarketAux news for a given ticker"""
    try:
        url = (
            f"https://api.marketaux.com/v1/news/all"
            f"?symbols={symbol.upper()}&filter_entities=true&language=en&limit=5"
            f"&api_token={MARKETAUX_API_KEY}"
        )
        r = requests.get(url, timeout=10)
        data = r.json()

        # sanity check
        if "data" not in data:
            return JSONResponse(status_code=502, content={"error": "No data returned", "raw": data})

        parsed = [
            {
                "title": item.get("title"),
                "summary": item.get("description"),
                "source": item.get("source"),
                "sentiment": item.get("overall_sentiment_label"),
                "published_at": item.get("published_at"),
            }
            for item in data["data"]
        ]

        return {"symbol": symbol.upper(), "count": len(parsed), "news": parsed}

    except Exception as e:
        logger.exception("Error fetching news")
        return JSONResponse(status_code=500, content={"error": str(e)})

# === ROOT ===
@app.get("/")
def root():
    return {
        "app": "Hedge Fund AI (MarketAux-only)",
        "status": "✅ ready",
        "endpoints": ["/test", "/health", "/news/{symbol}"],
    }