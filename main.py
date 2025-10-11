# v0.4.2 – Hedge Fund API (health + email test via RESEND)
import os
import requests
from fastapi import FastAPI

app = FastAPI(title="Hedge Fund API", version="0.4.2")

# ------------ Email (HTTP, Resend) -------------
def send_email_resend(subject: str, text: str, html: str):
    api_key = os.getenv("RESEND_API_KEY", "")
    email_from = os.getenv("EMAIL_FROM", "onboarding@resend.dev")  # teszthez OK
    email_to = os.getenv("ALERT_TO")
    if not api_key or not email_to:
        return False, "Missing RESEND_API_KEY or ALERT_TO"

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "from": email_from,
                "to": [email_to],
                "subject": subject,
                "text": text,
                "html": html,
            },
            timeout=15,
        )
        if r.status_code in (200, 201):
            return True, "sent"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)

def email_test():
    prefix = os.getenv("SUBJECT_PREFIX", "[HedgeFund]")
    subject = f"{prefix} Email Test v0.4.2 (RESEND)"
    text = "✅ Hedge Fund API v0.4.2 – HTTP email teszt (Resend)."
    html = """<html><body style="font-family:monospace;background:#0f111a;color:#c8e1ff">
      <h2>✅ Hedge Fund API v0.4.2 – Email Test (Resend)</h2>
      <p><b>Status:</b> RUNNING 🟢<br><b>Layer:</b> CORE-ALERT / MAIL PIPELINE</p>
    </body></html>"""
    return send_email_resend(subject, text, html)

# ------------- Endpoints -------------
@app.get("/")
def root():
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut v0.4.2 alatt – Email modul HTTP-n.",
        "endpoints": {"health": "/health", "email_test": "/alerts/email_test"},
    }

@app.get("/health")
def health():
    return {"status": "running", "marketaux_key_present": bool(os.getenv("MARKETAUX_API_KEY"))}

@app.get("/alerts/email_test")
def alerts_email_test():
    ok, info = email_test()
    return {"ok": bool(ok), "endpoint": "/alerts/email_test", "provider": "RESEND", "info": info}