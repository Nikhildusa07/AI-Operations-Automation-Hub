import json
import os
from typing import Dict, Any

from dotenv import load_dotenv
from google import genai


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv(override=True)


# =========================================================
# CONSTANTS
# =========================================================

VALID_RISK_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}

DEFAULT_DECISION = "Human review required."
DEFAULT_REASON = "AI decision analysis is currently unavailable."
DEFAULT_ACTION = "HUMAN_REVIEW"

LOW_CONFIDENCE_THRESHOLD = 0.70


# =========================================================
# GEMINI CLIENT
# =========================================================

def _get_client():
    """
    Use GEMINI_API_KEY explicitly.

    GOOGLE_API_KEY is intentionally not used here because
    the project is configured with GEMINI_API_KEY.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    api_key = api_key.strip()

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is empty."
        )

    return genai.Client(
        api_key=api_key
    )


# =========================================================
# CLEAN JSON
# =========================================================

def _clean_json(text: str) -> str:

    if not text:
        return ""

    text = text.strip()

    if text.startswith("```json"):
        text = text[len("```json"):].strip()

    elif text.startswith("```"):
        text = text[len("```"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


# =========================================================
# SAFE BOOLEAN
# =========================================================

def _safe_bool(
    value: Any,
    default: bool = True,
) -> bool:

    if isinstance(value, bool):
        return value

    if isinstance(value, str):

        value = value.strip().lower()

        if value in {
            "true",
            "yes",
            "1",
            "required",
            "human_review",
            "escalate",
        }:
            return True

        if value in {
            "false",
            "no",
            "0",
            "automate",
            "auto_execute",
        }:
            return False

    return default


# =========================================================
# SAFE CONFIDENCE
# =========================================================

def _safe_confidence(
    value: Any,
    default: float = 0.75,
) -> float:

    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default

    return max(
        0.0,
        min(1.0, score),
    )


# =========================================================
# NORMALIZE DECISION
# =========================================================

def _normalize_decision(
    result: Dict[str, Any],
) -> Dict[str, Any]:

    decision = str(
        result.get(
            "decision",
            DEFAULT_DECISION,
        )
    ).strip()

    reasoning = str(
        result.get(
            "reasoning",
            result.get(
                "reason",
                DEFAULT_REASON,
            ),
        )
    ).strip()

    reason = str(
        result.get(
            "reason",
            reasoning,
        )
    ).strip()

    risk_level = str(
        result.get(
            "risk_level",
            "MEDIUM",
        )
    ).upper().strip()

    if risk_level not in VALID_RISK_LEVELS:
        risk_level = "MEDIUM"

    recommended_action = str(
        result.get(
            "recommended_action",
            result.get(
                "action",
                DEFAULT_ACTION,
            ),
        )
    ).strip()

    if not recommended_action:
        recommended_action = DEFAULT_ACTION

    requires_human_approval = _safe_bool(
        result.get(
            "requires_human_approval",
            True,
        ),
        default=True,
    )

    confidence_score = _safe_confidence(
        result.get(
            "confidence_score",
            0.75,
        )
    )

    # -----------------------------------------------------
    # SAFETY OVERRIDES
    # -----------------------------------------------------

    if risk_level in {
        "HIGH",
        "CRITICAL",
    }:
        requires_human_approval = True

    if confidence_score < LOW_CONFIDENCE_THRESHOLD:
        requires_human_approval = True

    # -----------------------------------------------------
    # NORMALIZED ACTION
    # -----------------------------------------------------

    if requires_human_approval:

        action = "HUMAN_REVIEW"
        decision_status = "ESCALATE"

    else:

        action = "AUTO_EXECUTE"
        decision_status = "AUTOMATE"

    return {
        "decision": decision,
        "reason": reason,
        "reasoning": reasoning,
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "requires_human_approval": requires_human_approval,
        "confidence_score": confidence_score,
        "action": action,
        "decision_status": decision_status,
        "analysis_source": "GEMINI",
    }


# =========================================================
# DETERMINISTIC KEYWORD HELPER
# =========================================================

def _contains_any(
    text: str,
    keywords: list[str],
) -> bool:

    return any(
        keyword in text
        for keyword in keywords
    )


# =========================================================
# LOCAL FALLBACK
# =========================================================

def _local_fallback(
    situation: str,
    fallback_reason: str = "Gemini API unavailable.",
) -> Dict[str, Any]:

    text = (
        situation or ""
    ).lower().strip()

    # =====================================================
    # 1. CRITICAL SECURITY
    # =====================================================

    security_keywords = [
        "account compromise",
        "unauthorized payment",
        "security breach",
        "hacked",
        "compromised account",
        "data breach",
        "security incident",
        "unauthorized access",
        "someone accessed my account",
        "account was hacked",
        "security problem",
        "security issue",
    ]

    if _contains_any(
        text,
        security_keywords,
    ):

        return {
            "decision": "Escalate security incident.",
            "reason": (
                "Security-related activity requires "
                "immediate human review."
            ),
            "reasoning": (
                "The request contains indicators "
                "of a security incident."
            ),
            "risk_level": "CRITICAL",
            "recommended_action": "SECURITY_HUMAN_REVIEW",
            "requires_human_approval": True,
            "confidence_score": 0.95,
            "action": "HUMAN_REVIEW",
            "decision_status": "ESCALATE",
            "analysis_source": "LOCAL_FALLBACK",
            "fallback_reason": fallback_reason,
        }

    # =====================================================
    # 2. FINANCIAL / PAYMENT
    # =====================================================

    financial_keywords = [
        "duplicate charge",
        "refund",
        "payment failure",
        "payment failed",
        "financial dispute",
        "charged twice",
        "invoice dispute",
        "unauthorized charge",
        "billing dispute",
        "wrong charge",
        "wrong amount",
        "payment issue",
        "payment problem",
        "money deducted",
    ]

    if _contains_any(
        text,
        financial_keywords,
    ):

        return {
            "decision": "Financial review required.",
            "reason": (
                "The request involves a financial issue "
                "and requires human review."
            ),
            "reasoning": (
                "Financial disputes and payment-related "
                "issues require controlled review."
            ),
            "risk_level": "HIGH",
            "recommended_action": "FINANCE_HUMAN_REVIEW",
            "requires_human_approval": True,
            "confidence_score": 0.90,
            "action": "HUMAN_REVIEW",
            "decision_status": "ESCALATE",
            "analysis_source": "LOCAL_FALLBACK",
            "fallback_reason": fallback_reason,
        }

    # =====================================================
    # 3. BUSINESS HOURS
    # =====================================================

    business_hours_keywords = [
        "business hours",
        "business hour",
        "working hours",
        "working hour",
        "opening hours",
        "opening hour",
        "operating hours",
        "operating hour",
        "opening time",
        "closing time",
        "what time do you open",
        "what time do you close",
        "when are you open",
        "when do you open",
        "when do you close",
        "are you open",
        "what are your hours",
        "what is your business hours",
    ]

    if _contains_any(
        text,
        business_hours_keywords,
    ):

        return {
            "decision": "Automate informational response.",
            "reason": (
                "The request is a low-risk informational "
                "request that can be handled automatically."
            ),
            "reasoning": (
                "Business-hours information is routine "
                "and does not require human approval."
            ),
            "risk_level": "LOW",
            "recommended_action": "AUTOMATED_RESPONSE",
            "requires_human_approval": False,
            "confidence_score": 0.95,
            "action": "AUTO_EXECUTE",
            "decision_status": "AUTOMATE",
            "analysis_source": "LOCAL_FALLBACK",
            "fallback_reason": fallback_reason,
        }

    # =====================================================
    # 4. OTHER LOW-RISK INFORMATIONAL REQUESTS
    # =====================================================

    informational_keywords = [
        "what is",
        "what are",
        "how does",
        "how do i",
        "information about",
        "tell me about",
        "where can i find",
        "when is",
        "when will",
        "contact information",
    ]

    if _contains_any(
        text,
        informational_keywords,
    ):

        return {
            "decision": "Automate informational response.",
            "reason": (
                "The request appears to be a routine "
                "low-risk informational request."
            ),
            "reasoning": (
                "No high-risk financial or security "
                "indicators were detected."
            ),
            "risk_level": "LOW",
            "recommended_action": "AUTOMATED_RESPONSE",
            "requires_human_approval": False,
            "confidence_score": 0.85,
            "action": "AUTO_EXECUTE",
            "decision_status": "AUTOMATE",
            "analysis_source": "LOCAL_FALLBACK",
            "fallback_reason": fallback_reason,
        }

    # =====================================================
    # 5. SAFE GENERAL FALLBACK
    # =====================================================

    return {
        "decision": DEFAULT_DECISION,
        "reason": (
            "AI analysis is unavailable, so the request "
            "is safely routed to human review."
        ),
        "reasoning": (
            "The system could not obtain an AI decision "
            "and therefore uses a safe fallback."
        ),
        "risk_level": "HIGH",
        "recommended_action": "Review the situation manually.",
        "requires_human_approval": True,
        "confidence_score": 0.0,
        "action": "HUMAN_REVIEW",
        "decision_status": "ESCALATE",
        "analysis_source": "LOCAL_FALLBACK",
        "fallback_reason": fallback_reason,
    }


# =========================================================
# AI DECISION ENGINE
# =========================================================

def make_decision(
    situation: str,
    context: str = "",
) -> Dict[str, Any]:

    if not situation or not situation.strip():

        raise ValueError(
            "Situation is required."
        )

    prompt = f"""
