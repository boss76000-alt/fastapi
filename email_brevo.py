# email_brevo.py
import os, httpx

BREVO_API = "https://api.brevo.com/v3/smtp/email"
API_KEY = os.getenv("BREVO_API_KEY", "")
FROM_EMAIL = os.getenv("EMAIL_FROM", "")
TO_EMAIL = os.getenv("ALERT_TO", "")

def send_email(subject: str, text: str = "", html: str = ""):
    if not API_KEY or not FROM_EMAIL or not TO_EMAIL:
        return 400, "Hiányzó env: BREVO_API_KEY / EMAIL_FROM / ALERT_TO"

    payload = {
        "sender": {"email": FROM_EMAIL, "name": "Hedge Fund"},
        "to": [{"email": TO_EMAIL}],
        "subject": subject,
        "textContent": text or None,
        "htmlContent": html or None,
    }
    headers = {"api-key": API_KEY, "accept": "application/json", "content-type": "application/json"}

    try:
        r = httpx.post(BREVO_API, json=payload, headers=headers, timeout=20)
        ok = 200 <= r.status_code < 300
        return (200 if ok else r.status_code), (r.text if not ok else "OK")
    except Exception as e:
        return 500, f"Brevo hiba: {e}"