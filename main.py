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
    
        
# --- Marketaux teszt endpoint (CSERE BLOKK KEZDETE) ---
from datetime import datetime, timedelta
import os
import requests
from fastapi import HTTPException

@app.get("/test_marketaux")
def test_marketaux():
    api_key = os.getenv("MARKETAUX_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing MARKETAUX_API_KEY")

    symbols = os.getenv("NEWS_SYMBOLS", "AAPL,MSFT")
    keywords = os.getenv("NEWS_KEYWORDS", "").strip()
    since_days = int(os.getenv("NEWS_SINCE_DAYS", "7"))

    # vesszők szóközre cserélése, hogy az API elfogadja
    if "," in keywords:
        keywords = keywords.replace(",", " ")

    published_after = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    url = "https://api.marketaux.com/v1/news"
    params = {
        "api_token": api_key,
        "symbols": symbols,
        "language": "en",
        "limit": 5,
        "published_after": published_after,
        "filter_entities": "true",
    }
    if keywords:
        params["search"] = keywords

    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except requests.HTTPError as e:
        raise HTTPException(status_code=resp.status_code, detail=f"Marketaux request failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Marketaux request error: {e}")

    # --- domain blacklist ---
    items = payload.get("data") or payload.get("sample") or []
    blacklist = [d.strip().lower() for d in os.getenv("NEWS_SOURCES_BLACKLIST", "").split(",") if d.strip()]
    def blocked(it):
        src = (it.get("source") or "").lower()
        url_ = (it.get("url") or "").lower()
        return any(b in src or b in url_ for b in blacklist)

    filtered = [it for it in items if not blocked(it)]
    return {"ok": True, "count": len(filtered), "sample": (filtered[:1] if filtered else [])}
# --- Marketaux teszt endpoint (CSERE BLOKK VÉGE) ---
