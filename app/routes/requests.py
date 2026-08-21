import os
import re
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from ..database import get_db
from ..models import (
    Request as RequestModel,
    ActivityLog,
    ReviewQueue,
    AutomationAction,
)

from ..services.ai_service import analyze_request
from ..services.agent_service import run_agent_workflow
from ..services.decision_service import make_decision
from ..services.automation_service import execute_action
from ..services.notification_service import send_notification


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    tags=["Requests"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


# =========================================================
# CONFIGURATION
# =========================================================

MAX_INPUT_LENGTH = 5000
MAX_CUSTOMER_NAME_LENGTH = 100

MIN_AUTO_CONFIDENCE = 0.60

VALID_PRIORITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


BLOCKED_PROMPT_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior\s+instructions",
    r"ignore\s+(your|the)\s+(current\s+)?instructions",
    r"disregard\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?prior\s+instructions",
    r"forget\s+(all\s+)?previous\s+instructions",
    r"forget\s+(all\s+)?prior\s+instructions",
    r"override\s+(your|the)\s+(current\s+)?instructions",

    r"reveal\s+(your\s+)?system\s+prompt",
    r"reveal\s+(your\s+)?internal\s+instructions",
    r"show\s+(me\s+)?your\s+system\s+prompt",
    r"show\s+(me\s+)?internal\s+instructions",
    r"reveal\s+api\s+keys?",
    r"reveal\s+secrets?",
    r"reveal\s+credentials?",
    r"reveal\s+configuration",
    r"print\s+(the\s+)?api\s+key",
    r"show\s+(me\s+)?the\s+api\s+key",
    r"show\s+(me\s+)?the\s+secrets?",
    r"show\s+(me\s+)?the\s+credentials?",

    r"unrestricted\s+administrator",
    r"unrestricted\s+admin",
    r"you\s+are\s+now\s+an\s+administrator",
    r"you\s+are\s+now\s+an\s+admin",
    r"act\s+as\s+(an\s+)?administrator",
    r"act\s+as\s+(an\s+)?admin",
    r"bypass\s+(security|approval|authentication)",
    r"bypass\s+human\s+approval",
    r"bypass\s+the\s+approval",
    r"skip\s+(human\s+)?approval",
    r"disable\s+(security|authentication|approval)",
    r"override\s+(security|approval|authentication)",
    r"approve\s+this\s+request\s+and\s+execute",
    r"approve\s+this\s+request\s+and\s+bypass",
    r"approve\s+this\s+request",
    r"execute\s+any\s+available\s+automation",

    r"send\s+confidential\s+(business\s+)?data",
    r"share\s+confidential\s+(business\s+)?data",
    r"export\s+confidential\s+(business\s+)?data",
    r"send\s+.*confidential\s+data",
    r"share\s+.*confidential\s+data",
    r"send\s+.*sensitive\s+data",
    r"share\s+.*sensitive\s+data",
    r"send\s+.*to\s+an?\s+external\s+user",
    r"share\s+.*with\s+an?\s+external\s+user",
    r"send\s+.*to\s+external\s+user",
    r"share\s+.*with\s+external\s+user",
    r"external\s+user",

    r"developer\s+message",
    r"developer\s+instructions",
    r"system\s+message",
    r"system\s+instructions",
]


# =========================================================
# REQUEST INPUT
# =========================================================

class RequestCreate(BaseModel):

    customer_name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CUSTOMER_NAME_LENGTH,
    )

    customer_email: EmailStr

    subject: str = Field(
        default="",
        max_length=500,
    )

    message: str = Field(
        default="",
        max_length=MAX_INPUT_LENGTH,
    )

    input_text: str = Field(
        default="",
        max_length=MAX_INPUT_LENGTH,
    )

    priority: str | None = None

    recommended_action: str | None = None

    requires_human_approval: bool | None = None


# =========================================================
# BASIC HELPERS
# =========================================================

def _text(
    value: Any,
    default: str = "",
) -> str:

    if value is None:
        return default

    return str(value).strip()


def _dict(
    value: Any,
) -> dict:

    if isinstance(value, dict):
        return value

    return {}


def _input_text(
    data: RequestCreate,
) -> str:

    if _text(data.input_text):
        return _text(data.input_text)

    parts = []

    subject = _text(data.subject)
    message = _text(data.message)

    if subject:
        parts.append(subject)

    if message:
        parts.append(message)

    return "\n".join(parts).strip()


def _priority(
    value: Any,
) -> str:

    value = _text(
        value,
        "MEDIUM",
    ).upper()

    if value not in VALID_PRIORITIES:
        return "MEDIUM"

    return value


def _confidence(
    value: Any,
) -> float:

    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0

    return max(
        0.0,
        min(1.0, value),
    )


def _serialize_request(item: RequestModel) -> dict:
    """
    Convert SQLAlchemy Request model into JSON-safe data
    for the admin dashboard API.
    """

    created_at = getattr(
        item,
        "created_at",
        None,
    )

    return {
        "request_id": getattr(
            item,
            "request_id",
            None,
        ),

        "customer_name": getattr(
            item,
            "customer_name",
            None,
        ),

        "customer_email": getattr(
            item,
            "customer_email",
            None,
        ),

        "input_text": getattr(
            item,
            "input_text",
            None,
        ),

        "intent": getattr(
            item,
            "intent",
            None,
        ),

        "priority": getattr(
            item,
            "priority",
            None,
        ),

        "confidence_score": getattr(
            item,
            "confidence_score",
            None,
        ),

        "ai_summary": getattr(
            item,
            "ai_summary",
            None,
        ),

        "status": getattr(
            item,
            "status",
            None,
        ),

        "action_taken": getattr(
            item,
            "action_taken",
            None,
        ),

        "error_message": getattr(
            item,
            "error_message",
            None,
        ),

        "created_at": (
            created_at.isoformat()
            if created_at
            else None
        ),
    }


