from fastapi import FastAPI
import os
from telegram import Bot

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root():
    return {"ok": True, "service": "hedge-fund-core"}

@app.get("/status")
def status():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    return {
        "status": "running",
        "telegram_bot": bool(bot_token),
        "chat_id_set": bool(chat_id)
    }

@app.get("/test/telegram")
async def test_telegram():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return {"ok": False, "detail": "TELEGRAM_BOT_TOKEN vagy TELEGRAM_CHAT_ID hiányzik."}
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text="✅ Hedge Fund API: Telegram teszt OK")
    return {"ok": True}