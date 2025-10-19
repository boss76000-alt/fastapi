import os
import httpx
from fastapi import FastAPI

# Környezeti változók
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# FastAPI app
app = FastAPI(title="Hedge Fund API", version="1.0")

# --- Telegram küldő függvény ---
async def telegram_send(text: str) -> dict:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"ok": False, "error": "Missing TELEGRAM credentials"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
    return r.json()

# --- Endpontok ---
@app.get("/")
def root():
    return {
        "message": "Hedge Fund API aktív",
        "status": "OK",
        "endpoints": ["/health", "/test-telegram"]
    }

@app.get("/health")
def health():
    return {"status": "running"}

@app.get("/test-telegram")
async def test_telegram():
    resp = await telegram_send("✅ Telegram teszt OK!")
    ok = bool(resp.get("ok"))
    return {"ok": ok, "telegram_response": resp}