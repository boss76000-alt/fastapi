from fastapi import FastAPI, Query
import requests
import os

app = FastAPI()

# 🔹 Telegram bot token és chat_id
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 🔹 Telegram üzenetküldő függvény
async def telegram_send(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"ok": False, "error": "Missing bot token or chat id"}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        resp = requests.post(url, json=payload)
        return resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

# 🔹 Alap ellenőrzés – futás
@app.get("/")
async def root():
    return {"status": "running", "telegram_bot": bool(TELEGRAM_BOT_TOKEN), "chat_id_set": bool(TELEGRAM_CHAT_ID)}

# 🔹 Teszt végpont
@app.get("/test-telegram")
async def test_telegram():
    resp = await telegram_send("✅ Telegram kapcsolat OK — Hedge Fund API aktív!")
    return {"ok": bool(resp.get("ok")), "telegram_response": resp}

# 🔹 Fő értesítő végpont (ez az új!)
@app.get("/notify")
async def notify(text: str = Query(..., min_length=1)):
    resp = await telegram_send(text)
    return {"ok": bool(resp.get("ok")), "telegram_response": resp}
    
    # --- META ENDPOINTOK ---
@app.get("/", tags=["meta"])
async def home():
    return {
        "status": "running",
        "telegram_bot": bool(TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(TELEGRAM_CHAT_ID),
    }

@app.get("/health", tags=["meta"])
async def health():
    return {"ok": True}
# --- /META ENDPOINTOK ---