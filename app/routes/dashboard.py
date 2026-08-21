# app/routes/dashboard.py

from datetime import datetime, timedelta
from collections import Counter
import json
from urllib.parse import quote_plus

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Request as RequestModel,
    ActivityLog,
    ReviewQueue,
    AutomationAction,
)
from .reviews import approve_review, reject_review


router = APIRouter()

templates = Jinja2Templates(
    directory="app/templates"
)


# =========================================================
# ADMIN AUTH
# =========================================================

def _require_admin(request: Request):

    if not request.session.get("admin_logged_in"):
        return RedirectResponse(
            url="/auth/login",
            status_code=303,
        )

    return None


# =========================================================
# DASHBOARD
# =========================================================

@router.get("/dashboard")
@router.get("/dashboard/")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):

    redirect = _require_admin(request)

    if redirect:
        return redirect

    # =====================================================
    # REQUEST COUNTS
    # =====================================================

    total_requests = (
        db.query(RequestModel).count()
    )

    completed_requests = (
        db.query(RequestModel)
        .filter(
            RequestModel.status.in_(
                [
                    "completed",
                    "COMPLETED",
                    "processed",
                    "PROCESS_COMPLETED",
                    "approved",
                    "APPROVED",
                ]
            )
        )
        .count()
    )

    failed_requests = (
        db.query(RequestModel)
        .filter(
            RequestModel.status.in_(
                [
                    "failed",
                    "FAILED",
                    "error",
                    "ERROR",
                ]
            )
        )
        .count()
    )

    pending_requests = (
        db.query(RequestModel)
        .filter(
            RequestModel.status.in_(
                [
                    "pending",
                    "PENDING",
                    "pending_review",
                    "review",
                    "REVIEW",
                ]
            )
        )
        .count()
    )

    processing_requests = (
        db.query(RequestModel)
        .filter(
            RequestModel.status.in_(
                [
                    "processing",
                    "PROCESSING",
                    "in_progress",
                    "IN_PROGRESS",
                ]
            )
        )
        .count()
    )

    # =====================================================
    # REVIEW COUNTS
    # =====================================================

    pending_reviews_count = (
        db.query(ReviewQueue)
        .filter(
            ReviewQueue.status == "pending"
        )
        .count()
    )

    # =====================================================
    # PRIORITY
    # =====================================================

    high_priority = (
        db.query(RequestModel)
        .filter(
            RequestModel.priority.in_(
                [
                    "HIGH",
                    "CRITICAL",
                ]
            )
        )
        .count()
    )

    # =====================================================
    # AUTOMATION COUNTS
    # =====================================================

    successful_automations = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.status == "SUCCESS",
            ActivityLog.action.in_(
                [
                    "ACTION_EXECUTED",
                    "EXECUTE_SCHEDULED_AUTOMATION",
                    "ACTION_VERIFICATION",
                    "REQUEST_COMPLETED",
                ]
            ),
        )
        .count()
    )

    failed_automations = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.status == "FAILED"
        )
        .count()
    )

    # =====================================================
    # SCHEDULER COUNTS
    # =====================================================

    scheduled_count = (
        db.query(AutomationAction)
        .filter(
            AutomationAction.status == "scheduled"
        )
        .count()
    )

    running_count = (
        db.query(AutomationAction)
        .filter(
            AutomationAction.status == "running"
        )
        .count()
    )

    scheduler_completed_count = (
        db.query(AutomationAction)
        .filter(
            AutomationAction.status == "completed"
        )
        .count()
    )

    scheduler_failed_count = (
        db.query(AutomationAction)
        .filter(
            AutomationAction.status == "failed"
        )
        .count()
    )

    # =====================================================
    # STATUS COUNTER
    # =====================================================

    status_counter = Counter(
        row[0] or "UNKNOWN"
        for row in db.query(
            RequestModel.status
        ).all()
    )

    # =====================================================
    # PRIORITY COUNTER
    # =====================================================

    priority_counter = Counter(
        row[0] or "UNKNOWN"
        for row in db.query(
            RequestModel.priority
        ).all()
    )

    # =====================================================
    # ACTIVITY COUNTER
    # =====================================================

    activity_counter = Counter(
        row[0] or "UNKNOWN"
        for row in db.query(
            ActivityLog.status
        ).all()
    )

    # =====================================================
    # RECENT REQUESTS
    # =====================================================

    recent_requests = (
        db.query(RequestModel)
        .order_by(
            RequestModel.created_at.desc()
        )
        .limit(10)
        .all()
    )

    # =====================================================
    # PENDING REVIEWS
    # =====================================================

    pending_reviews = (
        db.query(
            ReviewQueue,
            RequestModel,
        )
        .join(
            RequestModel,
            ReviewQueue.request_id
            == RequestModel.request_id,
        )
        .filter(
            ReviewQueue.status == "pending"
        )
        .order_by(
            RequestModel.created_at.desc()
        )
        .all()
    )

    # =====================================================
    # RECENT ACTIVITY
    # =====================================================

    recent_activity = (
        db.query(ActivityLog)
        .order_by(
            ActivityLog.created_at.desc()
        )
        .limit(20)
        .all()
    )

    # =====================================================
    # 7 DAY REQUEST ACTIVITY
    # =====================================================

    today = datetime.now().date()

    activity_day_labels = []
    activity_day_values = []

    created_rows = (
        db.query(
            RequestModel.created_at
        ).all()
    )

    for offset in range(6, -1, -1):

        day = today - timedelta(
            days=offset
        )

        activity_day_labels.append(
            day.strftime("%d %b")
        )

        count = 0

        for row in created_rows:

            created_at = row[0]

            if created_at is None:
                continue

            try:

                if hasattr(
                    created_at,
                    "date",
                ):
                    created_date = (
                        created_at.date()
                    )

                else:
                    created_date = (
                        datetime.fromisoformat(
                            str(created_at)
                        ).date()
                    )

            except (
                TypeError,
                ValueError,
            ):
                continue

            if created_date == day:
                count += 1

        activity_day_values.append(
            count
        )

    # =====================================================
    # DAILY REPORT
    # =====================================================

    daily_report = {
        "requests": sum(
            activity_day_values
        ),
        "successful": successful_automations,
        "failed": failed_automations,
        "pending": pending_requests,
        "processing": processing_requests,
        "completed": completed_requests,
        "reviews": pending_reviews_count,
    }

    # =====================================================
    # CHART DATA
    # =====================================================

    chart_data = {

        "request_status": {
            "labels": list(
                status_counter.keys()
            ),
            "values": list(
                status_counter.values()
            ),
        },

        "priority": {
            "labels": list(
                priority_counter.keys()
            ),
            "values": list(
                priority_counter.values()
            ),
        },

        "automation": {
            "labels": [
                "Successful",
                "Failed",
                "Pending Review",
            ],
            "values": [
                successful_automations,
                failed_automations,
                pending_reviews_count,
            ],
        },

        "scheduler": {
            "labels": [
                "Scheduled",
                "Running",
                "Completed",
                "Failed",
            ],
            "values": [
                scheduled_count,
                running_count,
                scheduler_completed_count,
                scheduler_failed_count,
            ],
        },

        "activity": {
            "labels": list(
                activity_counter.keys()
            ),
            "values": list(
                activity_counter.values()
            ),
        },

        "request_activity": {
            "labels": activity_day_labels,
            "values": activity_day_values,
        },
    }

    # =====================================================
    # METRICS
    # =====================================================

    metrics = {

        "total_requests":
            total_requests,

        "pending_requests":
            pending_requests,

        "processing_requests":
            processing_requests,

        "completed_requests":
            completed_requests,

        "failed_requests":
            failed_requests,

        "pending_reviews":
            pending_reviews_count,

        "high_priority":
            high_priority,

        "successful_automations":
            successful_automations,

        "failed_automations":
            failed_automations,

        "scheduled_count":
            scheduled_count,

        "running_count":
            running_count,

        "scheduler_completed_count":
            scheduler_completed_count,

        "scheduler_failed_count":
            scheduler_failed_count,
    }

    # =====================================================
    # TEMPLATE
    # =====================================================

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={

            "metrics":
                metrics,

            **metrics,

            "daily_report":
                daily_report,

            "recent_requests":
                recent_requests,

            "pending_review_items":
                pending_reviews,

            "recent_activity":
                recent_activity,

            "chart_data":
                json.dumps(
                    chart_data
                ),

            "activity_day_labels":
                activity_day_labels,

            "activity_day_values":
                activity_day_values,

            "admin_username":
                request.session.get(
                    "admin_username",
                    "Admin",
                ),

            "success_message":
                request.query_params.get(
                    "success"
                ),

            "error_message":
                request.query_params.get(
                    "error"
                ),

            "home_url":
                "/",

            "business_request_url":
                "/business-request",

            "documents_url":
                "/documents",

            "requests_url":
                "/requests/",

            "dashboard_url":
                "/dashboard/",

            "logout_url":
                "/auth/logout",
        },
    )


