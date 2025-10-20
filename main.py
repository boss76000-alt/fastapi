# main.py
import os
import requests
from fastapi import FastAPI, Query

app = FastAPI(title="Hedge Fund API")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def send_telegram(text: str):
    """Küld üzenetet a beállított chatre. Visszaadja (ok, response_json)."""
    if not TELEGRAM_BOT_TOKEN:
        return False, {"error": "Missing TELEGRAM_BOT_TOKEN"}
    if not TELEGRAM_CHAT_ID:
        return False, {"error": "Missing TELEGRAM_CHAT_ID"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.ok, r.json()
    except Exception as e:
        return False, {"error": str(e)}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/status")
def status():
    return {
        "status": "running",
        "telegram_bot": bool(TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(TELEGRAM_CHAT_ID),
    }

@app.get("/running")
def running():
    return {"ok": True}

@app.get("/test-telegram")
def test_telegram(text: str = Query("✅ Telegram kapcsolat OK — Hedge Fund API aktív!")):
    ok, resp = send_telegram(text)
    return {"ok": ok, "telegram_response": resp}
    
# --- Marketaux teszt endpoint (CSERE BLOKK KEZDETE) ---
from fastapi import HTTPException
import os, requests

@app.get("/test-marketaux")
def test_marketaux():
    api_key = os.getenv("MARKETAUX_API_KEY")
    if not api_key:
        return {"ok": False, "error": "MARKETAUX_API_KEY missing"}

    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "api_token": api_key,
        "limit": 1,
        "published_after": "2024-01-01T00:00:00Z"
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {
            "ok": True,
            "status_code": r.status_code,
            "sample": (data.get("data") or [])[:1]
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Marketaux request failed: {e}")
# --- Marketaux teszt endpoint (CSERE BLOKK VÉGE) ---
