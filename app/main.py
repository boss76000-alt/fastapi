from fastapi import FastAPI
from app.settings import settings
from app.telegram import send_telegram
from app.news import get_news, to_message

app = FastAPI(title="Hedge Fund – minimal")

@app.get("/")
def root():
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/status")
def status():
    return {
        "status": "running",
        "telegram_bot": bool(settings.TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(settings.TELEGRAM_CHAT_ID),
        "marketaux_key": bool(settings.MARKETAUX_API_TOKEN),
        "blocked_domains": settings.NEWS_BLOCKED_DOMAINS,
        "max_age_hours": settings.NEWS_MAX_AGE_HOURS,
        "cache_seconds": settings.CACHE_SECONDS,
    }

@app.post("/test/telegram")
async def test_telegram():
    ok = await send_telegram("✅ Telegram test OK")
    return {"ok": ok}

@app.get("/news/auto")
async def news_auto(limit: int = 1):
    data = await get_news(limit)
    # ha Marketaux hiba érkezik, passzold tovább
    if "detail" in data and "marketaux_error" in data["detail"]:
        return data

    if data["count"] > 0:
        await send_telegram(to_message(data["items"]))
    return data