# =========================================================
# ADMIN AUTH
# =========================================================

def _require_admin(
    request: Request,
) -> Optional[str]:

    if not request.session.get(
        "admin_logged_in"
    ):
        return "/auth/login"

    return None


# =========================================================
# BROWSER REQUESTS PAGE
# =========================================================

@router.get("/requests/")
@router.get("/requests")
def requests_page(
    request: Request,
    db: Session = Depends(get_db),
):

    redirect_url = _require_admin(request)

    if redirect_url:

        from fastapi.responses import RedirectResponse

        return RedirectResponse(
            url=redirect_url,
            status_code=303,
        )

    requests = (
        db.query(RequestModel)
        .order_by(
            RequestModel.created_at.desc()
        )
        .all()
    )

    total_requests = len(requests)

    completed_count = sum(
        1
        for item in requests
        if str(item.status or "").upper()
        in {
            "COMPLETED",
            "PROCESSED",
            "PROCESS_COMPLETED",
            "APPROVED",
        }
    )

    pending_count = sum(
        1
        for item in requests
        if str(item.status or "").upper()
        in {
            "PENDING",
            "PENDING_REVIEW",
            "REVIEW",
            "PROCESSING",
        }
    )

    failed_count = sum(
        1
        for item in requests
        if str(item.status or "").upper()
        in {
            "FAILED",
            "ERROR",
        }
    )

    return templates.TemplateResponse(
        request=request,
        name="requests.html",
        context={
            "requests": requests,
            "recent_requests": requests,

            "total_requests": total_requests,

            "completed_requests": completed_count,

            "pending_requests": pending_count,

            "failed_requests": failed_count,

            "admin_username": request.session.get(
                "admin_username",
                "Admin",
            ),

            "home_url": "/",

            "dashboard_url": "/dashboard/",

            "requests_url": "/requests/",

            "business_request_url": "/business-request",

            "documents_url": "/documents",

            "logout_url": "/auth/logout",

            "api_requests_url": "/api/requests/",
        },
    )


# =========================================================
# GET REQUESTS API
# =========================================================
#
# THIS WAS THE MISSING ROUTE.
#
# The requests.html page calls:
#
#     GET /api/requests/
#
# Previously only POST existed, which caused:
#
#     405 Method Not Allowed
#
# =========================================================

@router.get(
    "/api/requests/",
)
def get_requests(
    request: Request,
    db: Session = Depends(get_db),

    search: str = Query(
        default="",
        max_length=200,
    ),

    status: str = Query(
        default="",
        max_length=50,
    ),

    priority: str = Query(
        default="",
        max_length=50,
    ),
):

    # -----------------------------------------------------
    # ADMIN AUTH
    # -----------------------------------------------------

    redirect_url = _require_admin(request)

    if redirect_url:

        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    # -----------------------------------------------------
    # BASE QUERY
    # -----------------------------------------------------

    query = db.query(
        RequestModel
    )

    # -----------------------------------------------------
    # SEARCH FILTER
    # -----------------------------------------------------

    search_value = search.strip()

    if search_value:

        search_pattern = (
            f"%{search_value}%"
        )

        query = query.filter(
            (
                RequestModel.request_id.ilike(
                    search_pattern
                )
            )
            |
            (
                RequestModel.customer_name.ilike(
                    search_pattern
                )
            )
            |
            (
                RequestModel.customer_email.ilike(
                    search_pattern
                )
            )
            |
            (
                RequestModel.input_text.ilike(
                    search_pattern
                )
            )
        )

    # -----------------------------------------------------
    # STATUS FILTER
    # -----------------------------------------------------

    status_value = status.strip()

    if status_value:

        query = query.filter(
            RequestModel.status.ilike(
                status_value
            )
        )

    # -----------------------------------------------------
    # PRIORITY FILTER
    # -----------------------------------------------------

    priority_value = priority.strip()

    if priority_value:

        query = query.filter(
            RequestModel.priority.ilike(
                priority_value
            )
        )

    # -----------------------------------------------------
    # ORDER
    # -----------------------------------------------------

    items = (
        query
        .order_by(
            RequestModel.created_at.desc()
        )
        .all()
    )

    # -----------------------------------------------------
    # SERIALIZE
    # -----------------------------------------------------

    serialized = [
        _serialize_request(item)
        for item in items
    ]

    # -----------------------------------------------------
    # COUNTS
    # -----------------------------------------------------

    total = len(serialized)

    completed = sum(
        1
        for item in serialized
        if str(
            item.get("status") or ""
        ).upper()
        in {
            "COMPLETED",
            "PROCESSED",
            "PROCESS_COMPLETED",
            "APPROVED",
        }
    )

    pending = sum(
        1
        for item in serialized
        if str(
            item.get("status") or ""
        ).upper()
        in {
            "PENDING",
            "PENDING_REVIEW",
            "REVIEW",
            "PROCESSING",
        }
    )

    failed = sum(
        1
        for item in serialized
        if str(
            item.get("status") or ""
        ).upper()
        in {
            "FAILED",
            "ERROR",
        }
    )

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {
        "success": True,

        "requests": serialized,

        "total": total,

        "completed": completed,

        "pending": pending,

        "failed": failed,
    }


