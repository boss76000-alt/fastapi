import os
import math
import time
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import httpx

APP_VERSION = "0.2.0"

# ---------- Konfig / ENV ----------
TWELVE_KEY = os.getenv("TWELVEDATA_KEY", "")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")  # opcionális
ALERT_AUTO = os.getenv("ALERT_AUTO", "0") == "1"    # automata háttér-scan
ALERT_COOLDOWN_MIN = int(os.getenv("ALERT_COOLDOWN_MIN", "15"))
ALERT_MIN_GRADE = os.getenv("ALERT_MIN_GRADE", "A").upper()  # A|B|C
# grade küszöbök (abszolút %-ban)
THRESH_A = float(os.getenv("THRESHOLD_A", "0.5"))   # pl. 0.5%+
THRESH_B = float(os.getenv("THRESHOLD_B", "0.2"))   # pl. 0.2%+
# alapértelmezett szimbólumok & intervallum
DEFAULT_SYMBOLS = os.getenv("SCAN_SYMBOLS", "AAPL,MSFT,BTC/USD,EUR/USD")
DEFAULT_INTERVAL = os.getenv("SCAN_INTERVAL", "1min")

# riasztás deduplikáció (cooldown)
_last_alert_at: Dict[str, float] = {}

app = FastAPI(
    title="Hedge Fund API",
    version=APP_VERSION,
    description="Signals + scanner + alerts (Slack webhook támogatással)"
)

# ---------- Helperek ----------
def grade_from_delta_pct(delta_pct: float) -> str:
    ap = abs(delta_pct) * 100.0
    if ap >= THRESH_A:
        return "A"
    if ap >= THRESH_B:
        return "B"
    return "C"

def grade_meets(min_grade: str, g: str) -> bool:
    order = {"A": 3, "B": 2, "C": 1}
    return order.get(g, 0) >= order.get(min_grade, 0)

def cooldown_ok(key: str) -> bool:
    now = time.time()
    last = _last_alert_at.get(key, 0.0)
    if (now - last) >= ALERT_COOLDOWN_MIN * 60:
        _last_alert_at[key] = now
        return True
    return False

async def fetch_last_two(symbol: str, interval: str) -> Dict[str, Any]:
    if not TWELVE_KEY:
        raise HTTPException(status_code=500, detail="TWELVEDATA_KEY hiányzik.")
    params = {
        "symbol": symbol,
        "interval": interval,
        "apikey": TWELVE_KEY,
        "outputsize": 2,
        "format": "JSON"
    }
    url = "https://api.twelvedata.com/time_series"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    if "values" not in data or len(data["values"]) < 2:
        raise HTTPException(status_code=502, detail=f"Kevés adat: {symbol}")

    last = data["values"][0]
    prev = data["values"][1]
    last_close = float(last["close"])
    prev_close = float(prev["close"])
    delta = last_close - prev_close
    delta_pct = 0.0 if prev_close == 0 else (delta / prev_close)
    g = grade_from_delta_pct(delta_pct)
    return {
        "symbol": symbol,
        "interval": interval,
        "last": {"datetime": last["datetime"], "close": last_close},
        "previous": {"datetime": prev["datetime"], "close": prev_close},
        "delta": delta,
        "delta_pct": delta_pct,
        "source": "twelvedata",
        "grade": g,
    }

async def slack_notify(payload: Dict[str, Any]) -> None:
    if not SLACK_WEBHOOK:
        return
    text = payload.get("text") or ""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(SLACK_WEBHOOK, json={"text": text})
        except Exception:
            # Néma hiba, hogy az API tovább fusson
            pass

def fmt_move(item: Dict[str, Any]) -> str:
    pct = item["delta_pct"] * 100.0
    sign = "+" if pct >= 0 else ""
    return f"{item['symbol']} {sign}{pct:.3f}% ({item['last']['close']:.4f})"

# ---------- Végpontok ----------
@app.get("/")
def root():
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut. Nézd meg a /docs oldalt a próbákhoz.",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "clearline": "/clearline?symbol=AAPL&interval=1min",
            "scan": "/scan?symbols=AAPL,MSFT&interval=1min",
            "alerts_test": "/alerts/test"
        },
        "version": APP_VERSION
    }

@app.get("/health")
def health():
    return {"status": "running", "twelvedata_key_present": bool(TWELVE_KEY)}

@app.get("/clearline")
async def clearline(symbol: str = Query(...), interval: str = Query("1min")):
    item = await fetch_last_two(symbol, interval)
    return JSONResponse(item)

@app.get("/scan")
async def scan(
    symbols: Optional[str] = Query(None, description="Pl. AAPL,MSFT,BTC/USD"),
    interval: str = Query("1min"),
):
    syms: List[str] = [s.strip() for s in (symbols or DEFAULT_SYMBOLS).split(",") if s.strip()]
    items: List[Dict[str, Any]] = []
    errors: List[str] = []

    for s in syms:
        try:
            items.append(await fetch_last_two(s, interval))
        except Exception as e:
            errors.append(f"{s}: {str(e)}")

    counts = {"A": 0, "B": 0, "C": 0}
    for it in items:
        counts[it["grade"]] += 1

    return {
        "summary": {
            "counts": counts,
            "errors": len(errors),
            "interval": interval,
            "thresholds": {"A": THRESH_A, "B": THRESH_B},
        },
        "items": items,
        "errors_detail": errors,
    }

# ---------- Riasztás logika ----------
async def scan_and_alert_once() -> Dict[str, Any]:
    res = await scan(None, DEFAULT_INTERVAL)  # ugyanaz a logika, mint /scan
    sent = []

    for it in res["items"]:
        g = it["grade"]
        key = f"{it['symbol']}|{DEFAULT_INTERVAL}|{g}"
        if grade_meets(ALERT_MIN_GRADE, g) and cooldown_ok(key):
            msg = f"Signal {g}: {fmt_move(it)}"
            await slack_notify({"text": msg})
            sent.append({"symbol": it["symbol"], "grade": g, "message": msg})

    return {"sent": sent, "summary": res["summary"]}

@app.get("/alerts/test")
async def alerts_test():
    """Kézi próba: lefuttat egy kört és – ha van webhook – küld Slack-re."""
    out = await scan_and_alert_once()
    return out

# ---------- Háttérben időzített scanner (opcionális) ----------
async def background_loop():
    # 60s-enként futtatjuk; TwelveData nem szereti a túl sűrű hívást.
    while True:
        try:
            await scan_and_alert_once()
        except Exception:
            pass
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup():
    if ALERT_AUTO:
        asyncio.create_task(background_loop())