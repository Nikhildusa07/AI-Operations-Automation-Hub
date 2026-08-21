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

    return genai.Client(
        api_key=api_key
    )


# =========================================================
# CLEAN GEMINI JSON
# =========================================================

def _clean_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


# =========================================================
# MEETING INTELLIGENCE
# =========================================================

def analyze_meeting(
    meeting_title: str,
    transcript: str,
    participants: list[str] | None = None
) -> Dict[str, Any]:

    if not transcript or not transcript.strip():
        raise ValueError(
            "Meeting transcript cannot be empty."
        )

    participants = participants or []

    participant_text = ", ".join(
        participants
    )

    prompt = f"""
You are an AI Meeting Intelligence Assistant.

Analyze the following business meeting transcript.

Return ONLY valid JSON.

Required JSON structure:

{{
    "meeting_title": "string",
    "summary": "concise meeting summary",
    "participants": [],
    "key_discussion_points": [],
    "decisions": [],
    "action_items": [
        {{
            "task": "string",
            "assignee": "string or null",
            "deadline": "string or null",
            "priority": "LOW, MEDIUM, HIGH, or CRITICAL"
        }}
    ],
    "risks_or_blockers": [],
    "follow_up_required": true,
    "next_meeting": "string or null",
    "confidence_score": 0.0
}}

Rules:

1. Do not invent information.
2. Extract participants only when available.
3. Extract actual decisions from the transcript.
4. Extract actionable tasks.
5. If an assignee is not mentioned, use null.
6. If a deadline is not mentioned, use null.
7. Identify risks or blockers only when supported by the transcript.
8. Set follow_up_required to true when follow-up work is required.
9. confidence_score must be between 0.0 and 1.0.
10. Return ONLY JSON.

Meeting title:
{meeting_title}

Known participants:
{participant_text}

Meeting transcript:
{transcript}
"""

    try:

        client = _get_client()

        # =================================================
        # GEMINI REQUEST
        # =================================================

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        result_text = response.text or ""

        if not result_text.strip():
            raise ValueError(
                "Gemini returned an empty response."
            )

        result_text = _clean_json(
            result_text
        )

        result = json.loads(
            result_text
        )

        # =================================================
        # NORMALIZE RESULT
        # =================================================

        meeting_title_result = str(
            result.get(
                "meeting_title",
                meeting_title
            )
        ).strip()

        summary = str(
            result.get(
                "summary",
                "Meeting analyzed successfully."
            )
        ).strip()

        extracted_participants = result.get(
            "participants",
            participants
        )

        if not isinstance(
            extracted_participants,
            list
        ):
            extracted_participants = participants

        key_discussion_points = result.get(
            "key_discussion_points",
            []
        )

        if not isinstance(
            key_discussion_points,
            list
        ):
            key_discussion_points = [
                str(key_discussion_points)
            ]

        decisions = result.get(
            "decisions",
            []
        )

        if not isinstance(
            decisions,
            list
        ):
            decisions = [
                str(decisions)
            ]

        action_items = result.get(
            "action_items",
            []
        )

        if not isinstance(
            action_items,
            list
        ):
            action_items = []

        risks_or_blockers = result.get(
            "risks_or_blockers",
            []
        )

        if not isinstance(
            risks_or_blockers,
            list
        ):
            risks_or_blockers = [
                str(risks_or_blockers)
            ]

        follow_up_required = result.get(
            "follow_up_required",
            False
        )

        next_meeting = result.get(
            "next_meeting",
            None
        )

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
            "meeting_title":
                meeting_title_result,

            "summary":
                summary,

            "participants":
                extracted_participants,

            "key_discussion_points":
                key_discussion_points,

            "decisions":
                decisions,

            "action_items":
                action_items,

            "risks_or_blockers":
                risks_or_blockers,

            "follow_up_required":
                bool(follow_up_required),

            "next_meeting":
                next_meeting,

            "confidence_score":
                confidence_score,

            "analysis_source":
                "GEMINI"
        }

    except Exception as exc:

        print(
            f"Meeting AI analysis unavailable: "
            f"{repr(exc)}"
        )

        # =================================================
        # SAFE FALLBACK
        # =================================================

        return {
            "meeting_title":
                meeting_title,

            "summary":
                "The meeting transcript was received, "
                "but AI analysis was unavailable.",

            "participants":
                participants,

            "key_discussion_points":
                [],

            "decisions":
                [],

            "action_items":
                [],

            "risks_or_blockers":
                [],

            "follow_up_required":
                False,

            "next_meeting":
                None,

            "confidence_score":
                0.0,

            "analysis_source":
                "LOCAL_FALLBACK",

            "fallback_reason":
                "Gemini API unavailable."
        }