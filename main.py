import os
import json
from datetime import datetime
from typing import Optional

import requests
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

# --- App init ---
app = FastAPI(title="Hedge Fund API", version="1.0")

# --- Env vars ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY", "").strip()

# --- Helpers ---
def tg_enabled() -> bool:
    return bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)

def tg_send(text: str) -> dict:
    """
    Egyszerű Telegram helper. Visszaadja a Telegram API válaszát dict-ben.
    """
    if not tg_enabled():
        return {"ok": False, "reason": "telegram_not_configured"}

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

# --- Health / status ---
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/status")
def status():
    return {
        "status": "running",
        "telegram_bot": bool(TELEGRAM_TOKEN),
        "chat_id_set": bool(TELEGRAM_CHAT_ID),
        "marketaux_key": bool(MARKETAUX_API_KEY),
    }

@app.get("/running")
def running():
    # kompatibilitás a korábbi ellenőrzéssel
    return {"status": "running", "telegram_bot": tg_enabled(), "chat_id_set": bool(TELEGRAM_CHAT_ID)}

# --- Telegram teszt ---
@app.get("/test-telegram")
def test_telegram(msg: Optional[str] = Query(default="✅ Telegram kapcsolat OK — Hedge Fund API aktív!")):
    """
    Küld egy próbaüzenetet a beállított TELEGRAM_CHAT_ID-re.
    """
    if not tg_enabled():
        return JSONResponse(
            status_code=400,
            content={"ok": False, "detail": "Telegram nincs konfigurálva (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)."},
        )

    resp = tg_send(msg)
    ok = bool(resp.get("ok"))
    return {"ok": ok, "telegram_response": resp}

# --- Marketaux teszt ---
@app.get("/test-marketaux")
def test_marketaux(
    limit: int = Query(default=1, ge=1, le=5),
    language: str = Query(default="en"),
):
    """
    Egyszerű Marketaux próbahívás. A /news/all végpontot hívja meg minimális,
    minden csomagra érvényes paraméterekkel (limit, language).
    """
    if not MARKETAUX_API_KEY:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "detail": "MARKETAUX_API_KEY nincs beállítva."},
        )

    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "api_token": MARKETAUX_API_KEY,
        "limit": limit,
        "language": language,
        # Szándékosan NINCS published_after (sok csomagnál 30 napos limitet dob 400-zal)
    }

    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "detail": f"Marketaux request failed: {r.status_code}",
                    "url": r.url,
                    "body": r.text[:500],
                },
            )
        data = r.json()
        count = len(data.get("data", [])) if isinstance(data, dict) else None
        return {"ok": True, "count": count, "sample": (data.get("data", [])[:1] if isinstance(data, dict) else None)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "detail": f"Marketaux exception: {str(e)}"},
        )

# --- Gyökér: opcionálisan visszaadjuk az elérhető végpontokat ---
@app.get("/")
def root():
    return {
        "message": "Hedge Fund API aktív",
        "status": "OK",
        "endpoints": ["/health", "/status", "/running", "/test-telegram", "/test-marketaux"],
        "server_time": datetime.utcnow().isoformat() + "Z",
    }