import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google import genai


load_dotenv()


# =========================================================
# CONSTANTS
# =========================================================

TASK_PRIORITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}

TASK_STATUSES = {
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "BLOCKED",
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
# LOCAL FALLBACK
# =========================================================

def _local_task_analysis(
    task: str,
    context: str = "",
    assignee: Optional[str] = None,
) -> Dict[str, Any]:

    text = f"{task} {context}".lower()

    # -----------------------------------------------------
    # PRIORITY
    # -----------------------------------------------------

    critical_keywords = [
        "security breach",
        "hacked",
        "fraud",
        "unauthorized",
        "emergency",
        "critical",
        "immediately",
    ]

    high_keywords = [
        "urgent",
        "as soon as possible",
        "customer complaint",
        "payment failed",
        "production issue",
        "system down",
        "deadline today",
    ]

    medium_keywords = [
        "invoice",
        "payment",
        "customer",
        "review",
        "follow up",
        "meeting",
        "report",
    ]

    if any(keyword in text for keyword in critical_keywords):
        priority = "CRITICAL"
    elif any(keyword in text for keyword in high_keywords):
        priority = "HIGH"
    elif any(keyword in text for keyword in medium_keywords):
        priority = "MEDIUM"
    else:
        priority = "LOW"

    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if any(word in text for word in [
        "invoice",
        "payment",
        "billing",
        "finance",
    ]):
        category = "Finance"

    elif any(word in text for word in [
        "customer",
        "support",
        "complaint",
    ]):
        category = "Customer Support"

    elif any(word in text for word in [
        "technical",
        "bug",
        "api",
        "server",
        "error",
    ]):
        category = "Technical"

    elif any(word in text for word in [
        "meeting",
        "schedule",
        "call",
    ]):
        category = "Meeting"

    elif any(word in text for word in [
        "sales",
        "lead",
        "proposal",
        "client",
    ]):
        category = "Sales"

    else:
        category = "General"

    # -----------------------------------------------------
    # ACTION
    # -----------------------------------------------------

    if priority in {"HIGH", "CRITICAL"}:
        next_action = (
            "Review the task immediately and assign "
            "it to the appropriate team member."
        )
    else:
        next_action = (
            "Assign the task and complete it according "
            "to the requested timeline."
        )

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    title = task.strip()

    if len(title) > 100:
        title = title[:97] + "..."

    return {
        "title": title,
        "description": task.strip(),
        "category": category,
        "priority": priority,
        "status": "PENDING",
        "assignee": assignee,
        "due_date": None,
        "next_action": next_action,
        "dependencies": [],
        "estimated_effort": "Not specified",
        "confidence_score": 0.75,
        "analysis_source": "LOCAL_FALLBACK",
    }


# =========================================================
# AI TASK ANALYSIS
# =========================================================

def analyze_task(
    task: str,
    context: str = "",
    assignee: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert a natural-language business request
    into a structured AI task.
    """

    if not task or not task.strip():
        raise ValueError(
            "Task description cannot be empty."
        )

    task = task.strip()
    context = context.strip() if context else ""

    prompt = f"""
You are an AI Task Management assistant
for a business operations automation platform.

Convert the following business request into
a structured actionable task.

Return ONLY valid JSON.

Required JSON structure:

{{
    "title": "short task title",
    "description": "clear task description",
    "category": "Finance, Customer Support, Technical, Meeting, Sales, Operations, or General",
    "priority": "LOW, MEDIUM, HIGH, or CRITICAL",
    "status": "PENDING",
    "assignee": null,
    "due_date": null,
    "next_action": "specific next action",
    "dependencies": [],
    "estimated_effort": "short estimate",
    "confidence_score": 0.0
}}

Rules:

1. Convert the request into one clear actionable task.
2. Create a concise professional title.
3. Preserve the actual meaning of the request.
4. Do not invent a due date.
5. If no due date is provided, return null.
6. If an assignee is provided, preserve it.
7. Priority must be LOW, MEDIUM, HIGH, or CRITICAL.
8. Use CRITICAL for emergencies, security issues,
   fraud, unauthorized transactions, or severe incidents.
9. Use HIGH for urgent customer-impacting or
   business-critical tasks.
10. Use MEDIUM for normal operational tasks.
11. Use LOW for routine tasks.
12. Identify dependencies only when explicitly
   mentioned or clearly required.
13. Do not invent dependencies.
14. status must initially be PENDING.
15. confidence_score must be between 0.0 and 1.0.

Business task:
{task}

Additional context:
{context}

Assignee:
{assignee or "Not specified"}
"""

    try:

        client = _get_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        result_text = response.text.strip()

        result_text = _clean_json(
            result_text
        )

        result = json.loads(
            result_text
        )

        # -------------------------------------------------
        # NORMALIZE PRIORITY
        # -------------------------------------------------

        priority = str(
            result.get(
                "priority",
                "MEDIUM",
            )
        ).strip().upper()

        if priority not in TASK_PRIORITIES:
            priority = "MEDIUM"

        # -------------------------------------------------
        # NORMALIZE STATUS
        # -------------------------------------------------

        status = str(
            result.get(
                "status",
                "PENDING",
            )
        ).strip().upper()

        if status not in TASK_STATUSES:
            status = "PENDING"

        # -------------------------------------------------
        # ASSIGNEE
        # -------------------------------------------------

        result_assignee = result.get(
            "assignee"
        )

        if not result_assignee:
            result_assignee = assignee

        # -------------------------------------------------
        # DEPENDENCIES
        # -------------------------------------------------

        dependencies = result.get(
            "dependencies",
            [],
        )

        if not isinstance(
            dependencies,
            list,
        ):
            dependencies = [
                str(dependencies)
            ]

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
        # RETURN
        # -------------------------------------------------

        return {
            "title": str(
                result.get(
                    "title",
                    task[:100],
                )
            ).strip(),

            "description": str(
                result.get(
                    "description",
                    task,
                )
            ).strip(),

            "category": str(
                result.get(
                    "category",
                    "General",
                )
            ).strip(),

            "priority": priority,

            "status": status,

            "assignee": result_assignee,

            "due_date": result.get(
                "due_date"
            ),

            "next_action": str(
                result.get(
                    "next_action",
                    "Review and complete the task.",
                )
            ).strip(),

            "dependencies": dependencies,

            "estimated_effort": str(
                result.get(
                    "estimated_effort",
                    "Not specified",
                )
            ).strip(),

            "confidence_score": confidence_score,

            "analysis_source": "GEMINI",
        }

    except Exception as exc:

        print(
            f"Task AI analysis unavailable: {exc}"
        )

        return _local_task_analysis(
            task=task,
            context=context,
            assignee=assignee,
        )