# =========================================================
# APPROVE REVIEW
# =========================================================

@router.post(
    "/dashboard/review/{request_id}/approve"
)
def dashboard_approve(
    request: Request,
    request_id: str,
    db: Session = Depends(get_db),
):

    redirect = _require_admin(request)

    if redirect:
        return redirect

    try:

        approve_review(
            request_id=request_id,
            db=db,
        )

        return RedirectResponse(
            url=(
                "/dashboard/?success="
                + quote_plus(
                    "Request approved successfully"
                )
            ),
            status_code=303,
        )

    except HTTPException as exc:

        return RedirectResponse(
            url=(
                "/dashboard/?error="
                + quote_plus(
                    str(exc.detail)
                )
            ),
            status_code=303,
        )


# =========================================================
# REJECT REVIEW
# =========================================================

@router.post(
    "/dashboard/review/{request_id}/reject"
)
def dashboard_reject(
    request: Request,
    request_id: str,
    db: Session = Depends(get_db),
):

    redirect = _require_admin(request)

    if redirect:
        return redirect

    try:

        reject_review(
            request_id=request_id,
            db=db,
        )

        return RedirectResponse(
            url=(
                "/dashboard/?success="
                + quote_plus(
                    "Request rejected successfully"
                )
            ),
            status_code=303,
        )

    except HTTPException as exc:

        return RedirectResponse(
            url=(
                "/dashboard/?error="
                + quote_plus(
                    str(exc.detail)
                )
            ),
            status_code=303,
        )


# =========================================================
# ADMIN ACTION PAGE
# =========================================================

@router.get("/admin-actions")
def admin_actions(
    request: Request,
):

    redirect = _require_admin(request)

    if redirect:
        return redirect

    return templates.TemplateResponse(
        request=request,
        name="customer_dashboard.html",
        context={

            "admin_username":
                request.session.get(
                    "admin_username",
                    "Admin",
                ),

            "business_request_url":
                "/business-request",

            "documents_url":
                "/documents",

            "requests_url":
                "/requests/",
        },
    )