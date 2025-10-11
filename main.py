# =========================================================
# Hedge Fund API v0.4.1 – EMAIL TEST + CORE
# =========================================================

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os, smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- FastAPI inicializálás ---
app = FastAPI(title="Hedge Fund API", version="0.4.1")

# --- Email küldő funkció ---
def send_test_email():
    smtp_server = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    receiver_email = os.getenv("ALERT_TO", sender_email)
    subject_prefix = os.getenv("SUBJECT_PREFIX", "[HedgeFund]")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{subject_prefix} Email Test v0.4.1"
    msg["From"] = os.getenv("EMAIL_FROM", sender_email)
    msg["To"] = receiver_email

    text = """✅ Hedge Fund API v0.4.1 teszt sikeresen elindult!
Ez az e-mail igazolja, hogy az SMTP kapcsolat működik.
"""
    html = """\
    <html>
      <body style="font-family: monospace; background-color:#0f111a; color:#c8e1ff;">
        <h2>✅ Hedge Fund API v0.4.1 – Email Test</h2>
        <p>Az SMTP modul sikeresen inicializálva.<br>
        <b>Status:</b> RUNNING 🟢<br>
        <b>Layer:</b> CORE-ALERT / MAIL PIPELINE</p>
        <hr>
        <p style="font-size:12px; color:#888;">© Hedge Fund Core | v0.4.1</p>
      </body>
    </html>
    """

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port, timeout=20) as server:
            server.starttls(context=context)
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("✅ Email sikeresen elküldve!")
        return True
    except Exception as e:
        print("❌ Hiba az e-mail küldés során:", e)
        return False

# --- Endpoint: teszt email ---
@app.get("/alerts/email_test")
def alerts_email_test():
    ok = send_test_email()
    return JSONResponse({"ok": bool(ok), "endpoint": "/alerts/email_test"})

# --- Endpoint: API health ---
@app.get("/health")
def health():
    return {"status": "running", "marketaux_key_present": bool(os.getenv("MARKETAUX_API_KEY"))}

# --- Root info ---
@app.get("/")
def root():
    return {
        "greeting": "Hello, Hedge Fund!",
        "message": "FastAPI fut v0.4.1 alatt – Email modul aktív.",
        "endpoints": {
            "health": "/health",
            "email_test": "/alerts/email_test"
        }
    }