from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task
from app.services.task_service import analyze_task


router = APIRouter(
    prefix="/api/tasks",
    tags=["AI Task Management"],
)


# =========================================================
# SCHEMAS
# =========================================================

class TaskCreateRequest(BaseModel):
    task: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )

    context: Optional[str] = Field(
        default="",
        max_length=5000,
    )

    assignee: Optional[str] = Field(
        default=None,
        max_length=200,
    )


class TaskStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        min_length=1,
        max_length=30,
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@router.get("/health")
def task_health():
    return {
        "success": True,
        "module": "AI Task Management",
        "status": "operational",
    }


# =========================================================
# CREATE + SAVE AI TASK
# =========================================================

@router.post("/analyze")
def create_ai_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        result = analyze_task(
            task=request.task,
            context=request.context or "",
            assignee=request.assignee,
        )

        dependencies = result.get(
            "dependencies",
            [],
        )

        task_record = Task(
            title=result.get("title"),
            description=result.get("description"),
            category=result.get("category"),
            priority=result.get("priority"),
            status=result.get(
                "status",
                "PENDING",
            ),
            assignee=result.get("assignee"),
            due_date=result.get("due_date"),
            next_action=result.get("next_action"),
            dependencies=", ".join(
                str(item)
                for item in dependencies
            ),
            estimated_effort=result.get(
                "estimated_effort"
            ),
            confidence_score=result.get(
                "confidence_score"
            ),
            analysis_source=result.get(
                "analysis_source"
            ),
        )

        db.add(task_record)
        db.commit()
        db.refresh(task_record)

        return {
            "success": True,
            "message": "AI task created successfully.",
            "task": {
                "id": task_record.id,
                "title": task_record.title,
                "description": task_record.description,
                "category": task_record.category,
                "priority": task_record.priority,
                "status": task_record.status,
                "assignee": task_record.assignee,
                "due_date": task_record.due_date,
                "next_action": task_record.next_action,
                "dependencies": dependencies,
                "estimated_effort": (
                    task_record.estimated_effort
                ),
                "confidence_score": (
                    task_record.confidence_score
                ),
                "analysis_source": (
                    task_record.analysis_source
                ),
            },
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        print(
            f"TASK CREATE ERROR: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to create task.",
        )


# =========================================================
# LIST TASKS
# =========================================================

@router.get("/")
def list_tasks(
    db: Session = Depends(get_db),
):
    tasks = (
        db.query(Task)
        .order_by(Task.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "count": len(tasks),
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "category": task.category,
                "priority": task.priority,
                "status": task.status,
                "assignee": task.assignee,
                "due_date": task.due_date,
                "next_action": task.next_action,
                "dependencies": (
                    [
                        item.strip()
                        for item in task.dependencies.split(",")
                        if item.strip()
                    ]
                    if task.dependencies
                    else []
                ),
                "estimated_effort": (
                    task.estimated_effort
                ),
                "confidence_score": (
                    task.confidence_score
                ),
                "analysis_source": (
                    task.analysis_source
                ),
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
            for task in tasks
        ],
    }


# =========================================================
# GET SINGLE TASK
# =========================================================

@router.get("/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    return {
        "success": True,
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "category": task.category,
            "priority": task.priority,
            "status": task.status,
            "assignee": task.assignee,
            "due_date": task.due_date,
            "next_action": task.next_action,
            "dependencies": (
                [
                    item.strip()
                    for item in task.dependencies.split(",")
                    if item.strip()
                ]
                if task.dependencies
                else []
            ),
            "estimated_effort": (
                task.estimated_effort
            ),
            "confidence_score": (
                task.confidence_score
            ),
            "analysis_source": (
                task.analysis_source
            ),
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        },
    }


# =========================================================
# UPDATE TASK STATUS
# =========================================================

@router.patch("/{task_id}/status")
def update_task_status(
    task_id: int,
    request: TaskStatusUpdate,
    db: Session = Depends(get_db),
):
    allowed_statuses = {
        "PENDING",
        "IN_PROGRESS",
        "COMPLETED",
        "BLOCKED",
    }

    new_status = request.status.strip().upper()

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid status. Allowed values: "
                "PENDING, IN_PROGRESS, COMPLETED, BLOCKED."
            ),
        )

    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    task.status = new_status

    db.commit()
    db.refresh(task)

    return {
        "success": True,
        "message": "Task status updated successfully.",
        "task": {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "updated_at": task.updated_at,
        },
    }


# =========================================================
# DELETE TASK
# =========================================================

@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    db.delete(task)
    db.commit()

    return {
        "success": True,
        "message": "Task deleted successfully.",
        "task_id": task_id,
    }