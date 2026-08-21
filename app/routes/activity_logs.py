from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ActivityLog
from ..services.audit_service import get_activity_logs


router = APIRouter(
    prefix="/api/activity-logs",
    tags=["Activity Logs"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


# =========================================================
# API — GET ACTIVITY LOGS
# =========================================================

@router.get("/")
def activity_logs(
    db: Session = Depends(get_db)
):
    logs = get_activity_logs(db)

    return {
        "success": True,
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "request_id": log.request_id,
                "action": log.action,
                "status": log.status,
                "message": log.message,
                "created_at": (
                    log.created_at.isoformat()
                    if log.created_at
                    else None
                ),
            }
            for log in logs
        ],
    }


# =========================================================
# ADMIN — ACTIVITY PAGE
# =========================================================

@router.get(
    "/activity",
    include_in_schema=False
)
def activity_page(
    request: Request,
    db: Session = Depends(get_db)
):
    # Admin authentication
    if not request.session.get("admin_authenticated"):
        from fastapi.responses import RedirectResponse

        return RedirectResponse(
            url="/auth/login",
            status_code=303
        )

    activities = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(200)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="activity.html",
        context={
            "admin_username": request.session.get(
                "admin_username",
                "admin"
            ),
            "activities": activities,
        },
    )