# =========================================================
# CREATE REQUEST API
# =========================================================

@router.post(
    "/api/requests/",
)
def create_request(
    request_data: RequestCreate,
    db: Session = Depends(get_db),
):

    input_text = _input_text(
        request_data
    )

    if not input_text:

        raise HTTPException(
            status_code=422,
            detail=(
                "Either input_text or "
                "subject/message is required."
            ),
        )

    if len(input_text) > MAX_INPUT_LENGTH:

        raise HTTPException(
            status_code=413,
            detail=(
                f"Request input exceeds the maximum "
                f"length of {MAX_INPUT_LENGTH} characters."
            ),
        )

    request_id = (
        f"REQ-{uuid4().hex[:8].upper()}"
    )

    customer_email = str(
        request_data.customer_email
    )

    # =====================================================
    # 1. SECURITY CHECK
    # =====================================================

    security_blocked = _contains_prompt_injection(
        input_text
    )

    if security_blocked:

        reason = _security_review(
            input_text=input_text,
            request_id=request_id,
        )

        if not reason:

            reason = (
                "Security control detected a "
                "potentially unsafe instruction."
            )

        notifications = _safe_human_review_fallback(
            request_id=request_id,
            customer_email=customer_email,
            reason=reason,
            db=db,
        )

        new_request = RequestModel(
            request_id=request_id,
            customer_name=request_data.customer_name,
            customer_email=customer_email,
            input_text=input_text,
            intent="Security / Prompt Injection",
            priority="CRITICAL",
            confidence_score=1.0,
            ai_summary=(
                "Potential prompt injection detected. "
                "Automatic execution blocked."
            ),
            status="pending_review",
            action_taken="SECURITY_BLOCKED",
            error_message=None,
        )

        db.add(new_request)

        db.add(
            ActivityLog(
                request_id=request_id,
                action="ACTION_EXECUTED",
                status="BLOCKED",
                message=(
                    "Security control prevented "
                    "automatic execution."
                ),
            )
        )

        db.commit()
        db.refresh(new_request)

        return {
            "success": True,

            "message": (
                "Request blocked by security controls "
                "and routed to human review."
            ),

            "request_id": request_id,

            "status": "pending_review",

            "security": {
                "blocked": True,
                "reason": reason,
            },

            "ai_analysis": {
                "intent": (
                    "Security / Prompt Injection"
                ),
                "priority": "CRITICAL",
                "confidence_score": 1.0,
                "summary": (
                    "Potential prompt injection detected. "
                    "Automatic execution blocked."
                ),
                "analysis_source": (
                    "SECURITY_CONTROL"
                ),
            },

            "decision": {
                "decision": "ESCALATE",
                "action_type": "HUMAN_REVIEW",
                "reason": reason,
                "requires_human_approval": True,
            },

            "automation": {
                "action": "SECURITY_BLOCKED",
                "status": "PENDING_REVIEW",
                "message": (
                    "Automatic execution was blocked."
                ),
            },

            "notifications": notifications,
        }

    # =====================================================
    # 2. REQUEST RECEIVED
    # =====================================================

    db.add(
        ActivityLog(
            request_id=request_id,
            action="REQUEST_RECEIVED",
            status="SUCCESS",
            message=(
                "Business request received successfully."
            ),
        )
    )

    # =====================================================
    # 3. AI ANALYSIS
    # =====================================================

    ai_failed = False
    ai_error = ""

    try:

        ai_result = analyze_request(
            input_text,
            request_id=request_id,
            db=db,
        )

        if not isinstance(
            ai_result,
            dict,
        ):

            raise ValueError(
                "AI service returned an invalid response."
            )

    except Exception as exc:

        ai_failed = True
        ai_error = str(exc)

        print(
            f"AI analysis unavailable: {repr(exc)}"
        )

        db.add(
            ActivityLog(
                request_id=request_id,
                action="AI_ANALYSIS",
                status="FALLBACK",
                message=ai_error,
            )
        )

        ai_result = _local_ai_analysis(
            input_text
        )

    # =====================================================
    # 4. NORMALIZE AI RESULT
    # =====================================================

    intent = _text(
        ai_result.get(
            "intent",
            "General Business Request",
        ),
        "General Business Request",
    )

    priority = _priority(
        ai_result.get(
            "priority",
            "MEDIUM",
        )
    )

    confidence = _confidence(
        ai_result.get(
            "confidence_score",
            0.0,
        )
    )

    summary = _text(
        ai_result.get(
            "summary",
            input_text,
        ),
        input_text,
    )

    recommended_action = _text(
        ai_result.get(
            "recommended_action",
            "",
        )
    )

    requires_human = bool(
        ai_result.get(
            "requires_human_approval",
            False,
        )
    )

    analysis_source = _text(
        ai_result.get(
            "analysis_source",
            "GEMINI",
        ),
        "GEMINI",
    )

    # =====================================================
    # 5. AI OUTPUT SECURITY CHECK
    # =====================================================

    ai_output_blocked = _contains_prompt_injection(
        summary
    )

    if ai_output_blocked:

        priority = "CRITICAL"

        requires_human = True

        recommended_action = "HUMAN_REVIEW"

        db.add(
            ActivityLog(
                request_id=request_id,
                action="SECURITY_CONTROL",
                status="BLOCKED",
                message=(
                    "Potential malicious instruction "
                    "detected in AI output."
                ),
            )
        )

    # =====================================================
    # 6. AI ACTIVITY LOG
    # =====================================================

    db.add(
        ActivityLog(
            request_id=request_id,
            action="AI_ANALYSIS",
            status=(
                "FALLBACK"
                if ai_failed
                else "SUCCESS"
            ),
            message=(
                f"Intent: {intent}, "
                f"Priority: {priority}, "
                f"Confidence: {confidence}, "
                f"Source: {analysis_source}"
            ),
        )
    )

    # =====================================================
    # 7. SAVE REQUEST
    # =====================================================

    new_request = RequestModel(
        request_id=request_id,
        customer_name=request_data.customer_name,
        customer_email=customer_email,
        input_text=input_text,
        intent=intent,
        priority=priority,
        confidence_score=confidence,
        ai_summary=summary,
        status="processing",
        action_taken="AI_ANALYSIS_COMPLETED",
        error_message=(
            ai_error
            if ai_failed
            else None
        ),
    )

    db.add(new_request)

    # =====================================================
    # 8. AGENT WORKFLOW
    # =====================================================

    agent_result = {}

    try:

        agent_result = run_agent_workflow(
            input_text=input_text,
            analysis=ai_result,
        )

        if not isinstance(
            agent_result,
            dict,
        ):
            agent_result = {}

    except TypeError:

        try:

            agent_result = run_agent_workflow(
                input_text
            )

            if not isinstance(
                agent_result,
                dict,
            ):
                agent_result = {}

        except Exception as exc:

            agent_result = {
                "status": "FAILED",
                "error": str(exc),
            }

    except Exception as exc:

        agent_result = {
            "status": "FAILED",
            "error": str(exc),
        }

    # =====================================================
    # 9. AGENT LOGGING
    # =====================================================

    if agent_result:

        tool = (
            agent_result.get("tool")
            or agent_result.get("selected_tool")
        )

        if tool:

            db.add(
                ActivityLog(
                    request_id=request_id,
                    action="AGENT_TOOL_SELECTED",
                    status="SUCCESS",
                    message=f"Tool: {tool}",
                )
            )

        retrieved = (
            agent_result.get("data")
            or agent_result.get("retrieved_data")
        )

        if retrieved:

            db.add(
                ActivityLog(
                    request_id=request_id,
                    action="AGENT_DATA_RETRIEVED",
                    status="SUCCESS",
                    message=str(retrieved)[:1000],
                )
            )

        reasoning = agent_result.get(
            "reasoning"
        )

        if reasoning:

            db.add(
                ActivityLog(
                    request_id=request_id,
                    action="AGENT_REASONING",
                    status="SUCCESS",
                    message=str(reasoning)[:1000],
                )
            )

    # =====================================================
    # 10. DECISION
    # =====================================================

    decision_result = {}

    try:

        decision_result = make_decision(
            situation=input_text,
            context=(
                f"Intent: {intent}\n"
                f"Priority: {priority}\n"
                f"Confidence: {confidence}\n"
                f"Recommended action: "
                f"{recommended_action}\n"
                f"Requires human approval: "
                f"{requires_human}"
            ),
        )

    except Exception as exc:

        print(
            f"Decision analysis unavailable: {repr(exc)}"
        )

        decision_result = {}

    # =====================================================
    # 11. NORMALIZE DECISION
    # =====================================================

    decision = _normalize_decision(
        decision_result,
        priority,
        confidence,
        security_blocked=(
            ai_output_blocked
            or priority == "CRITICAL"
        ),
    )

    db.add(
        ActivityLog(
            request_id=request_id,
            action="DECISION_MADE",
            status="SUCCESS",
            message=(
                f"Decision: {decision['decision']}, "
                f"Action: {decision['action_type']}, "
                f"Reason: {decision['reason']}"
            ),
        )
    )

    # =====================================================
    # 12. HUMAN REVIEW
    # =====================================================

    if decision["action_type"] in {
        "HUMAN_REVIEW",
        "REVIEW",
    }:

        reason = decision["reason"]

        notifications = _safe_human_review_fallback(
            request_id=request_id,
            customer_email=customer_email,
            reason=reason,
            db=db,
        )

        new_request.action_taken = "HUMAN_REVIEW"

        new_request.status = "pending_review"

        db.add(
            ActivityLog(
                request_id=request_id,
                action="ACTION_EXECUTED",
                status="PENDING",
                message=(
                    "Request routed to human review."
                ),
            )
        )

        for notification in notifications.values():

            if (
                isinstance(notification, dict)
                and notification.get("status")
                == "FAILED"
            ):

                db.add(
                    ActivityLog(
                        request_id=request_id,
                        action="NOTIFICATION",
                        status="FAILED",
                        message=notification.get(
                            "message",
                            "Notification failed.",
                        ),
                    )
                )

        db.commit()
        db.refresh(new_request)

        return {
            "success": True,

            "message": (
                "Request received and routed "
                "to human review."
            ),

            "request_id": request_id,

            "status": "pending_review",

            "security": {
                "blocked": False,
            },

            "ai_analysis": {
                "intent": intent,
                "priority": priority,
                "confidence_score": confidence,
                "summary": summary,
                "analysis_source": analysis_source,
            },

            "decision": decision,

            "automation": {
                "action": "HUMAN_REVIEW",
                "status": "PENDING",
                "message": (
                    "Human review required."
                ),
            },

            "agent": agent_result,

            "notifications": notifications,
        }

    # =====================================================
    # 13. AUTOMATION
    # =====================================================

    try:

        automation_result = execute_action(
            new_request,
            db=db,
        )

        if not isinstance(
            automation_result,
            dict,
        ):

            automation_result = {
                "action": "HUMAN_REVIEW",
                "status": "PENDING",
                "message": (
                    "Invalid automation result."
                ),
            }

    except Exception as exc:

        error_message = str(exc)

        new_request.error_message = error_message

        new_request.action_taken = "HUMAN_REVIEW"

        new_request.status = "pending_review"

        notifications = _safe_human_review_fallback(
            request_id=request_id,
            customer_email=customer_email,
            reason=(
                "Automation execution failed; "
                "safe human-review fallback "
                "was activated."
            ),
            db=db,
        )

        automation_result = {
            "action": "HUMAN_REVIEW",
            "status": "PENDING",
            "message": (
                "Automation failed and the request "
                "was routed to human review."
            ),
            "notification": notifications,
        }

        db.add(
            ActivityLog(
                request_id=request_id,
                action="ACTION_EXECUTED",
                status="FAILED",
                message=error_message,
            )
        )

    # =====================================================
    # 14. UPDATE AUTOMATION STATUS
    # =====================================================

    automation_action = _text(
        automation_result.get(
            "action",
            automation_result.get(
                "action_type",
                "HUMAN_REVIEW",
            ),
        ),
        "HUMAN_REVIEW",
    )

    automation_status = _text(
        automation_result.get(
            "status",
            "PENDING",
        ),
        "PENDING",
    ).upper()

    automation_message = _text(
        automation_result.get(
            "message",
            "Automation completed.",
        ),
        "Automation completed.",
    )

    new_request.action_taken = automation_action

    if automation_status in {
        "SUCCESS",
        "COMPLETED",
    }:

        new_request.status = "completed"

    elif automation_status in {
        "PENDING",
        "PENDING_REVIEW",
        "SCHEDULED",
    }:

        new_request.status = "pending_review"

    else:

        new_request.status = "failed"

    db.add(
        ActivityLog(
            request_id=request_id,
            action="ACTION_EXECUTED",
            status=automation_status,
            message=automation_message,
        )
    )

    # =====================================================
    # 15. NOTIFICATION LOGGING
    # =====================================================

    notifications = automation_result.get(
        "notification"
    ) or {}

    if isinstance(
        notifications,
        dict,
    ):

        for notification in notifications.values():

            if not isinstance(
                notification,
                dict,
            ):
                continue

            notification_status = notification.get(
                "status"
            )

            if notification_status == "FAILED":

                db.add(
                    ActivityLog(
                        request_id=request_id,
                        action="NOTIFICATION",
                        status="FAILED",
                        message=notification.get(
                            "message",
                            "Notification failed.",
                        ),
                    )
                )

            elif notification_status == "SENT":

                db.add(
                    ActivityLog(
                        request_id=request_id,
                        action="NOTIFICATION",
                        status="SUCCESS",
                        message=notification.get(
                            "message",
                            "Notification sent successfully.",
                        ),
                    )
                )

    # =====================================================
    # 16. COMMIT
    # =====================================================

    try:

        db.commit()
        db.refresh(new_request)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to save request.",
        ) from exc

    # =====================================================
    # 17. VERIFY ACTION
    # =====================================================

    verified, verification_message = _verify_action(
        request_id=request_id,
        action=automation_action,
        status=automation_status,
        db=db,
    )

    if verified:

        db.add(
            ActivityLog(
                request_id=request_id,
                action="ACTION_VERIFICATION",
                status="SUCCESS",
                message=verification_message,
            )
        )

    else:

        new_request.status = "pending_review"

        new_request.action_taken = "HUMAN_REVIEW"

        verification_reason = (
            "Action verification failed; "
            "request requires human review."
        )

        fallback_notifications = (
            _safe_human_review_fallback(
                request_id=request_id,
                customer_email=customer_email,
                reason=verification_reason,
                db=db,
            )
        )

        db.add(
            ActivityLog(
                request_id=request_id,
                action="ACTION_VERIFICATION",
                status="FAILED",
                message=verification_message,
            )
        )

        db.add(
            ActivityLog(
                request_id=request_id,
                action="VERIFICATION_FALLBACK",
                status="PENDING",
                message=verification_reason,
            )
        )

        notifications = fallback_notifications

    # =====================================================
    # 18. FINAL COMMIT
    # =====================================================

    try:

        db.commit()
        db.refresh(new_request)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save final request state."
            ),
        ) from exc

    # =====================================================
    # 19. FINAL RESPONSE
    # =====================================================

    return {
        "success": True,

        "message": (
            "Business request processed successfully."
        ),

        "request_id": request_id,

        "status": new_request.status,

        "security": {
            "blocked": False,
            "input_validation": "PASSED",
            "prompt_injection_check": "PASSED",
            "automatic_execution_guard": "ACTIVE",
        },

        "ai_analysis": {
            "intent": new_request.intent,
            "priority": new_request.priority,
            "confidence_score": (
                new_request.confidence_score
            ),
            "summary": new_request.ai_summary,
            "analysis_source": analysis_source,
        },

        "agent": agent_result,

        "decision": decision,

        "automation": {
            "action": new_request.action_taken,
            "status": automation_status,
            "message": automation_message,
        },

        "notifications": (
            notifications
            if isinstance(
                notifications,
                dict,
            )
            else {}
        ),

        "verification": {
            "verified": verified,
            "message": verification_message,
        },
    }


