# email_notifier.py — Google Apps Script webhook hívó

import os, json, requests

NOTIFIER_URL = os.getenv("NOTIFIER_URL", "")
NOTIFIER_SECRET = os.getenv("NOTIFIER_SECRET", "")
DEFAULT_TO = os.getenv("ALERT_TO", "")

def send_email(subject: str, text: str = "", html: str = "", to: str = None, cc: str = "", bcc: str = ""):
    to = to or DEFAULT_TO
    payload = {
        "secret": NOTIFIER_SECRET,
        "to": to,
        "subject": subject,
        "text": text,
        "html": html,
        "cc": cc,
        "bcc": bcc,
    }
    try:
        r = requests.post(NOTIFIER_URL, headers={"Content-Type": "application/json"},
                          data=json.dumps(payload), timeout=15)
        return r.status_code, r.text
    except Exception as e:
        return 500, f"request error: {e}"