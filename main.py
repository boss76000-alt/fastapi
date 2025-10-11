import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Query, HTTPException
import httpx

app = FastAPI(title="Hedge Fund API", version="0.1.0")

TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")

BASE_INFO = {
    "greeting": "Hello, Hedge Fund!",
    "message": "FastAPI fut. Nézd meg a /docs oldalt a próbákhoz.",
    "endpoints": {
        "docs": "/docs",
        "health": "/health",
        "clearline": "/clearline?symbol=AAPL&interval=1min",
        "scan": "/scan?symbols=AAPL,MSFT,BTC/USD,EUR/USD&interval=1min&a_thr=0.5&b_thr=0.2",
    },
}

@app.get("/")
def root():
    return BASE_INFO

@app.get("/health")
def health():
    return {"status": "running", "twelvedata_key_present": bool(TWELVEDATA_KEY)}

async def fetch_last_two(symbol: str, interval: str) -> Dict[str, Any]:
    if not TWELVEDATA_KEY:
        raise HTTPException(status_code=500, detail="Missing TWELVEDATA_API_KEY")

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 2,
        "apikey": TWELVEDATA_KEY,
    }
    url = "https://api.twelvedata.com/time_series"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        data = r.json()
    if "values" not in data:
        # TD hiba-üzenet továbbítása (rate limit / invalid symbol stb.)
        return {"symbol": symbol, "error": data}
    try:
        last = data["values"][0]
        prev = data["values"][1]
        last_c = float(last["close"])
        prev_c = float(prev["close"])
        delta = last_c - prev_c
        delta_pct = (delta / prev_c) * 100 if prev_c else 0.0
        return {
            "symbol": symbol,
            "interval": interval,
            "last": {"datetime": last["datetime"], "close": last_c},
            "previous": {"datetime": prev["datetime"], "close": prev_c},
            "delta": delta,
            "delta_pct": delta_pct,
            "source": "twelvedata",
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "raw": data}

@app.get("/clearline")
async def clearline(symbol: str = Query(...), interval: str = Query("1min")):
    return await fetch_last_two(symbol, interval)

def grade(delta_pct: float, a_thr: float, b_thr: float) -> str:
    abs_pct = abs(delta_pct)
    if abs_pct >= a_thr:
        return "A"
    if abs_pct >= b_thr:
        return "B"
    return "C"

@app.get("/scan")
async def scan(
    symbols: Optional[str] = Query(None, description="Vesszővel elválasztott watchlist"),
    interval: str = Query("1min"),
    a_thr: float = Query(0.5, description="A jelzés küszöb (%, abs)"),
    b_thr: float = Query(0.2, description="B jelzés küszöb (%, abs)"),
):
    # Alap watchlist, ha nem adsz meg sajátot
    default_list = ["AAPL", "MSFT", "BTC/USD", "EUR/USD"]
    watch = [s.strip() for s in (symbols.split(",") if symbols else default_list) if s.strip()]
    # Párhuzamos lekérés
    import asyncio
    tasks = [fetch_last_two(s, interval) for s in watch]
    results = await asyncio.gather(*tasks)
    # Jelölés + rendezés abs(delta_pct) szerint
    enriched = []
    for r in results:
        if "delta_pct" in r:
            r["grade"] = grade(r["delta_pct"], a_thr, b_thr)
        enriched.append(r)
    enriched.sort(key=lambda x: abs(x.get("delta_pct", 0.0)), reverse=True)
    summary = {
        "counts": {
            "A": sum(1 for x in enriched if x.get("grade") == "A"),
            "B": sum(1 for x in enriched if x.get("grade") == "B"),
            "C": sum(1 for x in enriched if x.get("grade") == "C"),
            "errors": sum(1 for x in enriched if "error" in x),
        },
        "interval": interval,
        "thresholds": {"A": a_thr, "B": b_thr},
    }
    return {"summary": summary, "items": enriched}