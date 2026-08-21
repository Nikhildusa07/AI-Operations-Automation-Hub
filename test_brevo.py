import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")

# CHANGE ONLY THIS EMAIL
TEST_EMAIL = "dussanikhil7@gmail.com"

print("\n========== BREVO EMAIL TEST ==========")
print("API Key loaded:", bool(API_KEY))
print("Sender:", SENDER_EMAIL)
print("Recipient:", TEST_EMAIL)

if not API_KEY:
    print("❌ BREVO_API_KEY missing in .env")
    raise SystemExit

if not SENDER_EMAIL:
    print("❌ BREVO_SENDER_EMAIL missing in .env")
    raise SystemExit

payload = {
    "sender": {
        "email": SENDER_EMAIL,
        "name": "AI Business Automation"
    },
    "to": [
        {
            "email": TEST_EMAIL,
            "name": "Test User"
        }
    ],
    "subject": "AI Business Automation - Brevo Test",
    "textContent": """
This is a direct test email from the
AI Business Automation project.

If you received this email, Brevo email sending is working correctly.
"""
}

headers = {
    "accept": "application/json",
    "api-key": API_KEY,
    "content-type": "application/json"
}

try:
    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers=headers,
        json=payload,
        timeout=20
    )

    print("\nHTTP STATUS:", response.status_code)
    print("BREVO RESPONSE:", response.text)

    if 200 <= response.status_code < 300:
        print("\n✅ EMAIL SENT SUCCESSFULLY")
        print("Check your inbox/spam folder.")
    else:
        print("\n❌ BREVO REJECTED THE EMAIL")

except Exception as e:
    print("\n❌ CONNECTION ERROR")
    print(e)