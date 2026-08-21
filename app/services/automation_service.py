from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..models import ActivityLog, AutomationAction


# =========================================================
# CONSTANTS
# =========================================================

HIGH_PRIORITIES = {
    "HIGH",
    "CRITICAL",
}

SUPPORTED_SCHEDULED_ACTIONS = {
    "PROCESS_PENDING_INVOICES",
    "SEND_NOTIFICATION",
    "SEND_EMAIL",
    "CREATE_TASK",
    "AUTOMATED_RESPONSE",
    "AUTO_EXECUTE",
}


# =========================================================
# WORKFLOW DEFINITIONS
# =========================================================

WORKFLOWS = {
    "CUSTOMER_SUPPORT": {
        "name": "Customer Support Automation",
        "trigger": "Customer support request",
        "ai_processing": "Classify intent, sentiment and priority",
        "condition": "Check priority and risk",
        "action": "Auto reply or human escalation",
        "notification": (
            "Notify support team when escalation is required"
        ),
        "record": "Store request and activity log",
    },

    "INVOICE_PROCESSING": {
        "name": "Invoice Processing",
        "trigger": "Invoice/document uploaded",
        "ai_processing": "Extract invoice information",
        "condition": "Check invoice amount and status",
        "action": "Process automatically or request approval",
        "notification": "Notify finance team",
        "record": "Store invoice processing activity",
    },

    "SECURITY_ESCALATION": {
        "name": "Security Incident Escalation",
        "trigger": "Security-related customer request",
        "ai_processing": "Identify security risk and severity",
        "condition": "Check for CRITICAL security risk",
        "action": "Escalate to human/security team",
        "notification": "Send urgent security notification",
        "record": "Create audit/activity record",
    },

    "MEETING_FOLLOWUP": {
        "name": "Meeting Follow-up Automation",
        "trigger": "Meeting transcript submitted",
        "ai_processing": "Extract decisions and action items",
        "condition": "Check whether action items exist",
        "action": "Create tasks for identified action items",
        "notification": "Notify assigned team members",
        "record": "Store meeting processing activity",
    },

    "SCHEDULED_OPERATIONS": {
        "name": "Scheduled Business Operations",
        "trigger": "Scheduled automation event",
        "ai_processing": "Analyze pending business operations",
        "condition": "Check whether pending work exists",
        "action": "Execute approved automation",
        "notification": "Notify relevant business team",
        "record": "Store scheduler and execution logs",
    },
}


# =========================================================
# NORMALIZATION
# =========================================================

def _normalize(
    value: Any,
    default: str = "",
) -> str:

    if value is None:
        return default

    return str(value).strip().upper()


# =========================================================
# DETERMINE AUTOMATION ACTION
# =========================================================

def determine_automation_action(
    priority: str,
    recommended_action: str = "",
    requires_human_approval: bool = False,
) -> Dict[str, Any]:

    priority = _normalize(
        priority,
        "MEDIUM",
    )

    recommended_action = _normalize(
        recommended_action
    )

    # HIGH / CRITICAL
    if (
        priority in HIGH_PRIORITIES
        or requires_human_approval
    ):
        return {
            "automation_status": "ESCALATED",
            "status": "PENDING",
            "action": "HUMAN_REVIEW",
            "action_type": "HUMAN_REVIEW",
            "decision": "ESCALATE",
            "reason": (
                "The request requires human review "
                "because of its priority or risk."
            ),
            "requires_human_approval": True,
            "message": (
                "Request requires human review "
                "before execution."
            ),
        }

    # MEDIUM
    if priority == "MEDIUM":
        return {
            "automation_status": "PENDING_REVIEW",
            "status": "PENDING",
            "action": "REVIEW",
            "action_type": "REVIEW",
            "decision": "REVIEW",
            "reason": (
                "The request has medium priority "
                "and should be reviewed before execution."
            ),
            "requires_human_approval": True,
            "message": (
                "Request is waiting for review "
                "before execution."
            ),
        }

    # LOW
    if priority == "LOW":
        return {
            "automation_status": "AUTOMATED",
            "status": "SUCCESS",
            "action": "AUTO_EXECUTE",
            "action_type": "AUTO_EXECUTE",
            "decision": "AUTOMATE",
            "reason": (
                "The request is low risk and can "
                "be processed automatically."
            ),
            "requires_human_approval": False,
            "message": (
                "Automation executed successfully "
                "for this low-risk request."
            ),
        }

    # UNKNOWN
    return {
        "automation_status": "PENDING_REVIEW",
        "status": "PENDING",
        "action": "REVIEW",
        "action_type": "REVIEW",
        "decision": "REVIEW",
        "reason": (
            "Priority could not be safely classified."
        ),
        "requires_human_approval": True,
        "message": (
            "Request requires review because "
            "priority could not be safely classified."
        ),
    }


