# main.py
import os
import requests
from fastapi import FastAPI, HTTPException, Query

APP_TITLE = "Hedge Fund API"
APP_DESC = "Signals + scanner + alerts (Marketaux)"
APP_VER = "0.2.0"

app = FastAPI(title=APP_TITLE, description=APP_DESC, version=APP_VER)

def has_marketaux_key() -> bool:
    return bool(os.getenv("MARKETAUX_API_KEY", "").strip())

@app.get("/")
def root():
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut. Nézd meg a /docs oldalt a próbákhoz.",
        "endpoints": {"health": "/health", "scan": "/scan", "alerts_test": "/alerts/test"},
        "version": APP_VER,
    }

@app.get("/health")
def health():
    return {"status": "running", "marketaux_key_present": has_marketaux_key()}

@app.get("/scan")
def scan(
    symbols: str = Query(..., description="Pl.: AAPL,MSFT,BTC/USD,EUR/USD"),
    limit: int = 3,
    language: str = "en",
):
    api_key = os.getenv("MARKETAUX_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=401, detail="MARKETAUX_API_KEY hiányzik")

    url = "https://api.marketaux.com/v1/news/all"
    params = {"symbols": symbols, "language": language, "limit": limit, "api_token": api_key}

    r = requests.get(url, params=params, timeout=30)
    if r.status_code == 401:
        # Marketaux pontos hibája továbbítva
        raise HTTPException(status_code=401, detail=r.json())
    r.raise_for_status()
    return r.json()

@app.get("/alerts/test")
def alerts_test():
    return {"ok": True}