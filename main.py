# main.py — Hedge Fund API v0.4.2 (Resend e-mail teszt)
from fastapi import FastAPI
from email_resend import send_email_resend
import os

app = FastAPI(title="Hedge Fund API", version="0.4.2")

@app.get("/")
def root():
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut v0.4.2 alatt — Email modul (Resend) aktív.",
        "endpoints": {
            "health": "/health",
            "email_test": "/alerts/email_test",
        },
    }

@app.get("/health")
def health():
    return {"status": "running", "marketaux_key_present": bool(os.getenv("MARKETAUX_API_KEY"))}

@app.get("/alerts/email_test")
def alerts_email_test():
    subj_prefix = os.getenv("SUBJECT_PREFIX", "[HedgeFund]")
    to_email = os.getenv("ALERT_TO", "")
    subject = f"{subj_prefix} Email Test (Resend)"

    html = """
    <html>
      <body style="font-family:monospace;background:#0f111a;color:#c8e1ff;">
        <h2>✅ Hedge Fund – Email Test via Resend</h2>
        <p><b>Status:</b> RUNNING 🟢<br>
           <b>Layer:</b> CORE-ALERT / MAIL PIPELINE</p>
        <hr>
        <p style="font-size:12px;color:#888;">© Hedge Fund Core | v0.4.2</p>
      </body>
    </html>
    """

    ok, info = send_email_resend(to_email=to_email, subject=subject, html=html)
    return {"ok": ok, "endpoint": "/alerts/email_test", "info": info[:300]}