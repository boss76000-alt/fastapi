import os, datetime as dt
from typing import List, Dict, Any
import httpx
from fastapi import FastAPI, HTTPException, Query

API_BASE = "https://api.marketaux.com/v1"
TOKEN = os.getenv("MARKETAUX_API_TOKEN")

app = FastAPI(title="Hedge Fund API", version="0.2.0",
              description="Signals + scanner + alerts (Marketaux)")

def need_token():
    if not TOKEN:
        raise HTTPException(status_code=500, detail="MARKETAUX_API_TOKEN hiányzik.")

async def mx_news(symbols: List[str], limit: int = 5, lang: str = "en") -> Dict[str, Any]:
    need_token()
    params = {
        "symbols": ",".join(symbols),
        "filter_entities": "true",
        "limit": str(limit),
        "language": lang,
        "api_token": TOKEN,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{API_BASE}/news/all", params=params)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()

@app.get("/")
def root():
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut. Nézd meg a /docs oldalt a próbákhoz.",
        "endpoints": {"health": "/health", "scan": "/scan", "alerts_test": "/alerts/test"},
        "version": "0.2.0"
    }

@app.get("/health")
def health():
    return {"status": "running", "marketaux_key_present": bool(TOKEN)}

@app.get("/scan")
async def scan(
    symbols: str = Query(..., description="Pl.: AAPL,MSFT,BTC/USD,EUR/USD"),
    limit: int = 3,
    language: str = "en"
):
    """Egyszerű hír-szkenner Marketaux-ról, sentiment + forrásokkal."""
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    data = await mx_news(syms, limit=limit, lang=language)

    items = []
    for art in data.get("data", []):
        items.append({
            "title": art.get("title"),
            "url": art.get("url"),
            "published_at": art.get("published_at"),
            "source": art.get("source"),
            "sentiment": art.get("sentiment", None),
            "symbols": [e.get("symbol") for e in art.get("entities", []) if e.get("symbol")]
        })

    summary = {
        "counts": {"items": len(items)},
        "interval": "news",
        "generated_at": dt.datetime.utcnow().isoformat() + "Z"
    }
    return {"summary": summary, "items": items}

@app.get("/alerts/test")
def alerts_test():
    # ide később jöhet Slack webhook, most csak ping
    return {"ok": True, "msg": "alerts test"}