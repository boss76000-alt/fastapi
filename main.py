from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
import os
import asyncio

app = FastAPI(title="Hedge Fund API", version="1.0")

# --- Környezeti változók ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ALERT_TOKEN = os.getenv("ALERT_TOKEN", "")

# --- Telegram üzenetküldő függvény ---
async def telegram_send(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"ok": False, "error": "Missing bot token or chat ID"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload)
            data = r.json()
            return data
    except Exception as e:
        return {"ok": False, "error": str(e)}

# --- Health check ---
@app.get("/health")
async def health():
    return {
        "status": "running",
        "telegram_bot": bool(TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(TELEGRAM_CHAT_ID)
    }

# --- Teszt üzenet küldése ---
@app.get("/test-telegram")
async def test_telegram():
    resp = await telegram_send("✅ Telegram kapcsolat OK – Hedge Fund API aktív!")
    return JSONResponse(content={"ok": True, "telegram_response": resp}, ensure_ascii=False)

# --- Egyszerű nyílt üzenetküldő végpont ---
@app.get("/notify")
async def notify(text: str = Query(..., min_length=1)):
    resp = await telegram_send(f"📢 {text}")
    ok = bool(resp.get("ok"))
    return JSONResponse(content={"ok": ok, "telegram_response": resp}, ensure_ascii=False)

# --- Tokenes, védett üzenetküldő végpont ---
@app.get("/notify-secure")
async def notify_secure(text: str = Query(..., min_length=1), token: str = Query("")):
    if not ALERT_TOKEN or token != ALERT_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing ALERT_TOKEN")
    resp = await telegram_send(f"🔐 {text}")
    ok = bool(resp.get("ok"))
    return JSONResponse(content={"ok": ok, "telegram_response": resp}, ensure_ascii=False)

# --- Root üzenet (ha valaki csak a domainre megy) ---
@app.get("/")
async def root():
    return JSONResponse(
        content={
            "message": "Hedge Fund API aktív 🚀",
            "status": "OK",
            "endpoints": ["/health", "/test-telegram", "/notify", "/notify-secure"]
        },
        ensure_ascii=False
    )