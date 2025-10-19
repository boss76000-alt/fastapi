import os
from fastapi import FastAPI
import httpx

# ---- környezeti változók ----
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---- FastAPI app LÉTREHOZÁSA ELŐSZÖR! ----
app = FastAPI(title="Hedge Fund API", version="1.0")

# ---- segédfüggvény Telegram küldéshez ----
async def telegram_send(text: str) -> dict:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"ok": False, "error": "Missing TELEGRAM_* envs"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
    return r.json()

# ---- endpointok ----
@app.get("/")
def root():
    return {
        "message": "Hedge Fund API aktív",
        "status": "OK",
        "endpoints": ["/health", "/test-telegram"]
    }

@app.get("/health")
def health():
    return {
        "status": "running",
        "BREVO_KEY_present": bool(os.getenv("BREVO_KEY")),
        "ALERT_TO_present": bool(os.getenv("ALERT_TO")),
    }

@app.get("/test-telegram")
async def test_telegram():
    resp = await telegram_send("✅ Telegram teszt OK")
    ok = bool(resp.get("ok"))
    return {"ok": ok, "telegram_response": resp}