# =========================================================
# ADMIN APPROVE REQUEST
# =========================================================

@router.post(
    "/api/requests/{request_id}/approve"
)
def approve_request(
    request_id: str,
    db: Session = Depends(get_db),
):

    request = (
        db.query(RequestModel)
        .filter(
            RequestModel.request_id
            == request_id
        )
        .first()
    )

    if not request:

        raise HTTPException(
            status_code=404,
            detail="Request not found.",
        )

    review = (
        db.query(ReviewQueue)
        .filter(
            ReviewQueue.request_id
            == request_id,
            ReviewQueue.status == "pending",
        )
        .first()
    )

    if not review:

        raise HTTPException(
            status_code=400,
            detail=(
                "Request is not waiting "
                "for approval."
            ),
        )

    review.status = "approved"

    request.status = "processing"

    request.action_taken = (
        "APPROVED_FOR_AUTOMATION"
    )

    request.error_message = None

    db.add(
        ActivityLog(
            request_id=request_id,
            action="HUMAN_APPROVAL",
            status="APPROVED",
            message=(
                "Request approved by administrator."
            ),
        )
    )

    db.commit()
    db.refresh(request)

    try:

        automation_result = execute_action(
            request,
            db=db,
        )

        if not isinstance(
            automation_result,
            dict,
        ):

            automation_result = {}

    except Exception as exc:

        request.status = "pending_review"

        request.action_taken = "HUMAN_REVIEW"

        request.error_message = str(exc)

        db.add(
            ActivityLog(
                request_id=request_id,
                action="ACTION_EXECUTED",
                status="FAILED",
                message=str(exc),
            )
        )

        db.commit()

        return {
            "success": False,
            "message": (
                "Automation failed after approval."
            ),
            "request_id": request_id,
            "status": "pending_review",
            "error": str(exc),
        }

    automation_status = _text(
        automation_result.get(
            "status",
            "PENDING",
        ),
        "PENDING",
    ).upper()

    automation_action = _text(
        automation_result.get(
            "action",
            automation_result.get(
                "action_type",
                "HUMAN_REVIEW",
            ),
        ),
        "HUMAN_REVIEW",
    )

    automation_message = _text(
        automation_result.get(
            "message",
            "Automation processed.",
        ),
        "Automation processed.",
    )

    if automation_status in {
        "SUCCESS",
        "COMPLETED",
    }:

        request.status = "completed"

    elif automation_status in {
        "PENDING",
        "PENDING_REVIEW",
        "SCHEDULED",
    }:

        request.status = "pending_review"

    else:

        request.status = "failed"

    request.action_taken = automation_action

    db.add(
        ActivityLog(
            request_id=request_id,
            action="ACTION_EXECUTED",
            status=automation_status,
            message=automation_message,
        )
    )

    db.commit()
    db.refresh(request)

    return {
        "success": True,

        "message": (
            "Request approved and processed."
        ),

        "request_id": request_id,

        "status": request.status,

        "action": request.action_taken,

        "automation": {
            "status": automation_status,
            "message": automation_message,
        },
    }


