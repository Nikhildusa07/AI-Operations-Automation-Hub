from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from ..database import get_db

from ..services.scheduler_service import (
    create_scheduled_task,
    execute_scheduled_task,
    retry_scheduled_task,
    get_scheduled_tasks,
    get_scheduler_logs,
)


router = APIRouter(
    prefix="/api/scheduler",
    tags=["Automation Scheduler"],
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class ScheduleRequest(BaseModel):
    request_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    action_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    scheduled_for: datetime

    message: str = Field(
        default="",
        max_length=5000,
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@router.get("/health")
def scheduler_health():

    return {
        "success": True,
        "module": "Automation Scheduler",
        "status": "operational",
    }


# =========================================================
# CREATE SCHEDULE
# =========================================================

@router.post("/schedule")
def schedule_automation(
    request: ScheduleRequest,
    db: Session = Depends(get_db),
):

    return create_scheduled_task(
        db=db,
        request_id=request.request_id,
        action_type=request.action_type,
        scheduled_for=request.scheduled_for,
        message=request.message,
    )


# =========================================================
# GET SCHEDULED TASKS
# =========================================================

@router.get("/scheduled")
def scheduled_tasks(
    request_id: Optional[str] = None,
    db: Session = Depends(get_db),
):

    tasks = get_scheduled_tasks(
        db=db,
        request_id=request_id,
    )

    return {
        "success": True,
        "count": len(tasks),
        "tasks": tasks,
    }


# =========================================================
# EXECUTE SCHEDULED TASK
# =========================================================

@router.post("/execute/{action_id}")
def execute_scheduler_action(
    action_id: int,
    db: Session = Depends(get_db),
):

    return execute_scheduled_task(
        db=db,
        action_id=action_id,
    )


# =========================================================
# RETRY FAILED AUTOMATION
# =========================================================

@router.post("/retry/{action_id}")
def retry_scheduler_action(
    action_id: int,
    db: Session = Depends(get_db),
):

    return retry_scheduled_task(
        db=db,
        action_id=action_id,
    )


# =========================================================
# EXECUTION LOGS
# =========================================================

@router.get("/logs")
def scheduler_logs(
    request_id: Optional[str] = None,
    db: Session = Depends(get_db),
):

    logs = get_scheduler_logs(
        db=db,
        request_id=request_id,
    )

    return {
        "success": True,
        "count": len(logs),
        "logs": logs,
    }