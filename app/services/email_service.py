import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from google import genai


load_dotenv()


# =========================================================
# CONSTANTS
# =========================================================

EMAIL_CATEGORIES = {
    "Sales",
    "Support",
    "Complaint",
    "Recruitment",
    "Finance",
    "Technical",
    "General",
    "Urgent",
}

PRIORITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


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
# LOCAL FALLBACK CLASSIFIER
# =========================================================

def _local_email_analysis(
    subject: str,
    message: str,
) -> Dict[str, Any]:
    """
    Deterministic fallback used when Gemini is unavailable.
    """

    text = f"{subject} {message}".lower()

    # -----------------------------------------------------
    # CRITICAL / URGENT
    # -----------------------------------------------------

    critical_keywords = [
        "fraud",
        "hacked",
        "account compromised",
        "security breach",
        "unauthorized transaction",
        "unauthorized payment",
        "stolen",
        "data breach",
        "critical",
        "emergency",
    ]

    if any(keyword in text for keyword in critical_keywords):
        return {
            "category": "Urgent",
            "priority": "CRITICAL",
            "intent": "Security or urgent business issue",
            "summary": (
                "The message contains a critical issue "
                "requiring immediate attention."
            ),
            "sentiment": "Negative",
            "suggested_reply": (
                "Thank you for contacting us. "
                "Your request has been identified as urgent "
                "and has been escalated to the appropriate team "
                "for immediate review."
            ),
            "recommended_action": "ESCALATE_TO_HUMAN",
            "confidence_score": 0.92,
            "analysis_source": "LOCAL_FALLBACK",
        }

    # -----------------------------------------------------
    # COMPLAINT
    # -----------------------------------------------------

    complaint_keywords = [
        "complaint",
        "unhappy",
        "disappointed",
        "terrible service",
        "bad service",
        "poor service",
        "not satisfied",
        "refund",
        "wrong charge",
        "double charged",
    ]

    if any(keyword in text for keyword in complaint_keywords):
        return {
            "category": "Complaint",
            "priority": "HIGH",
            "intent": "Customer complaint",
            "summary": (
                "The customer has raised a complaint "
                "requiring review and follow-up."
            ),
            "sentiment": "Negative",
            "suggested_reply": (
                "Thank you for bringing this matter to our attention. "
                "We have received your complaint and our team will "
                "review it and get back to you with the next steps."
            ),
            "recommended_action": "CREATE_SUPPORT_TICKET",
            "confidence_score": 0.90,
            "analysis_source": "LOCAL_FALLBACK",
        }

    # -----------------------------------------------------
    # FINANCE
    # -----------------------------------------------------

    finance_keywords = [
        "invoice",
        "payment",
        "billing",
        "bill",
        "transaction",
        "tax",
        "finance",
        "refund",
        "salary",
        "expense",
        "payout",
        "payment failed",
    ]

    if any(keyword in text for keyword in finance_keywords):
        return {
            "category": "Finance",
            "priority": "MEDIUM",
            "intent": "Financial or billing request",
            "summary": (
                "The message concerns a financial, billing, "
                "payment, invoice, or transaction-related matter."
            ),
            "sentiment": "Neutral",
            "suggested_reply": (
                "Thank you for contacting us. "
                "We have received your financial or billing request "
                "and will review it with the appropriate team."
            ),
            "recommended_action": "FINANCE_FOLLOW_UP",
            "confidence_score": 0.88,
            "analysis_source": "LOCAL_FALLBACK",
        }

    # -----------------------------------------------------
    # RECRUITMENT
    # -----------------------------------------------------

    recruitment_keywords = [
        "job",
        "job application",
        "resume",
        "cv",
        "career",
        "recruitment",
        "interview",
        "vacancy",
        "position",
        "hiring",
        "employment",
    ]

    if any(keyword in text for keyword in recruitment_keywords):
        return {
            "category": "Recruitment",
            "priority": "MEDIUM",
            "intent": "Recruitment or employment enquiry",
            "summary": (
                "The message is related to recruitment, "
                "employment, or a job opportunity."
            ),
            "sentiment": "Neutral",
            "suggested_reply": (
                "Thank you for your interest. "
                "We have received your recruitment-related message "
                "and will review it with the appropriate team."
            ),
            "recommended_action": "RECRUITMENT_FOLLOW_UP",
            "confidence_score": 0.88,
            "analysis_source": "LOCAL_FALLBACK",
        }

    # -----------------------------------------------------
    # TECHNICAL
    # -----------------------------------------------------

    technical_keywords = [
        "bug",
        "error",
        "technical",
        "api",
        "server",
        "website not working",
        "application not working",
        "login error",
        "system failure",
        "software issue",
        "integration",
        "database",
    ]

    if any(keyword in text for keyword in technical_keywords):
        return {
            "category": "Technical",
            "priority": "HIGH",
            "intent": "Technical support request",
            "summary": (
                "The message reports a technical issue "
                "requiring investigation."
            ),
            "sentiment": "Negative",
            "suggested_reply": (
                "Thank you for reporting the technical issue. "
                "Our technical team will review the problem "
                "and investigate the next steps."
            ),
            "recommended_action": "CREATE_TECHNICAL_TICKET",
            "confidence_score": 0.89,
            "analysis_source": "LOCAL_FALLBACK",
        }

    # -----------------------------------------------------
    # SALES
    # -----------------------------------------------------

    sales_keywords = [
        "pricing",
        "price",
        "quote",
        "quotation",
        "purchase",
        "buy",
        "sales",
        "product",
        "demo",
        "plan",
        "package",
        "subscription",
    ]

    if any(keyword in text for keyword in sales_keywords):
        return {
            "category": "Sales",
            "priority": "MEDIUM",
            "intent": "Sales or product enquiry",
            "summary": (
                "The message appears to be a sales, "
                "pricing, product, or purchasing enquiry."
            ),
            "sentiment": "Neutral",
            "suggested_reply": (
                "Thank you for your interest. "
                "We have received your enquiry and our sales team "
                "will review it and get back to you."
            ),
            "recommended_action": "SALES_FOLLOW_UP",
            "confidence_score": 0.86,
            "analysis_source": "LOCAL_FALLBACK",
        }

    # -----------------------------------------------------
    # SUPPORT
    # -----------------------------------------------------

    support_keywords = [
        "support",
        "help",
        "issue",
        "problem",
        "unable",
        "cannot",
        "not working",
        "account",
        "profile",
        "assistance",
    ]

    if any(keyword in text for keyword in support_keywords):
        return {
            "category": "Support",
            "priority": "MEDIUM",
            "intent": "Customer support request",
            "summary": (
                "The message requests customer support "
                "or assistance with a business service."
            ),
            "sentiment": "Neutral",
            "suggested_reply": (
                "Thank you for contacting support. "
                "We have received your request and our team "
                "will review it and get back to you."
            ),
            "recommended_action": "CREATE_SUPPORT_TICKET",
            "confidence_score": 0.84,
            "analysis_source": "LOCAL_FALLBACK",
        }

    # -----------------------------------------------------
    # GENERAL
    # -----------------------------------------------------

    return {
        "category": "General",
        "priority": "LOW",
        "intent": "General business enquiry",
        "summary": (
            "The message appears to be a general business enquiry."
        ),
        "sentiment": "Neutral",
        "suggested_reply": (
            "Thank you for contacting us. "
            "We have received your message and will review it "
            "and get back to you if further information is required."
        ),
        "recommended_action": "AUTOMATED_RESPONSE",
        "confidence_score": 0.75,
        "analysis_source": "LOCAL_FALLBACK",
    }