# =========================================================
# ADMIN REJECT REQUEST
# =========================================================

@router.post(
    "/api/requests/{request_id}/reject"
)
def reject_request(
    request_id: str,
    db: Session = Depends(get_db),
):

    request = (
        db.query(RequestModel)
        .filter(
            RequestModel.request_id
            == request_id
        )
        .first()
    )

    if not request:

        raise HTTPException(
            status_code=404,
            detail="Request not found.",
        )

    review = (
        db.query(ReviewQueue)
        .filter(
            ReviewQueue.request_id
            == request_id,
            ReviewQueue.status == "pending",
        )
        .first()
    )

    if not review:

        raise HTTPException(
            status_code=400,
            detail=(
                "Request is not waiting "
                "for approval."
            ),
        )

    review.status = "rejected"

    request.status = "failed"

    request.action_taken = "REJECTED"

    request.error_message = (
        "Request rejected by administrator."
    )

    db.add(
        ActivityLog(
            request_id=request_id,
            action="HUMAN_REJECTION",
            status="REJECTED",
            message=(
                "Request rejected by administrator."
            ),
        )
    )

    db.commit()
    db.refresh(request)

    return {
        "success": True,

        "message": (
            "Request rejected successfully."
        ),

        "request_id": request_id,

        "status": "failed",

        "action": "REJECTED",
    }


