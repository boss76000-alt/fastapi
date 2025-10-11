# v0.4.1 – Hedge Fund API (health + email test)
import os, ssl, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI

app = FastAPI(title="Hedge Fund API", version="0.4.1")

# --------- Helpers ----------
def try_send_email():
    smtp_server = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    receiver_email = os.getenv("ALERT_TO", sender_email)
    subject_prefix = os.getenv("SUBJECT_PREFIX", "[HedgeFund]")

    if not sender_email or not password or not receiver_email:
        return False, "Missing SMTP_USER/SMTP_PASS/ALERT_TO"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{subject_prefix} Email Test v0.4.1"
    msg["From"] = os.getenv("EMAIL_FROM", sender_email)
    msg["To"] = receiver_email

    text = "✅ Hedge Fund API v0.4.1 – SMTP teszt.\nHa ezt látod, a küldés ok."
    html = """\
    <html><body style="font-family:monospace;background:#0f111a;color:#c8e1ff">
      <h2>✅ Hedge Fund API v0.4.1 – Email Test</h2>
      <p><b>Status:</b> RUNNING 🟢<br><b>Layer:</b> CORE-ALERT / MAIL PIPELINE</p>
    </body></html>"""
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(smtp_server, port, timeout=10) as server:
            server.starttls(context=context)
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, str(e)

# --------- Endpoints ----------
@app.get("/")
def root():
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut v0.4.1 alatt – Email modul aktív.",
        "endpoints": {"health": "/health", "email_test": "/alerts/email_test"},
    }

@app.get("/health")
def health():
    return {"status": "running", "marketaux_key_present": bool(os.getenv("MARKETAUX_API_KEY"))}

@app.get("/alerts/email_test")
def alerts_email_test():
    ok, error = try_send_email()
    return {"ok": bool(ok), "endpoint": "/alerts/email_test", "error": None if ok else error}