# =========================================================
# AI EMAIL / MESSAGE ANALYSIS
# =========================================================

def analyze_email(
    subject: str,
    message: str,
    sender_email: str = "",
) -> Dict[str, Any]:
    """
    Analyze an incoming email/message using Gemini.

    Returns:
        category
        priority
        intent
        summary
        sentiment
        entities
        suggested_reply
        recommended_action
        confidence_score
        analysis_source

    Gemini failures automatically use local deterministic
    classification.
    """

    if not message or not message.strip():
        raise ValueError(
            "Email/message content cannot be empty."
        )

    subject = subject.strip() if subject else ""
    sender_email = sender_email.strip() if sender_email else ""

    prompt = f"""
You are an AI Email and Message Intelligence system
for a business operations automation platform.

Analyze the incoming business email/message.

Return ONLY valid JSON.

Required JSON structure:

{{
    "category": "Sales, Support, Complaint, Recruitment, Finance, Technical, General, or Urgent",
    "priority": "LOW, MEDIUM, HIGH, or CRITICAL",
    "intent": "short description of the user's intent",
    "summary": "short business summary",
    "sentiment": "Positive, Neutral, or Negative",
    "entities": {{
        "person": null,
        "company": null,
        "product": null,
        "amount": null,
        "date": null
    }},
    "suggested_reply": "professional response to the sender",
    "recommended_action": "recommended operational action",
    "confidence_score": 0.0
}}

Classification rules:

1. category MUST be one of:
   Sales
   Support
   Complaint
   Recruitment
   Finance
   Technical
   General
   Urgent

2. priority MUST be one of:
   LOW
   MEDIUM
   HIGH
   CRITICAL

3. Use CRITICAL for security breaches, fraud,
   unauthorized transactions, account compromise,
   emergencies, or similarly urgent matters.

4. Use HIGH for serious complaints, technical failures,
   significant customer-impacting issues, or matters
   requiring human attention.

5. Use MEDIUM for normal support, finance, sales,
   recruitment, and operational requests.

6. Use LOW for simple general enquiries.

7. Do not invent information.

8. Extract entities only when they are explicitly
   present in the message.

9. suggested_reply must be professional and concise.

10. recommended_action should describe an operational
    action such as:
    AUTOMATED_RESPONSE
    CREATE_SUPPORT_TICKET
    CREATE_TECHNICAL_TICKET
    CREATE_COMPLAINT_TICKET
    SALES_FOLLOW_UP
    FINANCE_FOLLOW_UP
    RECRUITMENT_FOLLOW_UP
    ESCALATE_TO_HUMAN

11. confidence_score must be between 0.0 and 1.0.

Sender:
{sender_email}

Subject:
{subject}

Message:
{message}
"""

    try:
        client = _get_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        result_text = response.text.strip()

        result_text = _clean_json(result_text)

        result = json.loads(result_text)

        # -------------------------------------------------
        # NORMALIZE CATEGORY
        # -------------------------------------------------

        category = str(
            result.get(
                "category",
                "General",
            )
        ).strip()

        if category not in EMAIL_CATEGORIES:
            category = "General"

        # -------------------------------------------------
        # NORMALIZE PRIORITY
        # -------------------------------------------------

        priority = str(
            result.get(
                "priority",
                "LOW",
            )
        ).strip().upper()

        if priority not in PRIORITIES:
            priority = "LOW"

        # -------------------------------------------------
        # NORMALIZE SENTIMENT
        # -------------------------------------------------

        sentiment = str(
            result.get(
                "sentiment",
                "Neutral",
            )
        ).strip()

        if sentiment not in {
            "Positive",
            "Neutral",
            "Negative",
        }:
            sentiment = "Neutral"

        # -------------------------------------------------
        # NORMALIZE ENTITIES
        # -------------------------------------------------

        entities = result.get(
            "entities",
            {},
        )

        if not isinstance(entities, dict):
            entities = {}

        normalized_entities = {
            "person": entities.get("person"),
            "company": entities.get("company"),
            "product": entities.get("product"),
            "amount": entities.get("amount"),
            "date": entities.get("date"),
        }

        # -------------------------------------------------
        # CONFIDENCE
        # -------------------------------------------------

        try:
            confidence_score = float(
                result.get(
                    "confidence_score",
                    0.75,
                )
            )
        except (TypeError, ValueError):
            confidence_score = 0.75

        confidence_score = max(
            0.0,
            min(
                1.0,
                confidence_score,
            ),
        )

        # -------------------------------------------------
        # RESULT
        # -------------------------------------------------

        return {
            "category": category,
            "priority": priority,
            "intent": str(
                result.get(
                    "intent",
                    "General business enquiry",
                )
            ).strip(),
            "summary": str(
                result.get(
                    "summary",
                    "Email analyzed successfully.",
                )
            ).strip(),
            "sentiment": sentiment,
            "entities": normalized_entities,
            "suggested_reply": str(
                result.get(
                    "suggested_reply",
                    "Thank you for contacting us. "
                    "We have received your message "
                    "and will review it shortly.",
                )
            ).strip(),
            "recommended_action": str(
                result.get(
                    "recommended_action",
                    "AUTOMATED_RESPONSE",
                )
            ).strip(),
            "confidence_score": confidence_score,
            "analysis_source": "GEMINI",
        }

    except Exception as exc:

        print(
            f"Email AI analysis unavailable: {exc}"
        )

        return _local_email_analysis(
            subject=subject,
            message=message,
        )


# =========================================================
# FORMAT EMAIL ANALYSIS
# =========================================================

def analyze_message(
    message: str,
    subject: str = "",
    sender_email: str = "",
) -> Dict[str, Any]:
    """
    Convenience wrapper for messages that do not have
    a separate subject.
    """

    return analyze_email(
        subject=subject,
        message=message,
        sender_email=sender_email,
    )