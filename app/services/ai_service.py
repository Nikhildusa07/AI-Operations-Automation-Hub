import json
import os
from typing import Dict, Any, Optional

from ..services.ai_cost_service import (
    record_ai_usage,
    check_cost_limit,
)


# =========================================================
# CONFIGURATION
# =========================================================

DEFAULT_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)

DEFAULT_PROVIDER = "google"

DEFAULT_MAX_COST = float(
    os.getenv(
        "AI_MAX_COST_PER_REQUEST",
        "0.10",
    )
)


# =========================================================
# GEMINI CLIENT
# =========================================================

def _get_gemini_client():
    """
    Create Gemini client only when an AI request is made.
    """

    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(
        api_key=api_key
    )


# =========================================================
# TOKEN USAGE
# =========================================================

def extract_token_usage(response) -> tuple[int, int]:
    """
    Extract Gemini input/output token usage safely.

    Supports:
    - Google GenAI UsageMetadata objects
    - dictionary-style usage metadata
    """

    input_tokens = 0
    output_tokens = 0

    usage_metadata = getattr(
        response,
        "usage_metadata",
        None,
    )

    if not usage_metadata:
        return 0, 0

    # -----------------------------------------------------
    # OBJECT STYLE
    # -----------------------------------------------------

    input_tokens = getattr(
        usage_metadata,
        "prompt_token_count",
        None,
    )

    output_tokens = getattr(
        usage_metadata,
        "candidates_token_count",
        None,
    )

    # -----------------------------------------------------
    # DICT STYLE
    # -----------------------------------------------------

    if isinstance(usage_metadata, dict):

        input_tokens = usage_metadata.get(
            "prompt_token_count",
            usage_metadata.get(
                "input_tokens",
                usage_metadata.get(
                    "promptTokenCount",
                    0,
                ),
            ),
        )

        output_tokens = usage_metadata.get(
            "candidates_token_count",
            usage_metadata.get(
                "output_tokens",
                usage_metadata.get(
                    "candidatesTokenCount",
                    0,
                ),
            ),
        )

    # -----------------------------------------------------
    # SAFE CONVERSION
    # -----------------------------------------------------

    try:
        input_tokens = int(
            input_tokens or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        input_tokens = 0

    try:
        output_tokens = int(
            output_tokens or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        output_tokens = 0

    return (
        input_tokens,
        output_tokens,
    )


# =========================================================
# SAFE JSON EXTRACTION
# =========================================================

def _extract_json(text: str) -> Dict[str, Any]:

    if not text:
        return {}

    text = text.strip()

    # Remove markdown code fences
    if text.startswith("```"):

        text = text.replace(
            "```json",
            "",
        )

        text = text.replace(
            "```",
            "",
        )

        text = text.strip()

    try:

        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # Try extracting JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:

        try:

            result = json.loads(
                text[start:end + 1]
            )

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

    return {}


# =========================================================
# AI BUDGET CHECK
# =========================================================

def check_ai_budget(
    db,
    request_id: Optional[str] = None,
    max_cost: float = DEFAULT_MAX_COST,
):

    return check_cost_limit(
        db=db,
        request_id=request_id,
        max_cost=max_cost,
    )


# =========================================================
# RECORD SUCCESSFUL USAGE
# =========================================================

def record_successful_ai_usage(
    db,
    response,
    request_id: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    purpose: Optional[str] = None,
):

    input_tokens, output_tokens = (
        extract_token_usage(response)
    )

    return record_ai_usage(
        db=db,
        provider=DEFAULT_PROVIDER,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        request_id=request_id,
        purpose=purpose,
        status="SUCCESS",
    )


# =========================================================
# RECORD FAILED USAGE
# =========================================================

def record_failed_ai_usage(
    db,
    request_id: Optional[str],
    model: str,
    error_message: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    purpose: Optional[str] = None,
):

    return record_ai_usage(
        db=db,
        provider=DEFAULT_PROVIDER,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        request_id=request_id,
        purpose=purpose,
        status="FAILED",
        error_message=error_message,
    )


# =========================================================
# ANALYZE REQUEST
# =========================================================

def analyze_request(
    input_text: str,
    request_id: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """
    Main AI analysis function used by requests.py.
    """

    if not input_text or not input_text.strip():

        return {
            "intent": "General Business Request",
            "priority": "MEDIUM",
            "confidence_score": 0.0,
            "summary": "Empty business request.",
            "recommended_action": "REVIEW",
            "requires_human_approval": True,
            "analysis_source": "LOCAL_FALLBACK",
        }

    # -----------------------------------------------------
    # COST CONTROL
    # -----------------------------------------------------

    if db is not None:

        cost_check = check_ai_budget(
            db=db,
            request_id=request_id,
            max_cost=DEFAULT_MAX_COST,
        )

        if not cost_check["allowed"]:

            return {
                "intent": "AI Cost Limit Exceeded",
                "priority": "HIGH",
                "confidence_score": 1.0,
                "summary": (
                    "AI processing was blocked because "
                    "the configured cost limit was reached."
                ),
                "recommended_action": "REVIEW",
                "requires_human_approval": True,
                "analysis_source": "COST_CONTROL",
            }

    # -----------------------------------------------------
    # GEMINI PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are an AI business operations analyst.

Analyze the following business request.

Return ONLY valid JSON.

Required JSON structure:

{{
    "intent": "short business category",
    "priority": "LOW | MEDIUM | HIGH | CRITICAL",
    "confidence_score": 0.0,
    "summary": "short summary",
    "recommended_action": "AUTO_EXECUTE | REVIEW",
    "requires_human_approval": true
}}

Rules:

- Security incidents, fraud, unauthorized access,
  compromised accounts, or serious risks:
  CRITICAL and human approval required.

- Financial, billing, refund, invoice or payment
  requests:
  MEDIUM unless clearly high risk.

- Routine requests:
  LOW or MEDIUM.

- Use confidence_score between 0 and 1.

Business request:

{input_text}
"""

    # -----------------------------------------------------
    # AI EXECUTION
    # -----------------------------------------------------

    try:

        client = _get_gemini_client()

        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
        )

        response_text = getattr(
            response,
            "text",
            "",
        ) or ""

        result = _extract_json(
            response_text
        )

        # -------------------------------------------------
        # VALIDATE RESULT
        # -------------------------------------------------

        if not result:

            raise ValueError(
                "Gemini returned an invalid JSON response."
            )

        priority = str(
            result.get(
                "priority",
                "MEDIUM",
            )
        ).upper()

        if priority not in {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }:

            priority = "MEDIUM"

        try:

            confidence = float(
                result.get(
                    "confidence_score",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            confidence = 0.0

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        recommended_action = str(
            result.get(
                "recommended_action",
                "REVIEW",
            )
        ).upper()

        if recommended_action not in {
            "AUTO_EXECUTE",
            "REVIEW",
        }:

            recommended_action = "REVIEW"

        # -------------------------------------------------
        # COST RECORDING
        # -------------------------------------------------

        if db is not None:

            try:

                record_successful_ai_usage(
                    db=db,
                    response=response,
                    request_id=request_id,
                    model=DEFAULT_MODEL,
                    purpose="BUSINESS_REQUEST_ANALYSIS",
                )

            except Exception as usage_error:

                print(
                    "AI usage logging failed:",
                    repr(usage_error),
                )

        return {

            "intent": str(
                result.get(
                    "intent",
                    "General Business Request",
                )
            ),

            "priority": priority,

            "confidence_score": confidence,

            "summary": str(
                result.get(
                    "summary",
                    input_text,
                )
            ),

            "recommended_action": recommended_action,

            "requires_human_approval": bool(
                result.get(
                    "requires_human_approval",
                    priority in {
                        "HIGH",
                        "CRITICAL",
                    },
                )
            ),

            "analysis_source": "GEMINI",
        }

    # -----------------------------------------------------
    # SAFE FALLBACK
    # -----------------------------------------------------

    except Exception as exc:

        print(
            "AI analysis failed:",
            repr(exc),
        )

        # Record failed AI usage
        if db is not None:

            try:

                record_failed_ai_usage(
                    db=db,
                    request_id=request_id,
                    model=DEFAULT_MODEL,
                    error_message=str(exc),
                    purpose="BUSINESS_REQUEST_ANALYSIS",
                )

            except Exception as usage_error:

                print(
                    "Failed AI usage logging failed:",
                    repr(usage_error),
                )

        # -------------------------------------------------
        # DETERMINISTIC FALLBACK
        # -------------------------------------------------

        text_lower = input_text.lower()

        # Security
        if any(
            word in text_lower
            for word in [
                "unauthorized",
                "fraud",
                "hacked",
                "security breach",
                "compromised",
                "stolen",
            ]
        ):

            return {
                "intent": "Security Incident",
                "priority": "CRITICAL",
                "confidence_score": 0.95,
                "summary": (
                    "Security-related request "
                    "requires human review."
                ),
                "recommended_action": "REVIEW",
                "requires_human_approval": True,
                "analysis_source": "LOCAL_FALLBACK",
            }

        # Financial
        if any(
            word in text_lower
            for word in [
                "refund",
                "payment",
                "billing",
                "invoice",
                "charge",
                "subscription",
            ]
        ):

            return {
                "intent": "Financial Support Request",
                "priority": "MEDIUM",
                "confidence_score": 0.70,
                "summary": (
                    "Financial or billing request "
                    "requires conditional processing."
                ),
                "recommended_action": "REVIEW",
                "requires_human_approval": True,
                "analysis_source": "LOCAL_FALLBACK",
            }

        # Routine
        return {
            "intent": "General Business Request",
            "priority": "LOW",
            "confidence_score": 0.60,
            "summary": input_text[:500],
            "recommended_action": "AUTO_EXECUTE",
            "requires_human_approval": False,
            "analysis_source": "LOCAL_FALLBACK",
        }


# =========================================================
# PROCESS AI REQUEST
# =========================================================

def process_ai_request(
    db,
    ai_client,
    prompt: str,
    request_id: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    purpose: str = "AI_ANALYSIS",
    max_cost: float = DEFAULT_MAX_COST,
):

    cost_check = check_ai_budget(
        db=db,
        request_id=request_id,
        max_cost=max_cost,
    )

    if not cost_check["allowed"]:

        return {
            "success": False,
            "message": "AI cost limit exceeded.",
            "cost_control": cost_check,
        }

    try:

        response = ai_client.models.generate_content(
            model=model,
            contents=prompt,
        )

        usage = record_successful_ai_usage(
            db=db,
            response=response,
            request_id=request_id,
            model=model,
            purpose=purpose,
        )

        return {
            "success": True,
            "response": getattr(
                response,
                "text",
                "",
            ) or "",
            "usage": usage,
        }

    except Exception as exc:

        try:

            usage = record_failed_ai_usage(
                db=db,
                request_id=request_id,
                model=model,
                error_message=str(exc),
                purpose=purpose,
            )

        except Exception:

            usage = None

        return {
            "success": False,
            "message": "AI processing failed.",
            "error": str(exc),
            "usage": usage,
        }