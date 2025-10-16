from fastapi import FastAPI
from email_brevo import send_email

app = FastAPI(title="Hedge Fund API", version="1.0")

@app.get("/")
def root():
    return {"message": "Hedge Fund API aktív", "status": "OK", "endpoints": ["/health", "/test-email"]}

@app.get("/health")
def health():
    import os
    return {
        "status": "running",
        "BREVO_KEY_present": bool(os.getenv("BREVO_API_KEY")),
        "ALERT_TO_present": bool(os.getenv("ALERT_TO")),
    }

@app.get("/test-email")
def test_email():
    code, msg = send_email(
        subject="Railway → Brevo TESZT",
        text="Ez egy Brevo (Sendinblue) teszt a /test-email végpontról.",
        html="<b>Brevo webhook teszt OK a Railway-ről</b>",
    )
    return {"status": code, "msg": msg}