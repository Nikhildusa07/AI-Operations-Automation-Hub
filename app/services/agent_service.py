import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from google import genai


load_dotenv()


# =========================================================
# CONFIGURATION
# =========================================================

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)


# =========================================================
# AVAILABLE BUSINESS TOOLS
# =========================================================

TOOLS = {
    "business_hours": (
        "Retrieve official business operating hours."
    ),

    "payment_support": (
        "Retrieve payment/refund support information."
    ),

    "profile_support": (
        "Retrieve routine customer profile support information."
    ),

    "general_support": (
        "Retrieve general business support information."
    ),
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

    return genai.Client(
        api_key=api_key
    )


# =========================================================
# CLEAN JSON
# =========================================================

def _clean_json(text: str) -> str:
    """
    Remove Markdown code fences if Gemini
    returns JSON inside ```json ... ```.
    """

    text = (text or "").strip()

    if text.startswith("```"):

        if text.startswith("```json"):
            text = text[7:]

        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

    return text.strip()


# =========================================================
# DETERMINISTIC TOOL SELECTION
# =========================================================

def _fallback_tool_selection(
    input_text: str,
    intent: str,
    fallback_reason: str = "",
) -> Dict[str, Any]:

    text = (
        f"{input_text} {intent}"
        .lower()
    )

    # -----------------------------------------------------
    # BUSINESS HOURS
    # -----------------------------------------------------

    if any(
        word in text
        for word in (
            "business hour",
            "working hour",
            "opening hour",
            "operating hour",
            "when are you open",
            "what time do you open",
            "what time do you close",
            "opening time",
            "closing time",
        )
    ):

        result = {
            "tool": "business_hours",
            "reason": (
                "Request contains business-hours "
                "or operating-time information."
            ),
            "fallback": True,
        }

        if fallback_reason:
            result["fallback_reason"] = (
                fallback_reason
            )

        return result

    # -----------------------------------------------------
    # PAYMENT
    # -----------------------------------------------------

    if any(
        word in text
        for word in (
            "payment",
            "refund",
            "charge",
            "charged",
            "billing",
            "invoice",
            "transaction",
            "money",
            "duplicate charge",
            "charged twice",
            "unauthorized payment",
            "unauthorized transaction",
        )
    ):

        result = {
            "tool": "payment_support",
            "reason": (
                "Request relates to payment, billing, "
                "transaction, or refund support."
            ),
            "fallback": True,
        }

        if fallback_reason:
            result["fallback_reason"] = (
                fallback_reason
            )

        return result

    # -----------------------------------------------------
    # PROFILE / ACCOUNT
    # -----------------------------------------------------

    if any(
        word in text
        for word in (
            "profile",
            "account",
            "address",
            "email",
            "phone number",
            "change my name",
            "update my",
            "change my",
            "subscription",
            "plan",
        )
    ):

        result = {
            "tool": "profile_support",
            "reason": (
                "Request relates to customer profile, "
                "account, or subscription information."
            ),
            "fallback": True,
        }

        if fallback_reason:
            result["fallback_reason"] = (
                fallback_reason
            )

        return result

    # -----------------------------------------------------
    # GENERAL SUPPORT
    # -----------------------------------------------------

    result = {
        "tool": "general_support",
        "reason": (
            "Request does not match a specialized "
            "business tool, so general support was selected."
        ),
        "fallback": True,
    }

    if fallback_reason:
        result["fallback_reason"] = (
            fallback_reason
        )

    return result


# =========================================================
# AI TOOL SELECTION
# =========================================================

def select_tool(
    input_text: str,
    intent: str,
) -> Dict[str, Any]:

    if not input_text or not input_text.strip():

        return _fallback_tool_selection(
            input_text or "",
            intent or "",
            "Request text was empty.",
        )

    prompt = f"""
You are the tool-selection agent in a business
operations automation system.

Your task is to select exactly ONE tool for
the customer request.

Available tools:

{json.dumps(TOOLS, indent=2)}

Customer request:

{input_text}

Detected intent:

{intent}

Rules:

1. Select exactly one tool.
2. Do not invent a tool.
3. Return ONLY valid JSON.
4. Do not include Markdown.
5. Do not include explanations outside the JSON.

Return exactly:

{{
    "tool": "business_hours|payment_support|profile_support|general_support",
    "reason": "short reason for selecting the tool"
}}
"""

    client = None

    try:

        client = _get_client()

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        text = _clean_json(
            getattr(
                response,
                "text",
                "",
            )
        )

        if not text:

            raise ValueError(
                "Gemini returned an empty "
                "tool-selection response."
            )

        result = json.loads(text)

        if not isinstance(
            result,
            dict,
        ):

            raise ValueError(
                "Gemini returned an invalid "
                "tool-selection object."
            )

        tool = result.get("tool")

        if tool not in TOOLS:

            raise ValueError(
                f"Unsupported tool returned by "
                f"Gemini: {tool}"
            )

        reason = str(
            result.get(
                "reason",
                "Tool selected by AI agent.",
            )
        ).strip()

        return {
            "tool": tool,
            "reason": reason,
            "fallback": False,
            "model": GEMINI_MODEL,
        }

    except Exception as exc:

        error_text = str(exc)

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
            or "quota" in error_text.lower()
            or "rate limit" in error_text.lower()
        ):

            print(
                "Gemini agent quota unavailable. "
                "Using deterministic tool selection."
            )

        else:

            print(
                "AI tool selection unavailable: "
                f"{error_text}"
            )

        return _fallback_tool_selection(
            input_text=input_text,
            intent=intent,
            fallback_reason=error_text,
        )

    finally:

        if client is not None:

            try:
                client.close()

            except Exception:
                pass


