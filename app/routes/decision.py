from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.decision_service import make_decision


router = APIRouter(
    prefix="/api/decision",
    tags=["AI Decision Engine"]
)


# =========================================================
# REQUEST SCHEMA
# =========================================================

class DecisionRequest(BaseModel):
    situation: str
    context: str = ""


# =========================================================
# HEALTH
# =========================================================

@router.get("/health")
def decision_health():

    return {
        "success": True,
        "module": "AI Decision Engine",
        "status": "operational"
    }


# =========================================================
# CREATE DECISION
# =========================================================

@router.post("/analyze")
def analyze_decision(
    request: DecisionRequest
):

    try:

        result = make_decision(
            situation=request.situation,
            context=request.context
        )

        return {
            "success": True,
            "input": {
                "situation": request.situation,
                "context": request.context
            },
            "decision": result
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        print(
            f"Decision engine error: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process business decision."
            )
        )