from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models import ActivityLog


# =========================================================
# CREATE ACTIVITY LOG
# =========================================================

def create_activity_log(
    db: Session,
    request_id: str,
    action: str,
    status: str,
    message: Optional[str] = None,
):
    """
    Create and store an activity/audit log.
    """

    log = ActivityLog(
        request_id=request_id,
        action=action,
        status=status,
        message=message,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


# =========================================================
# GET ACTIVITY LOGS
# =========================================================

def get_activity_logs(
    db: Session,
    request_id: Optional[str] = None,
):
    """
    Retrieve activity logs.

    If request_id is provided, only logs belonging
    to that request are returned.
    """

    query = db.query(ActivityLog)

    if request_id:
        query = query.filter(
            ActivityLog.request_id == request_id
        )

    return (
        query
        .order_by(
            ActivityLog.created_at.desc()
        )
        .all()
    )


# =========================================================
# GET SINGLE ACTIVITY LOG
# =========================================================

def get_activity_log(
    db: Session,
    log_id: int,
):
    """
    Retrieve a single activity log by ID.
    """

    return (
        db.query(ActivityLog)
        .filter(ActivityLog.id == log_id)
        .first()
    )


# =========================================================
# DELETE ACTIVITY LOG
# =========================================================

def delete_activity_log(
    db: Session,
    log_id: int,
):
    """
    Delete an activity log by ID.
    """

    log = (
        db.query(ActivityLog)
        .filter(ActivityLog.id == log_id)
        .first()
    )

    if not log:
        return None

    db.delete(log)
    db.commit()

    return log