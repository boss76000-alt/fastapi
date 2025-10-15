# email_notifier.py
import os, json, requests

NOTIFIER_URL = os.getenv("NOTIFIER_URL", "").strip()
NOTIFIER_SECRET = os.getenv("NOTIFIER_SECRET", "").strip()

def send_email(subject: str, text: str = "", html: str = "", to: str | None = None, cc: str = "", bcc: str = "") -> tuple[int, str]:
    """
    Google Apps Script webhook hívása JSON POST-tal.
    """
    if not NOTIFIER_URL or not NOTIFIER_SECRET:
        return 500, "Missing NOTIFIER_URL or NOTIFIER_SECRET"

    payload = {
        "secret": NOTIFIER_SECRET,
        "to": (to or os.getenv("ALERT_TO", "").strip()),
        "subject": subject,
        "text": text or "",
        "html": html or "",
        "cc": cc or "",
        "bcc": bcc or ""
    }
    try:
        r = requests.post(NOTIFIER_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=20)
        return r.status_code, r.text[:500]
    except Exception as e:
        return 500, f"EXC: {e}"