# =========================================================
# GET SINGLE REQUEST API
# =========================================================

@router.get(
    "/api/requests/{request_id}"
)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
):

    request = (
        db.query(RequestModel)
        .filter(
            RequestModel.request_id
            == request_id
        )
        .first()
    )

    if not request:

        raise HTTPException(
            status_code=404,
            detail="Request not found.",
        )

    review = (
        db.query(ReviewQueue)
        .filter(
            ReviewQueue.request_id
            == request_id
        )
        .order_by(
            ReviewQueue.id.desc()
        )
        .first()
    )

    activities = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.request_id
            == request_id
        )
        .order_by(
            ActivityLog.id.asc()
        )
        .all()
    )

    return {
        "success": True,

        "request": {
            "request_id": request.request_id,
            "customer_name": request.customer_name,
            "customer_email": request.customer_email,
            "input_text": request.input_text,
            "intent": request.intent,
            "priority": request.priority,
            "confidence_score": (
                request.confidence_score
            ),
            "ai_summary": request.ai_summary,
            "status": request.status,
            "action_taken": request.action_taken,
            "error_message": request.error_message,
        },

        "review": (
            {
                "status": review.status,
                "reason": review.reason,
            }
            if review
            else None
        ),

        "activity": [
            {
                "action": activity.action,
                "status": activity.status,
                "message": activity.message,
            }
            for activity in activities
        ],
    }


