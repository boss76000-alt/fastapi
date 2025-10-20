import os
from fastapi import FastAPI

app = FastAPI(title="Hedge Fund API", version="0.1.0")

@app.get("/health")
def health():
    return {"ok": True, "status": "running"}

@app.get("/status")
def status():
    return {
        "status": "running",
        "telegram_bot": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "chat_id_set": bool(os.getenv("TELEGRAM_CHAT_ID")),
        "marketaux_key": bool(os.getenv("MARKETAUX_API_TOKEN")),
    }

# Opcionális: egy nagyon egyszerű teszt-endpoint, ami NEM hív külső API-t
@app.get("/test")
def test():
    return {"ok": True, "msg": "API alive"}