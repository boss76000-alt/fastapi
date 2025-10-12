# email_resend.py — Resend HTTP API e-mail küldő
import os, requests

RESEND_API = "https://api.resend.com/emails"

def send_email_resend(to_email: str, subject: str, html: str, from_email: str = None):
api_key = os.getenv("RESEND_API_KEY", "")
from_addr = from_email or os.getenv("EMAIL_FROM", "")

if not api_key:
return False, "Missing RESEND_API_KEY"
if not to_email:
return False, "Missing recipient"

headers = {
"Authorization": f"Bearer {api_key}",
"Content-Type": "application/json",
}

payload = {
"from": from_addr,
"to": [to_email],
"subject": subject,
"html": html,
}

try:
r = requests.post(RESEND_API, headers=headers, json=payload)
if r.status_code in (200, 201):
return True, r.text
return False, f"HTTP {r.status_code}: {r.text}"
except Exception as e:
return False, str(e)
