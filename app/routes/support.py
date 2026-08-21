from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from ..services.support_service import (
    analyze_customer_support
)


router = APIRouter(
    prefix="/api/support",
    tags=["Customer Support Automation"]
)


# =========================================================
# REQUEST SCHEMA
# =========================================================

class SupportRequest(BaseModel):

    customer_email: EmailStr
    subject: str
    message: str


# =========================================================
# HEALTH
# =========================================================

@router.get("/health")
def support_health():

    return {
        "success": True,
        "module": "Customer Support Automation",
        "status": "operational"
    }


# =========================================================
# ANALYZE CUSTOMER REQUEST
# =========================================================

@router.post("/analyze")
def analyze_support_request(
    request: SupportRequest
):

    try:

        analysis = analyze_customer_support(
            customer_email=str(
                request.customer_email
            ),
            subject=request.subject,
            message=request.message
        )

        return {
            "success": True,
            "input": {
                "customer_email":
                    str(request.customer_email),
                "subject":
                    request.subject,
                "message":
                    request.message
            },
            "analysis": analysis
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        print(
            f"Customer support error: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to analyze customer support request."
            )
        )