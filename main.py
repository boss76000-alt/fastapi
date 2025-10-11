from fastapi import FastAPI
import requests, os, datetime

app = FastAPI(title="Hedge Fund API", version="0.3.0")

# === ENV CONFIG ===
MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY")
ALERT_MIN_GRADE = os.getenv("ALERT_MIN_GRADE", "A")
ALERT_COOLDOWN_MIN = int(os.getenv("ALERT_COOLDOWN_MIN", "15"))
THRESHOLD_A = float(os.getenv("THRESHOLD_A", "-0.40"))
THRESHOLD_B = float(os.getenv("THRESHOLD_B", "-0.20"))
SCAN_SYMBOLS = os.getenv("SCAN_SYMBOLS", "AAPL,MSFT,NVDA,AVGO")
SCAN_LIMIT = int(os.getenv("SCAN_LIMIT", "5"))
SCAN_LANGUAGE = os.getenv("SCAN_LANGUAGE", "en")

LAST_ALERTS = []  # ideiglenes memória (email még nincs)

@app.get("/")
def root():
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut. Nézd meg a /docs oldalt a próbákhoz.",
        "endpoints": {
            "health": "/health",
            "scan": "/scan",
            "alerts_test": "/alerts/test",
            "alerts_run": "/alerts/run"
        },
        "version": "0.3.0"
    }

@app.get("/health")
def health():
    return {"status": "running", "marketaux_key_present": bool(MARKETAUX_API_KEY)}

@app.get("/scan")
def scan():
    """Alap MarketAux scan"""
    url = f"https://api.marketaux.com/v1/news/all?symbols={SCAN_SYMBOLS}&filter_entities=true&limit={SCAN_LIMIT}&language={SCAN_LANGUAGE}&api_token={MARKETAUX_API_KEY}"
    r = requests.get(url)
    return r.json()

@app.get("/alerts/test")
def alerts_test():
    return {"ok": True, "rules": {"THRESHOLD_A": THRESHOLD_A, "THRESHOLD_B": THRESHOLD_B}}

@app.get("/alerts/run")
def alerts_run():
    """Dry-run alert motor: csak megmutatja, mit jelölne alertnek."""
    url = f"https://api.marketaux.com/v1/news/all?symbols={SCAN_SYMBOLS}&filter_entities=true&limit={SCAN_LIMIT}&language={SCAN_LANGUAGE}&api_token={MARKETAUX_API_KEY}"
    data = requests.get(url).json()
    alerts = []

    for art in data.get("data", []):
        score = art.get("sentiment_score", 0)
        title = art.get("title", "")
        source = art.get("source", "")
        if score <= THRESHOLD_A:
            level = "🔥 STRONG NEGATIVE"
        elif score <= THRESHOLD_B:
            level = "⚠️ NEGATIVE"
        elif score >= abs(THRESHOLD_B):
            level = "✅ POSITIVE"
        else:
            continue

        alerts.append({
            "title": title,
            "source": source,
            "sentiment_score": score,
            "level": level,
            "published": art.get("published_at")
        })

    now = datetime.datetime.utcnow().isoformat()
    return {
        "timestamp": now,
        "symbol_set": SCAN_SYMBOLS,
        "alerts_count": len(alerts),
        "alerts": alerts
    }