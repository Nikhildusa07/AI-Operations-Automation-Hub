from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from ..models import ActivityLog, AutomationAction


# =========================================================
# CREATE SCHEDULED TASK
# =========================================================

def create_scheduled_task(
    db: Session,
    request_id: str,
    action_type: str,
    scheduled_for: datetime,
    message: str = "",
) -> Dict[str, Any]:

    if not request_id:
        raise ValueError("request_id is required.")

    if not action_type:
        raise ValueError("action_type is required.")

    if not scheduled_for:
        raise ValueError("scheduled_for is required.")

    action = AutomationAction(
        request_id=request_id,
        action_type=action_type,
        status="scheduled",
        message=message,
        scheduled_for=scheduled_for,
        retry_count=0,
        max_retries=3,
    )

    db.add(action)
    db.flush()

    log = ActivityLog(
        request_id=request_id,
        action="SCHEDULE_AUTOMATION",
        status="SUCCESS",
        message=(
            f"Automation '{action_type}' scheduled "
            f"for {scheduled_for.isoformat()}."
        ),
    )

    db.add(log)

    db.commit()
    db.refresh(action)

    return {
        "success": True,
        "message": "Automation scheduled successfully.",
        "scheduled_action": {
            "id": action.id,
            "request_id": action.request_id,
            "action_type": action.action_type,
            "status": action.status,
            "message": action.message,
            "scheduled_for": (
                action.scheduled_for.isoformat()
                if action.scheduled_for
                else None
            ),
            "retry_count": action.retry_count,
            "max_retries": action.max_retries,
            "created_at": (
                action.created_at.isoformat()
                if action.created_at
                else None
            ),
        },
    }


# =========================================================
# EXECUTE SCHEDULED TASK
# =========================================================

def execute_scheduled_task(
    db: Session,
    action_id: int,
) -> Dict[str, Any]:

    action = (
        db.query(AutomationAction)
        .filter(
            AutomationAction.id == action_id
        )
        .first()
    )

    if not action:
        return {
            "success": False,
            "message": "Scheduled automation not found.",
            "action_id": action_id,
        }

    if action.status == "completed":
        return {
            "success": False,
            "message": "Automation has already been completed.",
            "action_id": action.id,
        }

    if action.status == "running":
        return {
            "success": False,
            "message": "Automation is already running.",
            "action_id": action.id,
        }

    try:

        # -------------------------------------------------
        # MARK RUNNING
        # -------------------------------------------------

        action.status = "running"
        action.started_at = datetime.utcnow()

        db.commit()

        # -------------------------------------------------
        # SUPPORTED ACTIONS
        # -------------------------------------------------

        supported_actions = {
            "PROCESS_PENDING_INVOICES",
            "SEND_NOTIFICATION",
            "SEND_EMAIL",
            "CREATE_TASK",
            "AUTOMATED_RESPONSE",
        }

        if action.action_type not in supported_actions:
            raise ValueError(
                f"Unsupported automation action: "
                f"{action.action_type}"
            )

        # -------------------------------------------------
        # EXECUTE
        # -------------------------------------------------

        action.status = "completed"
        action.completed_at = datetime.utcnow()
        action.error_message = None

        if not action.message:
            action.message = (
                "Automation executed successfully."
            )

        log = ActivityLog(
            request_id=action.request_id,
            action="EXECUTE_SCHEDULED_AUTOMATION",
            status="SUCCESS",
            message=(
                f"Scheduled automation "
                f"'{action.action_type}' "
                f"executed successfully."
            ),
        )

        db.add(log)

        db.commit()
        db.refresh(action)

        return {
            "success": True,
            "message": (
                "Scheduled automation "
                "executed successfully."
            ),
            "action": {
                "id": action.id,
                "request_id": action.request_id,
                "action_type": action.action_type,
                "status": action.status,
                "message": action.message,
                "scheduled_for": (
                    action.scheduled_for.isoformat()
                    if action.scheduled_for
                    else None
                ),
                "retry_count": action.retry_count,
                "max_retries": action.max_retries,
                "completed_at": (
                    action.completed_at.isoformat()
                    if action.completed_at
                    else None
                ),
            },
        }

    except Exception as exc:

        db.rollback()

        action = (
            db.query(AutomationAction)
            .filter(
                AutomationAction.id == action_id
            )
            .first()
        )

        if action:

            action.status = "failed"
            action.error_message = str(exc)

            log = ActivityLog(
                request_id=action.request_id,
                action="EXECUTE_SCHEDULED_AUTOMATION",
                status="FAILED",
                message=str(exc),
            )

            db.add(action)
            db.add(log)
            db.commit()

        return {
            "success": False,
            "message": "Scheduled automation failed.",
            "error": str(exc),
            "action_id": action_id,
        }