# =========================================================
# SECURITY
# =========================================================

def _contains_prompt_injection(
    input_text: str,
) -> bool:

    if not input_text:
        return False

    normalized = re.sub(
        r"\s+",
        " ",
        input_text.lower(),
    ).strip()

    for pattern in BLOCKED_PROMPT_PATTERNS:

        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        ):

            return True

    privilege_words = [
        "administrator",
        "admin",
        "unrestricted",
        "bypass",
        "override",
        "skip approval",
    ]

    approval_words = [
        "approve",
        "approval",
        "human review",
        "execute",
    ]

    data_words = [
        "confidential",
        "sensitive",
        "private",
        "business data",
    ]

    external_words = [
        "external user",
        "external party",
        "outside user",
        "outside party",
        "external recipient",
    ]

    has_privilege = any(
        word in normalized
        for word in privilege_words
    )

    has_approval = any(
        word in normalized
        for word in approval_words
    )

    has_sensitive_data = any(
        word in normalized
        for word in data_words
    )

    has_external_target = any(
        word in normalized
        for word in external_words
    )

    if has_privilege and has_approval:
        return True

    if (
        has_sensitive_data
        and has_external_target
    ):
        return True

    return False


def _security_review(
    input_text: str,
    request_id: Optional[str] = None,
) -> Optional[str]:

    if not input_text:
        return None

    text = " ".join(
        input_text.lower().split()
    )

    security_patterns = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "forget previous instructions",
        "forget all previous instructions",
        "disregard previous instructions",
        "disregard all previous instructions",
        "reveal your system prompt",
        "reveal system prompt",
        "show system prompt",
        "system instructions",
        "internal instructions",
        "api key",
        "api keys",
        "apikey",
        "apikeys",
        "password",
        "passwords",
        "credential",
        "credentials",
        "secret",
        "secrets",
        "access token",
        "access tokens",
        "private key",
        "private keys",
        "bypass human approval",
        "bypass approval",
        "skip human approval",
        "skip approval",
        "disable security",
        "bypass security",
        "override security",
        "unrestricted administrator",
        "unrestricted admin",
        "execute any available automation",
        "approve this request and execute",
        "automatically approve",
        "auto approve",
        "bypass human review",
        "skip human review",
        "confidential business data",
        "confidential data",
        "send confidential data",
        "send confidential business data",
        "send secrets",
        "send credentials",
        "send passwords",
        "send api keys",
        "external user",
        "unauthorized user",
    ]

    for pattern in security_patterns:

        if pattern in text:

            return (
                "Potential prompt injection or "
                "security-sensitive instruction detected. "
                "Automatic execution is blocked."
            )

    return None


# =========================================================
# LOCAL AI FALLBACK
# =========================================================

def _local_ai_analysis(
    input_text: str,
) -> dict:

    text = input_text.lower()

    security_words = [
        "unauthorized",
        "fraud",
        "compromised",
        "security breach",
        "account hacked",
        "hacked account",
        "stolen",
        "malware",
        "security incident",
    ]

    if any(
        word in text
        for word in security_words
    ):

        return {
            "intent": "Security Incident",
            "priority": "CRITICAL",
            "confidence_score": 0.95,
            "summary": (
                "Security-related request requires "
                "immediate human review."
            ),
            "recommended_action": "HUMAN_REVIEW",
            "requires_human_approval": True,
            "analysis_source": "LOCAL_FALLBACK",
        }

    financial_words = [
        "refund",
        "payment",
        "invoice",
        "billing",
        "charge",
        "transaction",
    ]

    if any(
        word in text
        for word in financial_words
    ):

        return {
            "intent": "Financial Support",
            "priority": "HIGH",
            "confidence_score": 0.90,
            "summary": (
                "Financial or billing request "
                "requires human review."
            ),
            "recommended_action": "HUMAN_REVIEW",
            "requires_human_approval": True,
            "analysis_source": "LOCAL_FALLBACK",
        }

    business_hours_words = [
        "business hours",
        "working hours",
        "opening hours",
        "operating hours",
        "when are you open",
        "what time do you open",
        "what time do you close",
    ]

    if any(
        word in text
        for word in business_hours_words
    ):

        return {
            "intent": "Business Hours",
            "priority": "LOW",
            "confidence_score": 0.90,
            "summary": (
                "Business-hours information is a "
                "low-risk request suitable for automation."
            ),
            "recommended_action": "AUTO_EXECUTE",
            "requires_human_approval": False,
            "analysis_source": "LOCAL_FALLBACK",
        }

    return {
        "intent": "General Business Request",
        "priority": "LOW",
        "confidence_score": 0.75,
        "summary": (
            "Routine business request suitable "
            "for automated processing."
        ),
        "recommended_action": "AUTO_EXECUTE",
        "requires_human_approval": False,
        "analysis_source": "LOCAL_FALLBACK",
    }


