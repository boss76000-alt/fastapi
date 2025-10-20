from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional, Set
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
import asyncio
import httpx
import logging

# -------------------------
# Config (ENV)
# -------------------------
class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    MARKETAUX_API_TOKEN: Optional[str] = None

    NEWS_SYMBOLS: str = "AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL,META,BTC,ETH,SPY"
    NEWS_SEARCH: str = "earnings,merger,acquisition,guidance,dividend,SEC,probe,short seller,AI,chip,antitrust"
    NEWS_LIMIT: int = 5
    NEWS_SINCE_HOURS: int = 24

    ENABLE_ALERTS: bool = False            # ütemezett push default: OFF
    ALERT_INTERVAL_MIN: int = 10           # ha bekapcsolod
    LOG_LEVEL: str = "INFO"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("app")

# -------------------------
# Helpers
# -------------------------
def _split_csv(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x and x.strip()]

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _iso_z(dt: datetime) -> str:
    # Marketaux szereti az ISO8601-Z formát: 2025-01-01T00:00:00Z
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _norm_search(search_csv: str) -> str:
    """
    Kulcsszavakat normalizáljuk:
    - CSV → lista
    - belső szóközök '+'-ra
    - végül mindet '+'-al fűzzük (URL-ben httpx úgyis kódolja)
    """
    items = _split_csv(search_csv)
    norm = [kw.replace(" ", "+") for kw in items]
    return "+".join(dict.fromkeys(norm))  # de-dup, sorrend megtartása

# -------------------------
# External clients
# -------------------------
async def marketaux_fetch():
    """
    Helyes endpoint: /v1/news/all
    Kötelező paramok: api_token, symbols, search, language, limit, published_after, filter_entities
    """
    if not settings.MARKETAUX_API_TOKEN:
        raise HTTPException(status_code=500, detail="Marketaux API token hiányzik (MARKETAUX_API_TOKEN).")

    url = "https://api.marketaux.com/v1/news/all"

    symbols = ",".join(_split_csv(settings.NEWS_SYMBOLS))
    search = _norm_search(settings.NEWS_SEARCH)
    published_after = _iso_z(_now_utc() - timedelta(hours=settings.NEWS_SINCE_HOURS))

    params = {
        "api_token": settings.MARKETAUX_API_TOKEN,
        "symbols": symbols,
        "search": search,
        "language": "en",
        "limit": str(settings.NEWS_LIMIT),
        "published_after": published_after,
        "filter_entities": "true"
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, params=params)
    if resp.status_code != 200:
        # Adjunk rövid, emberi hibát (status + részlet)
        text = resp.text[:500]
        raise HTTPException(status_code=resp.status_code,
                            detail=f"Marketaux request failed: {resp.status_code} — {text}")
    data = resp.json()
    return data

async def telegram_send(text: str):
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
        raise HTTPException(status_code=500, detail="Telegram token/chat id hiányzik.")
    api = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": text
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(api, json=payload)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code,
                            detail=f"Telegram send failed: {resp.status_code} — {resp.text[:300]}")
    rj = resp.json()
    # Rövidítés
    brief = {
        "ok": rj.get("ok", False),
        "message_id": rj.get("result", {}).get("message_id"),
        "date": rj.get("result", {}).get("date"),
        "text": rj.get("result", {}).get("text")
    }
    return brief

# -------------------------
# App & endpoints
# -------------------------
app = FastAPI(title="Hedge Fund API", version="1.0.0")

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/status")
async def status():
    return {
        "status": "running",
        "telegram_bot": bool(settings.TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(settings.TELEGRAM_CHAT_ID),
        "marketaux_key": bool(settings.MARKETAUX_API_TOKEN),
        "scheduler_running": False  # V1: only manual; ha bekapcsolod, állítjuk True-ra
    }

@app.get("/test/telegram")
async def test_telegram():
    text = "✅ Telegram kapcsolat OK — Hedge Fund API aktív!"
    res = await telegram_send(text)
    return {"ok": True, "telegram_response": res}

@app.get("/test/marketaux")
async def test_marketaux():
    data = await marketaux_fetch()
    # Rövid minta
    sample = None
    try:
        arr = data.get("data") or data.get("articles") or []
        if arr:
            first = arr[0]
            sample = {
                "uuid": first.get("uuid") or first.get("id"),
                "title": first.get("title"),
                "description": first.get("description"),
                "keywords": first.get("keywords"),
                "snippet": first.get("snippet") or first.get("summary"),
                "url": first.get("url"),
                "image_url": first.get("image_url"),
                "language": first.get("language"),
                "published_at": first.get("published_at"),
                "source": first.get("source"),
                "relevance_score": first.get("relevance_score"),
                "entities": first.get("entities", []),
                "similar": first.get("similar", [])
            }
    except Exception:
        sample = None
    count = len(data.get("data") or data.get("articles") or [])
    return {"ok": True, "count": count, "sample": sample}

# -------------------------
# (OPCIONÁLIS) Ütemezett riasztás – default: kikapcsolva
# -------------------------
scheduler = None
_seen_ids: Set[str] = set()

async def scheduled_pull_and_notify():
    try:
        data = await marketaux_fetch()
        articles = data.get("data") or data.get("articles") or []
        new_items = []
        for a in articles:
            uid = str(a.get("uuid") or a.get("id") or a.get("url"))
            if uid and uid not in _seen_ids:
                _seen_ids.add(uid)
                new_items.append(a)

        if not new_items:
            return

        # Küldjünk egy rövid összefoglalót (max 3 cím)
        lines = []
        for a in new_items[:3]:
            t = (a.get("title") or "")[:140]
            u = a.get("url") or ""
            lines.append(f"• {t}\n{u}")
        text = "📰 Új hírek Marketaux-ból:\n\n" + "\n\n".join(lines)
        await telegram_send(text)

    except HTTPException as he:
        logger.warning(f"Scheduler HTTP error: {he.detail}")
    except Exception as e:
        logger.exception(f"Scheduler error: {e}")

@app.on_event("startup")
async def on_startup():
    global scheduler
    if settings.ENABLE_ALERTS:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(scheduled_pull_and_notify, "interval", minutes=max(1, settings.ALERT_INTERVAL_MIN))
        scheduler.start()
        logger.info("Scheduler started.")

@app.on_event("shutdown")
async def on_shutdown():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)