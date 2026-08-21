import os
from typing import Optional

import requests
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# BREVO CONFIGURATION
# =========================================================

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _get_brevo_config():
    api_key = os.getenv("BREVO_API_KEY", "").strip()
    sender_email = os.getenv(
        "BREVO_SENDER_EMAIL",
        "",
    ).strip()

    return api_key, sender_email


# =========================================================
# SEND NOTIFICATION
# =========================================================

def send_notification(
    recipient_email: str,
    subject: str,
    message: str,
    recipient_name: Optional[str] = None,
) -> dict:
    """
    Send an email notification through Brevo.

    Returns a structured result instead of allowing
    email failures to crash the complete workflow.
    """

    # -----------------------------------------------------
    # VALIDATE RECIPIENT
    # -----------------------------------------------------

    if not recipient_email:
        return {
            "status": "SKIPPED",
            "message": (
                "Recipient email is not configured."
            ),
        }

    recipient_email = recipient_email.strip()

    if not recipient_email:
        return {
            "status": "SKIPPED",
            "message": (
                "Recipient email is empty."
            ),
        }

    # -----------------------------------------------------
    # LOAD BREVO CONFIG
    # -----------------------------------------------------

    api_key, sender_email = _get_brevo_config()

    if not api_key:
        print(
            "[EMAIL] BREVO_API_KEY is not configured."
        )

        return {
            "status": "FAILED",
            "message": (
                "BREVO_API_KEY is not configured."
            ),
        }

    if not sender_email:
        print(
            "[EMAIL] BREVO_SENDER_EMAIL is not configured."
        )

        return {
            "status": "FAILED",
            "message": (
                "BREVO_SENDER_EMAIL is not configured."
            ),
        }

    # -----------------------------------------------------
    # PREPARE PAYLOAD
    # -----------------------------------------------------

    recipient = {
        "email": recipient_email,
    }

    if recipient_name:
        recipient["name"] = recipient_name

    payload = {
        "sender": {
            "email": sender_email,
            "name": "AI Business Automation",
        },
        "to": [
            recipient
        ],
        "subject": subject,
        "textContent": message,
    }

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    # -----------------------------------------------------
    # SEND THROUGH BREVO
    # -----------------------------------------------------

    try:

        print(
            f"[EMAIL] Sending notification to "
            f"{recipient_email}"
        )

        response = requests.post(
            BREVO_API_URL,
            headers=headers,
            json=payload,
            timeout=20,
        )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if 200 <= response.status_code < 300:

            try:
                response_data = response.json()
            except ValueError:
                response_data = {}

            message_id = (
                response_data.get("messageId")
                or response_data.get("message_id")
            )

            print(
                "[EMAIL] Brevo notification sent "
                f"successfully. "
                f"message_id={message_id}"
            )

            return {
                "status": "SENT",
                "message": (
                    "Email notification sent "
                    "successfully."
                ),
                "message_id": message_id,
                "recipient": recipient_email,
            }

        # -------------------------------------------------
        # BREVO ERROR
        # -------------------------------------------------

        try:
            error_data = response.json()
        except ValueError:
            error_data = response.text

        print(
            "[EMAIL] Brevo request failed. "
            f"status={response.status_code}, "
            f"response={error_data}"
        )

        return {
            "status": "FAILED",
            "message": (
                "Brevo email delivery failed."
            ),
            "http_status": response.status_code,
            "details": error_data,
            "recipient": recipient_email,
        }

    # -----------------------------------------------------
    # REQUEST ERROR
    # -----------------------------------------------------

    except requests.RequestException as exc:

        print(
            "[EMAIL] Brevo connection error: "
            f"{repr(exc)}"
        )

        return {
            "status": "FAILED",
            "message": (
                "Unable to connect to Brevo."
            ),
            "details": str(exc),
            "recipient": recipient_email,
        }

    # -----------------------------------------------------
    # UNEXPECTED ERROR
    # -----------------------------------------------------

    except Exception as exc:

        print(
            "[EMAIL] Unexpected email error: "
            f"{repr(exc)}"
        )

        return {
            "status": "FAILED",
            "message": (
                "Unexpected email notification error."
            ),
            "details": str(exc),
            "recipient": recipient_email,
        }