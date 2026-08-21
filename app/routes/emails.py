from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr

from app.services.email_service import analyze_email
from app.services.notification_service import send_notification


router = APIRouter(
    prefix="/api/emails",
    tags=["Email / Message Intelligence"],
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class EmailAnalysisRequest(BaseModel):

    sender_email: Optional[EmailStr] = None

    subject: str = Field(
        default="",
        max_length=300
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000
    )


class EmailSendRequest(BaseModel):

    sender_email: Optional[EmailStr] = None

    subject: str = Field(
        default="",
        max_length=300
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000
    )

    recipient_email: EmailStr

    send_email: bool = False


# =========================================================
# HEALTH CHECK
# =========================================================

@router.get("/health")
def email_health():

    return {
        "success": True,
        "module": "Email / Message Intelligence",
        "status": "operational"
    }


# =========================================================
# ANALYZE EMAIL
# =========================================================

@router.post("/analyze")
def analyze_email_message(
    request: EmailAnalysisRequest
):

    try:

        analysis = analyze_email(
            subject=request.subject,
            message=request.message,
            sender_email=request.sender_email or ""
        )

        return {
            "success": True,

            "input": {
                "sender_email": request.sender_email,
                "subject": request.subject,
                "message": request.message
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
            f"EMAIL ANALYSIS ERROR: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to analyze the email/message."
        )


# =========================================================
# ANALYZE + OPTIONAL SEND
# =========================================================

@router.post("/process")
def process_email(
    request: EmailSendRequest
):

    try:

        # -------------------------------------------------
        # AI ANALYSIS
        # -------------------------------------------------

        analysis = analyze_email(
            subject=request.subject,
            message=request.message,
            sender_email=request.sender_email or ""
        )

        priority = analysis.get(
            "priority",
            "LOW"
        )

        category = analysis.get(
            "category",
            "General"
        )

        suggested_reply = analysis.get(
            "suggested_reply",
            ""
        )

        recommended_action = analysis.get(
            "recommended_action",
            "AUTOMATED_RESPONSE"
        )

        # -------------------------------------------------
        # HUMAN APPROVAL RULE
        # -------------------------------------------------

        approval_required = (
            priority in {"HIGH", "CRITICAL"}
            or category in {
                "Complaint",
                "Urgent",
                "Finance"
            }
        )

        # -------------------------------------------------
        # HIGH-RISK REQUEST
        # -------------------------------------------------

        if approval_required:

            return {
                "success": True,
                "status": "PENDING_HUMAN_APPROVAL",
                "approval_required": True,

                "reason": (
                    "Sensitive or high-priority message "
                    "requires human approval before sending."
                ),

                "analysis": analysis,
                "draft_reply": suggested_reply
            }

        # -------------------------------------------------
        # DRAFT MODE
        # -------------------------------------------------

        if not request.send_email:

            return {
                "success": True,
                "status": "DRAFT",
                "approval_required": False,
                "analysis": analysis,
                "draft_reply": suggested_reply
            }

        # -------------------------------------------------
        # AUTOMATED SEND
        # -------------------------------------------------

        notification_result = send_notification(
            recipient_email=str(
                request.recipient_email
            ),

            subject=(
                f"Re: {request.subject}"
                if request.subject
                else "Response to your request"
            ),

            message=suggested_reply
        )

        # -------------------------------------------------
        # FINAL RESPONSE
        # -------------------------------------------------

        return {
            "success": (
                notification_result.get("status")
                == "SENT"
            ),

            "status": notification_result.get(
                "status",
                "FAILED"
            ),

            "approval_required": False,

            "analysis": analysis,

            "reply": suggested_reply,

            "notification": notification_result
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        print(
            f"EMAIL PROCESSING ERROR: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to process the email."
        )