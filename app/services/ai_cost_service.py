from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from ..models import AIUsageLog


# =========================================================
# MODEL PRICING
# =========================================================

MODEL_PRICING = {
    "gemini-3.6-flash": {
        "input_per_1m": 1.50,
        "output_per_1m": 7.50,
    },

    "gemini-3.5-flash": {
        "input_per_1m": 1.50,
        "output_per_1m": 7.50,
    },

    "gemini-3.5-flash-lite": {
        "input_per_1m": 0.30,
        "output_per_1m": 2.50,
    },

    "default": {
        "input_per_1m": 1.50,
        "output_per_1m": 7.50,
    },
}

# =========================================================
# COST CALCULATION
# =========================================================

def calculate_ai_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate estimated AI cost based on token usage.
    """

    pricing = MODEL_PRICING.get(
        model,
        MODEL_PRICING["default"]
    )

    input_cost = (
        input_tokens / 1_000_000
    ) * pricing["input_per_1m"]

    output_cost = (
        output_tokens / 1_000_000
    ) * pricing["output_per_1m"]

    return round(
        input_cost + output_cost,
        8
    )


# =========================================================
# RECORD AI USAGE
# =========================================================

def record_ai_usage(
    db: Session,
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    request_id: Optional[str] = None,
    purpose: Optional[str] = None,
    status: str = "SUCCESS",
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Store AI usage and estimated cost.
    """

    input_tokens = max(
        int(input_tokens or 0),
        0
    )

    output_tokens = max(
        int(output_tokens or 0),
        0
    )

    total_tokens = (
        input_tokens +
        output_tokens
    )

    estimated_cost = calculate_ai_cost(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    usage = AIUsageLog(
        request_id=request_id,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        purpose=purpose,
        status=status,
        error_message=error_message,
    )

    db.add(usage)
    db.commit()
    db.refresh(usage)

    return {
        "success": True,
        "usage": {
            "id": usage.id,
            "request_id": usage.request_id,
            "provider": usage.provider,
            "model": usage.model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
            "estimated_cost": usage.estimated_cost,
            "purpose": usage.purpose,
            "status": usage.status,
            "created_at": (
                usage.created_at.isoformat()
                if usage.created_at
                else None
            ),
        },
    }


# =========================================================
# GET TOTAL AI COST
# =========================================================

def get_total_ai_cost(
    db: Session,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return total AI usage and estimated cost.
    """

    query = db.query(AIUsageLog)

    if request_id:
        query = query.filter(
            AIUsageLog.request_id == request_id
        )

    records = query.all()

    total_input_tokens = sum(
        record.input_tokens or 0
        for record in records
    )

    total_output_tokens = sum(
        record.output_tokens or 0
        for record in records
    )

    total_tokens = sum(
        record.total_tokens or 0
        for record in records
    )

    total_cost = sum(
        record.estimated_cost or 0
        for record in records
    )

    return {
        "success": True,
        "usage": {
            "total_calls": len(records),
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": round(
                total_cost,
                8
            ),
        },
    }


# =========================================================
# COST CONTROL CHECK
# =========================================================

def check_cost_limit(
    db: Session,
    request_id: Optional[str] = None,
    max_cost: float = 0.10,
) -> Dict[str, Any]:
    """
    Check whether AI usage is within the configured limit.
    """

    result = get_total_ai_cost(
        db=db,
        request_id=request_id,
    )

    current_cost = result["usage"]["estimated_cost"]

    allowed = current_cost < max_cost

    return {
        "success": True,
        "allowed": allowed,
        "current_cost": current_cost,
        "max_cost": max_cost,
        "remaining_budget": round(
            max(max_cost - current_cost, 0),
            8
        ),
    }