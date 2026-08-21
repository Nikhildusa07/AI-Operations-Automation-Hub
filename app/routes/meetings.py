from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.meeting_service import analyze_meeting


router = APIRouter(
    prefix="/api/meetings",
    tags=["Meeting Intelligence"]
)


# =========================================================
# REQUEST SCHEMA
# =========================================================

class MeetingAnalysisRequest(BaseModel):

    meeting_title: str = Field(
        ...,
        min_length=1,
        max_length=200
    )

    transcript: str = Field(
        ...,
        min_length=10
    )

    participants: Optional[List[str]] = None


# =========================================================
# HEALTH CHECK
# =========================================================

@router.get("/health")
def meeting_health():

    return {
        "success": True,
        "module": "Meeting Intelligence",
        "status": "operational"
    }


# =========================================================
# ANALYZE MEETING
# =========================================================

@router.post("/analyze")
def analyze_meeting_endpoint(
    request: MeetingAnalysisRequest
):

    try:

        result = analyze_meeting(
            meeting_title=request.meeting_title,
            transcript=request.transcript,
            participants=request.participants
        )

        return {
            "success": True,
            "input": {
                "meeting_title":
                    request.meeting_title,
                "participants":
                    request.participants or [],
                "transcript_length":
                    len(request.transcript)
            },
            "analysis": result
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        print(
            f"Meeting analysis error: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to analyze meeting."
            )
        )