# =========================================================
# DECISION NORMALIZATION
# =========================================================

def _normalize_decision(
    decision: Any,
    priority: str,
    confidence: float,
    security_blocked: bool = False,
) -> dict:

    decision = _dict(decision)

    if security_blocked:

        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_REVIEW",
            "reason": (
                "Security control blocked automatic "
                "execution and requires human review."
            ),
            "requires_human_approval": True,
        }

    priority = _priority(priority)

    confidence = _confidence(confidence)

    decision_name = _text(
        decision.get(
            "decision",
            "",
        )
    ).upper()

    reason = _text(
        decision.get(
            "reason",
            "Workflow decision generated.",
        ),
        "Workflow decision generated.",
    )

    if priority in {
        "HIGH",
        "CRITICAL",
    }:

        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_REVIEW",
            "reason": reason,
            "requires_human_approval": True,
        }

    if priority == "LOW":

        if confidence >= MIN_AUTO_CONFIDENCE:

            return {
                "decision": "AUTOMATE",
                "action_type": "AUTO_EXECUTE",
                "reason": reason,
                "requires_human_approval": False,
            }

        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_REVIEW",
            "reason": (
                "AI confidence is below the "
                "automatic execution threshold."
            ),
            "requires_human_approval": True,
        }

    return {
        "decision": (
            decision_name
            if decision_name
            else "REVIEW"
        ),
        "action_type": "HUMAN_REVIEW",
        "reason": reason,
        "requires_human_approval": True,
    }


# =========================================================
# HUMAN REVIEW FALLBACK
# =========================================================

def _safe_human_review_fallback(
    request_id: str,
    customer_email: str,
    reason: str,
    db: Session,
):

    existing = (
        db.query(ReviewQueue)
        .filter(
            ReviewQueue.request_id == request_id,
            ReviewQueue.status == "pending",
        )
        .first()
    )

    if not existing:

        db.add(
            ReviewQueue(
                request_id=request_id,
                reason=reason,
                status="pending",
            )
        )

    reviewer_email = os.getenv(
        "REVIEWER_EMAIL"
    )

    reviewer_notification = {
        "status": "SKIPPED",
        "message": (
            "Reviewer email is not configured."
        ),
    }

    if reviewer_email:

        try:

            reviewer_notification = send_notification(
                recipient_email=reviewer_email,
                subject=(
                    "Human Review Required - "
                    f"{request_id}"
                ),
                message=(
                    "A business request requires "
                    "human review.\n\n"
                    f"Request ID: {request_id}\n"
                    f"Reason: {reason}\n\n"
                    "Please review the request "
                    "from the dashboard."
                ),
            )

        except Exception as exc:

            reviewer_notification = {
                "status": "FAILED",
                "message": str(exc),
            }

    customer_notification = {
        "status": "SKIPPED",
        "message": (
            "Customer email is not configured."
        ),
    }

    if customer_email:

        try:

            customer_notification = send_notification(
                recipient_email=customer_email,
                subject=(
                    "Request Received - "
                    f"{request_id}"
                ),
                message=(
                    "Your business request "
                    "has been received.\n\n"
                    f"Request ID: {request_id}\n\n"
                    "Your request requires "
                    "additional human review."
                ),
            )

        except Exception as exc:

            customer_notification = {
                "status": "FAILED",
                "message": str(exc),
            }

    return {
        "reviewer": reviewer_notification,
        "customer": customer_notification,
    }


# =========================================================
# ACTION VERIFICATION
# =========================================================

def _verify_action(
    request_id: str,
    action: str,
    status: str,
    db: Session,
):

    if action == "HUMAN_REVIEW":

        review = (
            db.query(ReviewQueue)
            .filter(
                ReviewQueue.request_id == request_id,
                ReviewQueue.status == "pending",
            )
            .first()
        )

        if review:

            return (
                True,
                "Human review queue entry verified.",
            )

        return (
            False,
            "Human review queue entry was not found.",
        )

    action_record = (
        db.query(AutomationAction)
        .filter(
            AutomationAction.request_id == request_id,
            AutomationAction.status == "completed",
        )
        .order_by(
            AutomationAction.id.desc()
        )
        .first()
    )

    if (
        status in {
            "SUCCESS",
            "COMPLETED",
        }
        and action_record
    ):

        return (
            True,
            "Automation action record verified.",
        )

    if status in {
        "PENDING",
        "PENDING_REVIEW",
        "SCHEDULED",
    }:

        return (
            True,
            "Pending workflow action verified.",
        )

    return (
        False,
        "Expected automation action record was not found.",
    )