You are an AI Business Decision Engine.

Analyze the business situation and recommend
the most appropriate operational decision.

Return ONLY valid JSON.

Required structure:

{{
    "decision": "Recommended decision",
    "reasoning": "Why this decision is appropriate",
    "risk_level": "LOW, MEDIUM, HIGH, or CRITICAL",
    "recommended_action": "Specific action to take",
    "requires_human_approval": true,
    "confidence_score": 0.0
}}

Rules:

1. Base the decision only on the provided information.
2. Do not invent facts.
3. Identify operational risks.
4. Security incidents must be CRITICAL.
5. Critical financial, security, legal, or serious
   customer-impacting situations require human approval.
6. confidence_score must be between 0.0 and 1.0.
7. risk_level must be exactly LOW, MEDIUM, HIGH, or CRITICAL.
8. requires_human_approval must be true or false.
9. Duplicate charges, refunds, payment failures,
   financial disputes, or customer financial issues
   requiring review should normally be HIGH.
10. Account compromise, unauthorized payment,
    security breach, hacked account, or unauthorized
    access should be CRITICAL.
11. Simple informational requests such as business
    hours should be LOW.
12. LOW-risk informational requests should normally
    be automated.
13. HIGH and CRITICAL risk requests must require
    human approval.
14. Provide clear reasoning.