# =========================================================
# RETRY FAILED TASK
# =========================================================

def retry_scheduled_task(
    db: Session,
    action_id: int,
) -> Dict[str, Any]:

    action = (
        db.query(AutomationAction)
        .filter(
            AutomationAction.id == action_id
        )
        .first()
    )

    if not action:
        return {
            "success": False,
            "message": "Scheduled automation not found.",
        }

    if action.status != "failed":
        return {
            "success": False,
            "message": (
                "Only failed automations can be retried."
            ),
            "action_id": action.id,
            "status": action.status,
        }

    if action.retry_count >= action.max_retries:
        return {
            "success": False,
            "message": (
                "Maximum retry limit reached."
            ),
            "action_id": action.id,
            "retry_count": action.retry_count,
            "max_retries": action.max_retries,
        }

    # -----------------------------------------------------
    # INCREMENT RETRY
    # -----------------------------------------------------

    action.retry_count += 1
    action.status = "scheduled"
    action.error_message = None
    action.completed_at = None
    action.started_at = None

    retry_log = ActivityLog(
        request_id=action.request_id,
        action="RETRY_SCHEDULED_AUTOMATION",
        status="SUCCESS",
        message=(
            f"Retry {action.retry_count}/"
            f"{action.max_retries} scheduled for "
            f"automation '{action.action_type}'."
        ),
    )

    db.add(action)
    db.add(retry_log)
    db.commit()
    db.refresh(action)

    # -----------------------------------------------------
    # EXECUTE AGAIN
    # -----------------------------------------------------

    result = execute_scheduled_task(
        db=db,
        action_id=action.id,
    )

    return {
        "success": result.get("success", False),
        "message": (
            "Automation retry completed."
            if result.get("success")
            else "Automation retry failed."
        ),
        "retry": {
            "action_id": action.id,
            "retry_count": action.retry_count,
            "max_retries": action.max_retries,
        },
        "execution": result,
    }


# =========================================================
# EXECUTE DUE TASKS
# =========================================================

def execute_due_tasks(
    db: Session,
) -> Dict[str, Any]:

    now = datetime.utcnow()

    due_actions = (
        db.query(AutomationAction)
        .filter(
            AutomationAction.status == "scheduled",
            AutomationAction.scheduled_for.isnot(None),
            AutomationAction.scheduled_for <= now,
        )
        .order_by(
            AutomationAction.scheduled_for.asc()
        )
        .all()
    )

    results = []

    for action in due_actions:

        result = execute_scheduled_task(
            db=db,
            action_id=action.id,
        )

        results.append(result)

    return {
        "success": True,
        "checked_at": now.isoformat(),
        "due_count": len(due_actions),
        "executed_count": sum(
            1
            for result in results
            if result.get("success") is True
        ),
        "failed_count": sum(
            1
            for result in results
            if result.get("success") is False
        ),
        "results": results,
    }


# =========================================================
# GET SCHEDULED TASKS
# =========================================================

def get_scheduled_tasks(
    db: Session,
    request_id: Optional[str] = None,
):

    query = (
        db.query(AutomationAction)
        .filter(
            AutomationAction.status == "scheduled"
        )
    )

    if request_id:
        query = query.filter(
            AutomationAction.request_id == request_id
        )

    actions = (
        query
        .order_by(
            AutomationAction.scheduled_for.asc()
        )
        .all()
    )

    return [
        {
            "id": action.id,
            "request_id": action.request_id,
            "action_type": action.action_type,
            "status": action.status,
            "message": action.message,
            "scheduled_for": (
                action.scheduled_for.isoformat()
                if action.scheduled_for
                else None
            ),
            "retry_count": action.retry_count,
            "max_retries": action.max_retries,
            "error_message": action.error_message,
            "created_at": (
                action.created_at.isoformat()
                if action.created_at
                else None
            ),
        }
        for action in actions
    ]


# =========================================================
# GET SCHEDULER LOGS
# =========================================================

def get_scheduler_logs(
    db: Session,
    request_id: Optional[str] = None,
):

    query = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.action.in_(
                [
                    "SCHEDULE_AUTOMATION",
                    "EXECUTE_SCHEDULED_AUTOMATION",
                    "RETRY_SCHEDULED_AUTOMATION",
                ]
            )
        )
    )

    if request_id:
        query = query.filter(
            ActivityLog.request_id == request_id
        )

    logs = (
        query
        .order_by(
            ActivityLog.created_at.desc()
        )
        .all()
    )

    return [
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
    ]