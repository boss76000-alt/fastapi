# main.py — Hedge Fund webhook email teszt (Resend nélkül)
from fastapi import FastAPI
from email_notifier import send_email
import os

app = FastAPI(title="Hedge Fund API", version="1.0")

@app.get("/")
def root():
    return {
        "message": "Hedge Fund API aktív",
        "status": "OK",
        "endpoints": ["/health", "/test-email"]
    }

@app.get("/health")
def health():
    return {"status": "running", "MARKETAUX_API_KEY_present": bool(os.getenv("MARKETAUX_API_KEY"))}

@app.get("/test-email")
def test_email():
    code, msg = send_email(
        subject="Railway → Gmail webhook TESZT",
        text="Ez egy próba a /test-email végpontról.",
        html="<b>Webhook teszt OK a Railway-ről</b>"
    )
    return {"status": code, "msg": msg}