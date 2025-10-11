import os
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query
import httpx

APP_NAME = "Hedge Fund API"
APP_VERSION = "0.1.0"

app = FastAPI(title=APP_NAME, version=APP_VERSION)


@app.get("/", summary="Root")
async def root() -> Dict[str, Any]:
    """
    Alap üdvözlő endpoint. Itt szabadon módosíthatod az üzenetet.
    """
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut. Nézd meg a /docs oldalt a próbához.",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "clearline": "/clearline?symbol=AAPL&interval=1min",
        },
        "version": APP_VERSION,
    }


@app.get("/health", summary="Health")
async def health() -> Dict[str, Any]:
    """
    Egyszerű egészségügyi ellenőrzés.
    """
    return {
        "status": "running",
        "twelvedata_key_present": bool(os.getenv("TWELVEDATA_API_KEY")),
    }


@app.get("/clearline", summary="Clearline")
async def clearline(
    symbol: str = Query(..., description="Ticker, pl. AAPL vagy BTC/USD"),
    interval: str = Query(
        "1min",
        description="TwelveData interval (1min, 5min, 15min, 1h, 1day, ...)",
    ),
) -> Dict[str, Any]:
    """
    Gyors 'clearline' végpont: TwelveData time_series-ből lekéri az utolsó két
    gyertyát, és visszaadja a legutóbbi zárót, valamint a változást.
    """
    api_key = os.getenv("TWELVEDATA_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Hiányzik a TWELVEDATA_API_KEY változó a Railway 'Variables' alatt.",
        )

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 2,  # utolsó két gyertya a változáshoz
        "format": "JSON",
        "apikey": api_key,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params)
    data = r.json()

    # TwelveData hibaüzenet kezelése
    if "status" in data and data.get("status") == "error":
        raise HTTPException(status_code=400, detail=data.get("message", "API error"))

    ts = data.get("values") or data.get("data") or data.get("time_series") or data.get("values")
    if not ts and "values" in data:
        ts = data["values"]
    if not ts:
        # standard struktúra: {"meta": {...}, "values": [ {datetime, close, ...}, ... ] }
        ts = data.get("values", [])

    if not isinstance(ts, list) or len(ts) == 0:
        raise HTTPException(status_code=404, detail="Nincs elérhető adat erre a kérésre.")

    # legutóbbi és előző záró
    last = ts[0]
    prev = ts[1] if len(ts) > 1 else None

    try:
        last_close = float(last.get("close"))
        prev_close = float(prev.get("close")) if prev else None
    except Exception:
        raise HTTPException(status_code=500, detail="Váratlan adatformátum a TwelveData-tól.")

    delta = None
    delta_pct = None
    if prev_close is not None:
        delta = last_close - prev_close
        if prev_close != 0:
            delta_pct = (delta / prev_close) * 100.0

    return {
        "symbol": symbol,
        "interval": interval,
        "last": {
            "datetime": last.get("datetime") or last.get("time") or last.get("timestamp"),
            "close": last_close,
        },
        "previous": {
            "datetime": prev.get("datetime") if prev else None,
            "close": prev_close,
        },
        "delta": delta,
        "delta_pct": delta_pct,
        "source": "twelvedata",
    }


# Opcionális: lokális futtatáshoz (Railway-en nem szükséges)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
    
    import asyncio

def grade_signal(delta_pct: float) -> str:
    # egyszerű küszöbök – később finomítjuk
    if abs(delta_pct) >= 1.0:
        return "A"
    if abs(delta_pct) >= 0.3:
        return "B"
    return "C"

@app.get("/scan")
async def scan(
    watchlist: str = Query(..., description="Vesszővel elválasztott szimbólumok, pl. AAPL,MSFT,BTC/USD,EUR/USD"),
    interval: str = Query("1min", pattern="^(1min|5min|15min|30min|1h)$"),
    top: int = Query(10, ge=1, le=50),
):
    """
    Többszimbólumos gyorsteszt. TwelveData-ról lehúzza az utolsó és az előző gyertyát,
    kiszámolja a %-os elmozdulást, és A/B/C fokozatot ad.
    """
    symbols = [s.strip() for s in watchlist.split(",") if s.strip()]
    if not symbols:
        raise HTTPException(status_code=400, detail="Empty watchlist")

    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [fetch_latest_from_twelvedata(client, s, interval) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    rows = []
    for sym, res in zip(symbols, results):
        if isinstance(res, Exception) or res is None:
            rows.append({"symbol": sym, "error": True})
            continue
        delta_pct = res.get("delta_pct", 0.0)
        rows.append({
            "symbol": sym,
            "interval": interval,
            "delta_pct": round(delta_pct, 6),
            "grade": grade_signal(delta_pct),
            "last": res.get("last"),
            "previous": res.get("previous"),
        })

    # rendezzük abszolút %-ra és vágjuk top N-re
    rows.sort(key=lambda r: abs(r.get("delta_pct", 0.0)), reverse=True)
    return {"count": len(rows[:top]), "results": rows[:top]}