# =========================================================
# BUSINESS DATA RETRIEVAL
# =========================================================

def retrieve_data(
    tool: str,
    request_text: str,
) -> Dict[str, Any]:

    data = {

        "business_hours": {
            "source": (
                "Business Operations Knowledge Base"
            ),
            "data": (
                "Monday-Friday 9:00 AM-6:00 PM; "
                "Saturday 10:00 AM-2:00 PM; "
                "Sunday closed."
            ),
        },

        "payment_support": {
            "source": (
                "Payment Support Policy"
            ),
            "data": (
                "Payment/refund issues require "
                "verification of the transaction "
                "and may require human review."
            ),
        },

        "profile_support": {
            "source": (
                "Customer Profile Service"
            ),
            "data": (
                "Routine profile updates can be "
                "handled automatically after "
                "customer verification."
            ),
        },

        "general_support": {
            "source": (
                "Business Support Knowledge Base"
            ),
            "data": (
                "General requests are routed "
                "according to priority and "
                "AI confidence."
            ),
        },
    }

    if tool not in data:

        raise ValueError(
            f"Unsupported tool: {tool}"
        )

    return data[tool]


# =========================================================
# WORKFLOW REASONING
# =========================================================

def reason_about_result(
    input_text: str,
    analysis: Dict[str, Any],
    retrieved: Dict[str, Any],
) -> Dict[str, Any]:

    priority = str(
        analysis.get(
            "priority",
            "LOW",
        )
    ).upper().strip()

    try:

        confidence = float(
            analysis.get(
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
        min(1.0, confidence),
    )

    if confidence < 0.70:

        next_step = (
            "Human review because AI confidence "
            "is below the threshold."
        )

    elif priority == "HIGH":

        next_step = (
            "Human review because the "
            "request is high priority."
        )

    elif priority == "CRITICAL":

        next_step = (
            "Human review because the "
            "request is critical priority."
        )

    elif priority == "MEDIUM":

        next_step = (
            "Customer follow-up is required."
        )

    else:

        next_step = (
            "Automated response is appropriate "
            "for this routine request."
        )

    return {

        "reasoning": (
            f"Retrieved data from "
            f"{retrieved['source']}. "
            f"The request was classified as "
            f"{priority} with confidence "
            f"{confidence:.2f}. "
            f"{next_step}"
        ),

        "next_step": next_step,
    }


# =========================================================
# COMPLETE AGENT WORKFLOW
# =========================================================

def run_agent_workflow(
    input_text: str,
    analysis: Dict[str, Any],
) -> Dict[str, Any]:

    if not input_text or not input_text.strip():

        raise ValueError(
            "input_text is required "
            "for agent workflow."
        )

    if not isinstance(
        analysis,
        dict,
    ):

        analysis = {}

    # -----------------------------------------------------
    # 1. TOOL SELECTION
    # -----------------------------------------------------

    selected = select_tool(
        input_text=input_text,
        intent=analysis.get(
            "intent",
            "General Business Request",
        ),
    )

    # -----------------------------------------------------
    # 2. DATA RETRIEVAL
    # -----------------------------------------------------

    retrieved = retrieve_data(
        tool=selected["tool"],
        request_text=input_text,
    )

    # -----------------------------------------------------
    # 3. REASONING
    # -----------------------------------------------------

    reasoning = reason_about_result(
        input_text=input_text,
        analysis=analysis,
        retrieved=retrieved,
    )

    # -----------------------------------------------------
    # 4. VERIFICATION
    # -----------------------------------------------------

    if selected.get("fallback"):

        verification = {
            "status": "SUCCESS",
            "message": (
                "Tool selection fallback completed "
                "successfully; data retrieval and "
                "reasoning completed."
            ),
        }

    else:

        verification = {
            "status": "READY",
            "message": (
                "Tool selection, data retrieval, "
                "and reasoning completed before "
                "action execution."
            ),
        }

    # -----------------------------------------------------
    # 5. COMPLETE RESULT
    # -----------------------------------------------------

    return {

        "status": "SUCCESS",

        # IMPORTANT:
        # requests.py expects this field directly.
        "tool": selected["tool"],

        "selected_tool": selected["tool"],

        "tool_selection": selected,

        "data_retrieval": retrieved,

        "reasoning": reasoning,

        "verification": verification,

    }