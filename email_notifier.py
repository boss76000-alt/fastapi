# email_notifier.py
import os, logging, httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

NOTIFIER_URL    = os.getenv("NOTIFIER_URL")
NOTIFIER_SECRET = os.getenv("NOTIFIER_SECRET")
ALERT_TO        = os.getenv("ALERT_TO", "boss760000@gmail.com")
SUBJECT_PREFIX  = os.getenv("SUBJECT_PREFIX", "HedgeFund")

async def _send_email(subject: str, text: str = "", html: str = "", to: str | None = None,
                      cc: str | None = None, bcc: str | None = None):
    if not NOTIFIER_URL or not NOTIFIER_SECRET:
        raise HTTPException(500, "Webhook nincs beállítva (NOTIFIER_URL / NOTIFIER_SECRET).")

    payload = {
        "secret":  NOTIFIER_SECRET,
        "to":      to or ALERT_TO,
        "subject": f"{SUBJECT_PREFIX} | {subject}",
        "text":    text or "",
        "html":    html or ""
    }
    if cc:  payload["cc"]  = cc
    if bcc: payload["bcc"] = bcc

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(NOTIFIER_URL, json=payload, headers={"Content-Type": "application/json"})
    if r.status_code >= 300:
        logging.error("Notifier hiba: %s %s", r.status_code, r.text)
        raise HTTPException(502, "Notifier válasz hibás.")

    return {"ok": True}

@router.get("/notify/test")
async def notify_test():
    return await _send_email("teszt", html="<b>FastAPI → Gmail OK</b>")

@router.post("/notify")
async def notify(subject: str, text: str = "", html: str = ""):
    return await _send_email(subject, text=text, html=html)