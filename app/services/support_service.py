import json
import os
from typing import Dict, Any

from dotenv import load_dotenv
from google import genai

load_dotenv()


# =========================================================
# GEMINI CLIENT
# =========================================================

def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(api_key=api_key)


# =========================================================
# CLEAN JSON
# =========================================================

def _clean_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    return text


# =========================================================
# CUSTOMER SUPPORT ANALYSIS
# =========================================================

def analyze_customer_support(
    customer_email: str,
    subject: str,
    message: str
) -> Dict[str, Any]:

    if not customer_email:
        raise ValueError(
            "Customer email is required."
        )

    if not message or not message.strip():
        raise ValueError(
            "Customer message is required."
        )

    prompt = f"""
You are an AI Customer Support Automation Assistant.

Analyze the customer support message below.

Return ONLY valid JSON.

Required structure:

{{
    "category": "General, Sales, Billing, Technical, Complaint, Refund, Account, Security, or Other",
    "priority": "LOW, MEDIUM, HIGH, or CRITICAL",
    "intent": "Clear description of what the customer wants",
    "summary": "Short summary of the customer's issue",
    "sentiment": "Positive, Neutral, or Negative",
    "suggested_reply": "Professional customer-facing response",
    "recommended_action": "AUTOMATED_RESPONSE, SALES_FOLLOW_UP, SUPPORT_FOLLOW_UP, ESCALATE_TO_HUMAN, or SECURITY_ESCALATION",
    "confidence_score": 0.0
}}

Rules:

1. Do not invent information.
2. Use CRITICAL for security incidents, account compromise,
   unauthorized transactions, or other urgent safety/security issues.
3. Use HIGH for serious complaints, payment problems,
   refund issues, or urgent customer-impacting problems.
4. Use MEDIUM for sales enquiries, product questions,
   technical questions, or issues requiring staff follow-up.
5. Use LOW for simple informational/general questions.
6. Use ESCALATE_TO_HUMAN when human intervention is required.
7. Use SECURITY_ESCALATION for account compromise or
   unauthorized payment/security incidents.
8. The suggested reply must be professional and concise.
9. confidence_score must be between 0.0 and 1.0.

Customer email:
{customer_email}

Subject:
{subject}

Customer message:
{message}
"""

    try:

        client = _get_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result_text = response.text.strip()

        result_text = _clean_json(
            result_text
        )

        result = json.loads(
            result_text
        )

        category = str(
            result.get(
                "category",
                "Other"
            )
        ).strip()

        priority = str(
            result.get(
                "priority",
                "MEDIUM"
            )
        ).upper().strip()

        intent = str(
            result.get(
                "intent",
                "Customer support request"
            )
        ).strip()

        summary = str(
            result.get(
                "summary",
                "Customer support request received."
            )
        ).strip()

        sentiment = str(
            result.get(
                "sentiment",
                "Neutral"
            )
        ).strip()

        suggested_reply = str(
            result.get(
                "suggested_reply",
                "Thank you for contacting us. "
                "Our support team will review your request."
            )
        ).strip()

        recommended_action = str(
            result.get(
                "recommended_action",
                "SUPPORT_FOLLOW_UP"
            )
        ).upper().strip()

        confidence_score = float(
            result.get(
                "confidence_score",
                0.75
            )
        )

        confidence_score = max(
            0.0,
            min(
                1.0,
                confidence_score
            )
        )

        return {
            "category": category,
            "priority": priority,
            "intent": intent,
            "summary": summary,
            "sentiment": sentiment,
            "suggested_reply": suggested_reply,
            "recommended_action": recommended_action,
            "confidence_score": confidence_score,
            "analysis_source": "GEMINI"
        }

    except Exception as exc:

        print(
            f"Customer support AI analysis unavailable: "
            f"{repr(exc)}"
        )

        return {
            "category": "Other",
            "priority": "MEDIUM",
            "intent": "Customer support request",
            "summary": (
                "The customer support request was received "
                "but AI analysis was unavailable."
            ),
            "sentiment": "Neutral",
            "suggested_reply": (
                "Thank you for contacting us. "
                "Our support team will review your request."
            ),
            "recommended_action": "SUPPORT_FOLLOW_UP",
            "confidence_score": 0.0,
            "analysis_source": "LOCAL_FALLBACK",
            "fallback_reason": "Gemini API unavailable."
        }