from telegram_notifier import send_telegram

@app.get("/test-telegram")
def test_telegram():
    res = send_telegram("Hedge Fund webhook ➜ Telegram test OK ✅")
    return {"status": "sent", "message_id": res["message_id"]}

# (opcionális) health bővítés
@app.get("/health")
def health():
    import os
    return {
        "status": "running",
        "TELEGRAM_BOT_TOKEN_present": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "TELEGRAM_CHAT_ID_present": bool(os.getenv("TELEGRAM_CHAT_ID")),
    }