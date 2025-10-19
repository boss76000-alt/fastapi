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