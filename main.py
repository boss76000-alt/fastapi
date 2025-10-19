from fastapi import FastAPI
import os, httpx

app = FastAPI(title="Hedge Fund API", version="1.1")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def telegram_send(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"ok": False, "error": "Missing Telegram credentials"}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
    return r.json()

@app.get("/")
def root():
    return {"message": "Hedge Fund API aktív", "status": "OK", "endpoints": ["/health", "/test-telegram"]}

@app.get("/health")
def health():
    return {
        "status": "running",
        "telegram_bot": bool(TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(TELEGRAM_CHAT_ID)
    }

@app.get("/test-telegram")
async def test_telegram():
    resp = await telegram_send("✅ Telegram kapcsolat OK — Hedge Fund API aktív!")
    return {"ok": bool(resp.get("ok")), "telegram_response": resp}
    @app.get("/notify")
async def notify(text: str):
    resp = await telegram_send(f"📡 Manuális üzenet: {text}")
    return {"ok": bool(resp.get("ok")), "telegram_response": resp}