# =========================================================
# GET ALL WORKFLOWS
# =========================================================

def get_workflows() -> Dict[str, Any]:

    return {
        "success": True,
        "count": len(WORKFLOWS),
        "workflows": WORKFLOWS,
    }


# =========================================================
# GET SINGLE WORKFLOW
# =========================================================

def get_workflow(
    workflow_name: str,
) -> Dict[str, Any]:

    workflow_key = _normalize(
        workflow_name
    )

    workflow = WORKFLOWS.get(
        workflow_key
    )

    if not workflow:
        return {
            "success": False,
            "message": "Workflow not found.",
            "workflow": workflow_name,
        }

    return {
        "success": True,
        "workflow_name": workflow_key,
        "workflow": workflow,
    }


# =========================================================
# CREATE AUTOMATION ACTION RECORD
# =========================================================

def _create_automation_record(
    db: Session,
    request_id: str,
    action_type: str,
    status: str,
    message: str,
) -> Optional[AutomationAction]:

    if not request_id:
        return None

    # Never create an automation execution record
    # for human-review actions.
    if action_type in {
        "HUMAN_REVIEW",
        "REVIEW",
    }:
        return None

    action = AutomationAction(
        request_id=request_id,
        action_type=action_type,
        status=(
            "completed"
            if status in {
                "SUCCESS",
                "COMPLETED",
            }
            else "scheduled"
        ),
        message=message,
        retry_count=0,
        max_retries=3,
    )

    if action.status == "completed":
        action.started_at = datetime.utcnow()
        action.completed_at = datetime.utcnow()

    db.add(action)
    db.flush()

    return action


# =========================================================
# EXECUTE ACTION
# =========================================================

def execute_action(
    request,
    db: Optional[Session] = None,
) -> Dict[str, Any]:

    priority = getattr(
        request,
        "priority",
        "MEDIUM",
    )

    action_taken = getattr(
        request,
        "action_taken",
        "",
    )

    request_id = getattr(
        request,
        "request_id",
        None,
    )

    requires_human = (
        _normalize(
            priority,
            "MEDIUM",
        )
        in HIGH_PRIORITIES
    )

    decision = determine_automation_action(
        priority=priority,
        recommended_action=action_taken,
        requires_human_approval=requires_human,
    )

    action = decision["action"]
    status = decision["status"]
    message = decision["message"]

    # -----------------------------------------------------
    # HUMAN REVIEW
    # -----------------------------------------------------

    if action in {
        "HUMAN_REVIEW",
        "REVIEW",
    }:

        return {
            **decision,
            "success": True,
        }

    # -----------------------------------------------------
    # AUTOMATIC EXECUTION
    # -----------------------------------------------------

    if action == "AUTO_EXECUTE":

        automation_record = None

        if db is not None:

            automation_record = (
                _create_automation_record(
                    db=db,
                    request_id=request_id,
                    action_type="AUTO_EXECUTE",
                    status=status,
                    message=message,
                )
            )

            db.add(
                ActivityLog(
                    request_id=request_id,
                    action="ACTION_EXECUTED",
                    status="SUCCESS",
                    message=(
                        "Automatic action "
                        "AUTO_EXECUTE completed successfully."
                    ),
                )
            )

            db.flush()

        return {
            **decision,
            "success": True,
            "status": "SUCCESS",
            "automation_status": "AUTOMATED",
            "action": "AUTO_EXECUTE",
            "action_type": "AUTO_EXECUTE",
            "message": (
                "Automation executed successfully "
                "for this low-risk request."
            ),
            "automation_record_id": (
                automation_record.id
                if automation_record
                else None
            ),
        }

    # SAFE FALLBACK
    return {
        "success": True,
        "automation_status": "PENDING_REVIEW",
        "status": "PENDING",
        "action": "HUMAN_REVIEW",
        "action_type": "HUMAN_REVIEW",
        "decision": "ESCALATE",
        "reason": (
            "Automation could not be safely classified."
        ),
        "message": (
            "Request was routed to human review."
        ),
        "requires_human_approval": True,
    }


