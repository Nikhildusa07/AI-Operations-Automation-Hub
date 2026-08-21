from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db

from ..services.ai_cost_service import (
    get_total_ai_cost,
    check_cost_limit,
    record_ai_usage,
)


router = APIRouter(
    prefix="/api/ai-cost",
    tags=["AI Cost Control"],
)


# =========================================================
# REQUEST SCHEMA
# =========================================================

class AIUsageTestRequest(BaseModel):
    request_id: str = Field(
        default="REQ-COST-001",
        min_length=1,
    )

    input_tokens: int = Field(
        default=1000,
        ge=0,
    )

    output_tokens: int = Field(
        default=500,
        ge=0,
    )

    model: str = Field(
        default="gemini-2.0-flash",
        min_length=1,
    )


# =========================================================
# HEALTH
# =========================================================

@router.get("/health")
def ai_cost_health():

    return {
        "success": True,
        "module": "AI Cost Control",
        "status": "operational",
    }


# =========================================================
# TOTAL AI USAGE
# =========================================================

@router.get("/usage")
def ai_usage(
    request_id: Optional[str] = None,
    db: Session = Depends(get_db),
):

    return get_total_ai_cost(
        db=db,
        request_id=request_id,
    )


# =========================================================
# COST LIMIT CHECK
# =========================================================

@router.get("/limit")
def ai_cost_limit(
    request_id: Optional[str] = None,
    max_cost: float = 0.10,
    db: Session = Depends(get_db),
):

    return check_cost_limit(
        db=db,
        request_id=request_id,
        max_cost=max_cost,
    )


# =========================================================
# TEST / RECORD AI USAGE
# =========================================================

@router.post("/record-test")
def record_test_usage(
    data: AIUsageTestRequest,
    db: Session = Depends(get_db),
):

    return record_ai_usage(
        db=db,
        provider="google",
        model=data.model,
        input_tokens=data.input_tokens,
        output_tokens=data.output_tokens,
        request_id=data.request_id,
        purpose="COST_CONTROL_TEST",
        status="SUCCESS",
    )