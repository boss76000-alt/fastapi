import os
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException
import httpx

APP_START = datetime.now(timezone.utc)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
MARKETAUX_KEY = os.getenv("MARKETAUX_API_TOKEN", "")

app = FastAPI(title="HedgeFund Mini API")


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
        "uptime_seconds": int((datetime.now(timezone.utc) - APP_START).total_seconds()),
        "telegram_bot": bool(TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(TELEGRAM_CHAT_ID),
        "marketaux_key": bool(MARKETAUX_KEY),
    }


@app.post("/test/telegram")
async def test_telegram():
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        raise HTTPException(status_code=400, detail="Telegram env vars missing")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "✅ Telegram kapcsolat OK — Hedge Fund API aktív!"
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload)
        try:
            data = r.json()
        except Exception:
            data = {"text": r.text}
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail={"telegram_error": data})
    return {"ok": True, "telegram_response": data}


@app.get("/news/sample")
async def news_sample(limit: int = 1):
    """
    Egyszerű Marketaux próba — safe param kezeléssel, hogy ne legyen 400.
    Csak 1-2 cikket kérünk, fix, könnyű szűréssel.
    """
    if not MARKETAUX_KEY:
        raise HTTPException(status_code=400, detail="MARKETAUX_API_TOKEN hiányzik")

    # 48 órán belüli cikkek — ISO8601 UTC, pontos formátum
    published_after = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")

    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "api_token": MARKETAUX_KEY,
        "language": "en",
        "limit": max(1, min(limit, 5)),
        "published_after": published_after,
        # KEZDJÜK EGYSZERŰEN: nincs bonyolult 'search', nincs 'symbols' első körben
        # ha ez stabil, akkor bővítjük
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params)

    # próbáljunk JSON-t olvasni, de ha nem megy, adjuk vissza a textet
    try:
        payload = r.json()
    except Exception:
        payload = {"raw": r.text}

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail={"marketaux_error": payload})

    # Rövid, barátságos válasz
    sample = payload.get("data") or payload.get("news") or payload.get("sample") or []
    return {
        "ok": True,
        "count": len(sample) if isinstance(sample, list) else 0,
        "sample": sample[:1] if isinstance(sample, list) else sample
    }


if __name__ == "__main__":
    # Railway PORT-ot használunk, különben 8000
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    
    from typing import Optional, List
from fastapi import Query

@app.get("/news/headlines", summary="Marketaux hírek (angol, formázott)")
async def news_headlines(
    limit: int = Query(5, ge=1, le=20),
    symbols: Optional[str] = Query(None, description="Pl.: AAPL,MSFT,TSLA"),
    search: Optional[str] = Query(None, description="Pl.: earnings OR guidance"),
    hours: int = Query(24, ge=1, le=72, description="Mióta visszafelé nézzünk (óra)"),
    min_relevance: float = Query(0.0, ge=0.0, le=1.0),
    notify: bool = Query(False, description="Küldjön-e Telegram értesítést")
):
    token = os.getenv("MARKETAUX_API_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="MARKETAUX_API_TOKEN hiányzik")

    # published_after ISO idő (UTC)
    since = datetime.utcnow() - timedelta(hours=hours)
    published_after = since.replace(microsecond=0).isoformat() + "Z"

    params = {
        "api_token": token,
        "language": "en",
        "limit": str(limit),
        "published_after": published_after,
        "filter_entities": "true",
    }

    if symbols:
        # Marketaux vesszővel elválasztott listát vár
        params["symbols"] = symbols.replace(" ", "")
    if search:
        params["search"] = search
    # relevance score 0..1 skála – ha >0, akkor beállítjuk
    if min_relevance > 0:
        params["relevance_score.gte"] = str(min_relevance)

    url = "https://api.marketaux.com/v1/news/all"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, params=params)
            if r.status_code == 401:
                return {"detail": "marketaux_error", "error": {"code": "invalid_api_token", "message": "Érvénytelen API token."}}
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Marketaux kérés hiba: {str(e)}")

    # Átalakítjuk rövid, tiszta listává
    items = []
    for it in data.get("data", [])[:limit]:
        items.append({
            "title": it.get("title"),
            "source": it.get("source"),
            "published_at": it.get("published_at"),
            "url": it.get("url"),
            "language": it.get("language"),
        })

    # Opcionális Telegram értesítés (max 3 cikk, hogy ne spam-eljen)
    if notify and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        lines = []
        for art in items[:3]:
            lines.append(f"• {art['title']} ({art['source']})\n{art['url']}")
        text = "📰 Friss hírek (Marketaux):\n" + "\n\n".join(lines) if lines else "Nincs friss angol hír."
        try:
            await send_telegram_message(text)
        except Exception as e:
            # Nem dobjuk el a választ, csak jelezzük
            return {"items": items, "telegram": {"sent": False, "error": str(e)}}

        return {"items": items, "telegram": {"sent": True}}

    return {"items": items}