# =========================================================
# EXTRACT MEETING ACTION ITEMS
# =========================================================

def _extract_meeting_action_items(
    transcript: str,
) -> list:

    if not transcript or not transcript.strip():
        return []

    text = transcript.strip()

    action_items = []

    sentences = [
        sentence.strip()
        for sentence in (
            text
            .replace("!", ".")
            .replace("?", ".")
            .split(".")
        )
        if sentence.strip()
    ]

    for sentence in sentences:

        lower = sentence.lower()

        if (
            " will " in f" {lower} "
            or " should " in f" {lower} "
            or " needs to " in f" {lower} "
            or " must " in f" {lower} "
            or " responsible for " in f" {lower} "
        ):
            action_items.append(sentence)

    return action_items


# =========================================================
# EXECUTE WORKFLOW
# =========================================================

def execute_workflow(
    workflow_name: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(input_data, dict):
        return {
            "success": False,
            "message": "input_data must be a dictionary.",
            "workflow": workflow_name,
        }

    workflow_key = _normalize(
        workflow_name
    )

    if workflow_key not in WORKFLOWS:
        return {
            "success": False,
            "message": "Workflow not found.",
            "workflow": workflow_name,
        }

    workflow = WORKFLOWS[workflow_key]

    priority = _normalize(
        input_data.get(
            "priority",
            "MEDIUM",
        ),
        "MEDIUM",
    )

    requires_human = bool(
        input_data.get(
            "requires_human_approval",
            False,
        )
    )

    # =====================================================
    # CUSTOMER SUPPORT
    # =====================================================

    if workflow_key == "CUSTOMER_SUPPORT":

        decision = determine_automation_action(
            priority=priority,
            recommended_action=input_data.get(
                "recommended_action",
                "",
            ),
            requires_human_approval=requires_human,
        )

        return {
            "success": True,
            "workflow_name": workflow_key,
            "workflow": workflow,
            "decision": decision,
            "input": input_data,
        }

    # =====================================================
    # INVOICE PROCESSING
    # =====================================================

    if workflow_key == "INVOICE_PROCESSING":

        try:
            amount = float(
                input_data.get(
                    "amount",
                    0,
                )
            )

        except (TypeError, ValueError):

            return {
                "success": False,
                "message": (
                    "Invoice amount must be "
                    "a valid number."
                ),
                "workflow": workflow_name,
                "input": input_data,
            }

        if amount >= 100000:

            decision = {
                "automation_status": "PENDING_REVIEW",
                "status": "PENDING",
                "action": "FINANCE_REVIEW",
                "action_type": "FINANCE_REVIEW",
                "decision": "ESCALATE",
                "reason": (
                    "Invoice amount requires "
                    "finance review."
                ),
                "requires_human_approval": True,
                "message": (
                    "Invoice requires finance "
                    "approval before processing."
                ),
            }

        else:

            decision = {
                "automation_status": "AUTOMATED",
                "status": "SUCCESS",
                "action": "AUTO_PROCESS",
                "action_type": "AUTO_PROCESS",
                "decision": "AUTOMATE",
                "reason": (
                    "Invoice can be processed "
                    "automatically."
                ),
                "requires_human_approval": False,
                "message": (
                    "Invoice processed automatically."
                ),
            }

        return {
            "success": True,
            "workflow_name": workflow_key,
            "workflow": workflow,
            "decision": decision,
            "input": input_data,
        }

    # =====================================================
    # SECURITY ESCALATION
    # =====================================================

    if workflow_key == "SECURITY_ESCALATION":

        decision = {
            "automation_status": "ESCALATED",
            "status": "PENDING",
            "action": "SECURITY_HUMAN_REVIEW",
            "action_type": "SECURITY_HUMAN_REVIEW",
            "decision": "ESCALATE",
            "reason": (
                "Security workflow requires "
                "immediate human review."
            ),
            "requires_human_approval": True,
            "message": (
                "Security request routed "
                "to human review."
            ),
        }

        return {
            "success": True,
            "workflow_name": workflow_key,
            "workflow": workflow,
            "decision": decision,
            "input": input_data,
        }

    # =====================================================
    # MEETING FOLLOW-UP
    # =====================================================

    if workflow_key == "MEETING_FOLLOWUP":

        action_items = input_data.get(
            "action_items",
            [],
        )

        if not isinstance(
            action_items,
            list,
        ):
            action_items = []

        if not action_items:

            transcript = input_data.get(
                "transcript",
                "",
            )

            action_items = (
                _extract_meeting_action_items(
                    transcript
                )
            )

        if action_items:

            decision = {
                "automation_status": "AUTOMATED",
                "status": "SUCCESS",
                "action": "CREATE_TASKS",
                "action_type": "CREATE_TASKS",
                "decision": "AUTOMATE",
                "reason": (
                    "Meeting action items detected."
                ),
                "requires_human_approval": False,
                "message": (
                    "Tasks can be created "
                    "for identified action items."
                ),
            }

        else:

            decision = {
                "automation_status": "NO_ACTION",
                "status": "SUCCESS",
                "action": "NO_ACTION",
                "action_type": "NO_ACTION",
                "decision": "NO_ACTION",
                "reason": (
                    "No meeting action items "
                    "were detected."
                ),
                "requires_human_approval": False,
                "message": (
                    "No action is required."
                ),
            }

        return {
            "success": True,
            "workflow_name": workflow_key,
            "workflow": workflow,
            "decision": decision,
            "action_items": action_items,
            "input": input_data,
        }

    # =====================================================
    # SCHEDULED OPERATIONS
    # =====================================================

    if workflow_key == "SCHEDULED_OPERATIONS":

        pending_work = bool(
            input_data.get(
                "pending_work",
                False,
            )
        )

        operation = str(
            input_data.get(
                "operation",
                "",
            )
        ).strip()

        action_type = _normalize(
            input_data.get(
                "action_type",
                "",
            )
        )

        if pending_work and operation:

            action = (
                action_type
                if action_type
                else "EXECUTE_OPERATION"
            )

            decision = {
                "automation_status": "AUTOMATED",
                "status": "SUCCESS",
                "action": action,
                "action_type": action,
                "decision": "AUTOMATE",
                "reason": (
                    "Pending scheduled operation "
                    "detected and approved for execution."
                ),
                "requires_human_approval": False,
                "message": (
                    "Scheduled operation "
                    "executed successfully."
                ),
            }

        elif action_type:

            decision = {
                "automation_status": "AUTOMATED",
                "status": "SUCCESS",
                "action": action_type,
                "action_type": action_type,
                "decision": "AUTOMATE",
                "reason": (
                    "Scheduled business operation "
                    "is being executed."
                ),
                "requires_human_approval": False,
                "message": (
                    "Scheduled operation "
                    "executed successfully."
                ),
            }

        else:

            decision = {
                "automation_status": "NO_ACTION",
                "status": "SUCCESS",
                "action": "NO_ACTION",
                "action_type": "NO_ACTION",
                "decision": "NO_ACTION",
                "reason": (
                    "No scheduled operation "
                    "was provided."
                ),
                "requires_human_approval": False,
                "message": (
                    "No scheduled operation "
                    "requires execution."
                ),
            }

        return {
            "success": True,
            "workflow_name": workflow_key,
            "workflow": workflow,
            "decision": decision,
            "input": input_data,
        }

    # =====================================================
    # UNSUPPORTED
    # =====================================================

    return {
        "success": False,
        "message": (
            "Workflow execution is not supported."
        ),
        "workflow": workflow_name,
        "input": input_data,
    }


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
        raise ValueError(
            "request_id is required."
        )

    if not action_type:
        raise ValueError(
            "action_type is required."
        )

    if not scheduled_for:
        raise ValueError(
            "scheduled_for is required."
        )

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
        "message": (
            "Automation scheduled successfully."
        ),
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
            "message": (
                "Scheduled automation not found."
            ),
            "action_id": action_id,
        }

    if action.status == "completed":
        return {
            "success": False,
            "message": (
                "Automation has already been completed."
            ),
            "action_id": action.id,
        }

    if action.status == "running":
        return {
            "success": False,
            "message": (
                "Automation is already running."
            ),
            "action_id": action.id,
        }

    try:

        action.status = "running"
        action.started_at = datetime.utcnow()

        db.commit()

        if (
            action.action_type
            not in SUPPORTED_SCHEDULED_ACTIONS
        ):
            raise ValueError(
                "Unsupported automation action: "
                f"{action.action_type}"
            )

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
            "message": (
                "Scheduled automation failed."
            ),
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
            "message": (
                "Scheduled automation not found."
            ),
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

    result = execute_scheduled_task(
        db=db,
        action_id=action.id,
    )

    return {
        "success": result.get(
            "success",
            False,
        ),
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