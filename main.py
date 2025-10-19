from fastapi import FastAPI
import os
import httpx

# ---- Környezeti változók ----
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---- FastAPI app létrehozása ----
app = FastAPI(title="Hedge Fund API", version="1.0")

# ---- Segédfüggvény Telegram küldéshez ----
async def telegram_send(text: str) -> dict:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"ok": False, "error": "Hiányzó TELEGRAM token vagy chat_id"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
        return r.json()

# ---- Alap (health) végpont ----
@app.get("/")
def root():
    return {
        "message": "Hedge Fund API aktív ✅",
        "status": "OK",
        "endpoints": ["/health", "/test-telegram"]
    }

@app.get("/health")
def health():
    return {"status": "running"}

# ---- Teszt üzenet küldés Telegramra ----
@app.get("/test-telegram")
async def test_telegram():
    resp = await telegram_send("✅ Telegram kapcsolat OK – Hedge Fund API aktív!")
    ok = bool(resp.get("ok"))
    return {"ok": ok, "telegram_response": resp}
    from fastapi import Query, HTTPException
import os

ALERT_TOKEN = os.getenv("ALERT_TOKEN", "")

@app.get("/notify")
async def notify(text: str = Query(..., min_length=1)):
    resp = await telegram_send(text)
    ok = bool(resp.get("ok"))
    return {"ok": ok, "telegram_response": resp}

@app.get("/notify-secure")
async def notify_secure(text: str = Query(..., min_length=1), token: str = ""):
    if not ALERT_TOKEN or token != ALERT_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    resp = await telegram_send(text)
    ok = bool(resp.get("ok"))
    return {"ok": ok, "telegram_response": resp}