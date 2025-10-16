# email_brevo.py
import os, requests

BREVO_KEY = os.getenv("BREVO_API_KEY")
ALERT_TO = os.getenv("ALERT_TO", "")
SUBJ_PREFIX = os.getenv("SUBJECT_PREFIX", "HedgeFund")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
HEADERS = {
    "api-key": BREVO_KEY,
    "accept": "application/json",
    "content-type": "application/json",
}

def send_email(subject: str, text: str = "", html: str = "") -> tuple[int, str]:
    payload = {
        "sender": {"name": "Hedge Fund Alerts", "email": "boss760000@gmail.com"},
        "to": [{"email": ALERT_TO}],
        "subject": f"{SUBJ_PREFIX} | {subject}",
        "textContent": text or None,
        "htmlContent": html or None,
    }
    r = requests.post(BREVO_URL, json=payload, headers=HEADERS, timeout=20)
    try:
        data = r.json()
    except Exception:
        data = r.text
    return r.status_code, str(data)[:400]