Business situation:

{situation}

Additional context:

{context}
"""

    client = None

    try:

        # -------------------------------------------------
        # CREATE GEMINI CLIENT
        # -------------------------------------------------

        client = _get_client()

        # -------------------------------------------------
        # MODEL
        # -------------------------------------------------

        model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        ).strip()

        # -------------------------------------------------
        # GEMINI REQUEST
        # -------------------------------------------------

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        result_text = getattr(
            response,
            "text",
            "",
        )

        if not result_text:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        # -------------------------------------------------
        # CLEAN RESPONSE
        # -------------------------------------------------

        result_text = _clean_json(
            result_text
        )

        # -------------------------------------------------
        # PARSE JSON
        # -------------------------------------------------

        result = json.loads(
            result_text
        )

        if not isinstance(
            result,
            dict,
        ):

            raise ValueError(
                "Gemini response is not a JSON object."
            )

        # -------------------------------------------------
        # NORMALIZE
        # -------------------------------------------------

        return _normalize_decision(
            result
        )

    except Exception as exc:

        error_text = str(exc)

        print(
            "Decision AI analysis unavailable: "
            f"{repr(exc)}"
        )

        return _local_fallback(
            situation=situation,
            fallback_reason=error_text,
        )

    finally:

        if client is not None:

            try:
                client.close()
            except Exception:
                pass