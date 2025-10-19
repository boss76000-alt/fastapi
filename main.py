# -*- coding: utf-8 -*-
import os
from typing import Any, Dict

from fastapi import FastAPI, Query
import httpx

# --- környezeti változók ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- FastAPI app ---
app = FastAPI(title="Hedge Fund API", version="1.0")

# --- segédfüggvény: üzenet küldése Telegramra ---
async def telegram_send(text: str) -> Dict[str, Any]:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"ok": False, "error": "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
        try:
            data = r.json()
        except Exception:
            data = {"status_code": r.status_code, "text": r.text}
    return data

# --- endpointok ---
@app.get("/")
def root():
    return {
        "message": "Hedge Fund API aktív",
        "status": "OK",
        "endpoints": ["/health", "/test-telegram", "/notify"]
    }

@app.get("/health")
def health():
    return {
        "status": "running",
        "telegram_bot": bool(TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(TELEGRAM_CHAT_ID),
    }

@app.get("/test-telegram")
async def test_telegram():
    resp = await telegram_send("✅ Telegram kapcsolat OK — Hedge Fund API aktív!")
    ok = bool(resp.get("ok"))
    return {"ok": ok, "telegram_response": resp}

@app.get("/notify")
async def notify(text: str = Query(..., min_length=1)):
    resp = await telegram_send(text)
    ok = bool(resp.get("ok"))
    return {"ok": ok, "telegram_response": resp}