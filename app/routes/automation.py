from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict

from ..services.automation_service import (
    determine_automation_action,
    get_workflows,
    get_workflow,
    execute_workflow,
)


router = APIRouter(
    prefix="/api/automation",
    tags=["Automation Orchestrator"],
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class AutomationRequest(BaseModel):
    priority: str = "MEDIUM"
    recommended_action: str = ""
    requires_human_approval: bool = False


class WorkflowRequest(BaseModel):
    workflow_name: str
    input_data: Dict[str, Any] = Field(
        default_factory=dict
    )


# =========================================================
# HEALTH
# =========================================================

@router.get("/health")
def automation_health():
    return {
        "success": True,
        "module": "Automation Orchestrator",
        "status": "operational",
    }


# =========================================================
# AUTOMATION EXECUTION
# =========================================================

@router.post("/execute")
def execute_automation(
    request: AutomationRequest,
):
    try:
        result = determine_automation_action(
            priority=request.priority,
            recommended_action=request.recommended_action,
            requires_human_approval=(
                request.requires_human_approval
            ),
        )

        return {
            "success": True,
            "input": {
                "priority": request.priority,
                "recommended_action": (
                    request.recommended_action
                ),
                "requires_human_approval": (
                    request.requires_human_approval
                ),
            },
            "automation": result,
        }

    except Exception as exc:
        print(
            f"Automation error: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Automation execution failed.",
        )


# =========================================================
# LIST WORKFLOWS
# =========================================================

@router.get("/workflows")
def list_workflows():
    try:
        return get_workflows()

    except Exception as exc:
        print(
            f"Workflow listing error: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve workflows.",
        )


# =========================================================
# GET WORKFLOW
# =========================================================

@router.get("/workflows/{workflow_name}")
def workflow_details(
    workflow_name: str,
):
    try:
        result = get_workflow(
            workflow_name
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=result.get(
                    "message",
                    "Workflow not found.",
                ),
            )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        print(
            f"Workflow details error: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve workflow.",
        )


# =========================================================
# EXECUTE WORKFLOW
# =========================================================

@router.post("/workflows/execute")
def run_workflow(
    request: WorkflowRequest,
):
    try:
        result = execute_workflow(
            workflow_name=request.workflow_name,
            input_data=request.input_data,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=result.get(
                    "message",
                    "Workflow execution failed.",
                ),
            )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        print(
            f"Workflow execution error: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Workflow execution failed.",
        )