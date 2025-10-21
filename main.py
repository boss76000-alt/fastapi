from fastapi import FastAPI, HTTPException
import os, time
import httpx

app = FastAPI(title="Hedge Fund – minimal")

START_TS = time.time()

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
        "uptime_seconds": int(time.time() - START_TS),
        "telegram_bot": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "chat_id_set": bool(os.getenv("TELEGRAM_CHAT_ID")),
        "marketaux_key": bool(os.getenv("MARKETAUX_API_TOKEN")),
    }

@app.post("/test/telegram")
def test_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN vagy TELEGRAM_CHAT_ID hiányzik")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": "✅ Railway teszt: működöm."}
    try:
        r = httpx.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Telegram hiba: {e}")
    return {"ok": True}

@app.get("/news/sample")
def news_sample(limit: int = 1):
    """
    Egyszerű Marketaux próba — safe param kezeléssel, hogy ne legyen 400.
    Csak 1–2 cikket kérünk, fix, könnyű szűréssel.
    """
    api_key = os.getenv("MARKETAUX_API_TOKEN")
    if not api_key:
        raise HTTPException(status_code=400, detail="MARKETAUX_API_TOKEN hiányzik")

    params = {
        "api_token": api_key,
        "limit": max(1, min(limit, 3)),   # 1..3
        "language": "en",
        "countries": "us",
        "sort": "published_at"
    }
    try:
        r = httpx.get("https://api.marketaux.com/v1/news/all", params=params, timeout=15)
        if r.status_code == 401:
            # Emberbarát üzenet, hogy a kulcs él-e
            return {"detail": {"marketaux_error": r.json()}}
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Marketaux hiba: {e}")

    data = r.json()
    # Visszaadunk egy könnyen olvasható mintát
    items = []
    for it in (data.get("data") or [])[:params["limit"]]:
        items.append({
            "title": it.get("title"),
            "source": it.get("source"),
            "published_at": it.get("published_at"),
            "url": it.get("url")
        })
    return {"count": len(items), "items": items}