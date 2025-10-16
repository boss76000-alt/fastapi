# system_status.py
from fastapi import APIRouter
import os, time

START_TS = time.time()
router = APIRouter()

@router.get("/status")
def status():
    return {
        "service": "Hedge Fund",
        "version": os.getenv("APP_VERSION", "0.5.0"),
        "uptime_sec": int(time.time() - START_TS),
        "email_to": os.getenv("ALERT_TO", ""),
        "notifier_url_present": bool(os.getenv("NOTIFIER_URL")),
        "env_ok": {
            "MARKETAUX_API_KEY": bool(os.getenv("MARKETAUX_API_KEY")),
            "SUBJECT_PREFIX": bool(os.getenv("SUBJECT_PREFIX")),
            "NOTIFIER_SECRET": bool(os.getenv("NOTIFIER_SECRET")),
        }
    }