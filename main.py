import os, requests
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(title="Hedge Fund – minimal")

MARKETAUX_TOKEN = os.getenv("MARKETAUX_API_TOKEN")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_marketaux(query: str | None, language: str, limit: int):
    if not MARKETAUX_TOKEN:
        raise HTTPException(status_code=500, detail="MARKETAUX_API_TOKEN missing")

    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "api_token": MARKETAUX_TOKEN,
        "limit": max(1, min(limit, 5)),   # óvatos limit
        "language": language or "en",
    }
    if query:
        params["query"] = query

    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail={"marketaux_error": r.json()})
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail={"marketaux_error": r.text})

    data = r.json()
    items = []
    for it in (data.get("data") or [])[:limit]:
        items.append({
            "title": it.get("title"),
            "source": it.get("source"),
            "published_at": it.get("published_at"),
            "url": it.get("url"),
        })
    return {"count": len(items), "items": items}

def send_telegram(text: str) -> None:
    if not (TG_TOKEN and TG_CHAT_ID):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": text, "disable_web_page_preview": True},
            timeout=10,
        )
    except Exception:
        pass

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
        "telegram_bot": bool(TG_TOKEN),
        "chat_id_set": bool(TG_CHAT_ID),
        "marketaux_key": bool(MARKETAUX_TOKEN),
    }

@app.get("/news/search")
def news_search(
    q: str | None = Query(default=None, description="Kulcsszó pl. AAPL OR NVDA"),
    language: str = Query(default="en", pattern="^[a-z]{2}$"),
    limit: int = Query(default=2, ge=1, le=5),
    send: bool = Query(default=False, description="Ha true, Telegramra is megy összefoglaló"),
):
    result = fetch_marketaux(q, language, limit)
    if send and result["count"] > 0:
        lines = [f"Top hírek ({language}, {result['count']} db):"]
        for i, it in enumerate(result["items"], start=1):
            lines.append(f"{i}. {it['title']} — {it['source']}\n{it['url']}")
        send_telegram("\n\n".join(lines))
    return result