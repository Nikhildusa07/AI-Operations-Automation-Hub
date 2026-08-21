from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models import Request, ActivityLog, AutomationAction


def _date_value(value):
    if value is None:
        return None

    if hasattr(value, "date"):
        return value.date()

    try:
        return datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        return None


def _success_rate(successes, total):
    if not total:
        return 0.0

    return round((successes / total) * 100, 2)


def generate_daily_automation_report(
    db: Session,
    report_date=None,
):
    """
    Generate a daily automation report.

    Includes:
    - Executions
    - Success rate
    - Failures
    - AI usage
    """

    if report_date is None:
        report_date = datetime.now().date()

    requests = db.query(Request).all()
    activities = db.query(ActivityLog).all()

    day_requests = [
        item
        for item in requests
        if _date_value(item.created_at) == report_date
    ]

    day_activities = [
        item
        for item in activities
        if _date_value(item.created_at) == report_date
    ]

    executions = len(day_activities)

    successful = sum(
        1
        for item in day_activities
        if str(item.status or "").upper() == "SUCCESS"
    )

    failures = sum(
        1
        for item in day_activities
        if str(item.status or "").upper() == "FAILED"
    )

    ai_usage = sum(
        1
        for item in day_activities
        if str(item.action or "").upper()
        in {
            "AI_ANALYSIS",
            "AGENT_REASONING",
            "AGENT_TOOL_SELECTED",
            "AGENT_DATA_RETRIEVED",
            "DECISION_MADE",
        }
    )

    return {
        "report": "Daily Automation Report",
        "date": str(report_date),
        "executions": executions,
        "successful_executions": successful,
        "failed_executions": failures,
        "success_rate": _success_rate(
            successful,
            executions,
        ),
        "ai_usage": ai_usage,
        "requests_received": len(day_requests),
    }


def generate_weekly_operations_report(
    db: Session,
    end_date=None,
):
    """
    Generate a weekly operations report.

    Includes:
    - Major activities
    - Issues
    - Trends
    - Recommendations
    """

    if end_date is None:
        end_date = datetime.now().date()

    start_date = end_date - timedelta(days=6)

    requests = db.query(Request).all()
    activities = db.query(ActivityLog).all()

    week_requests = [
        item
        for item in requests
        if (
            _date_value(item.created_at)
            and start_date
            <= _date_value(item.created_at)
            <= end_date
        )
    ]

    week_activities = [
        item
        for item in activities
        if (
            _date_value(item.created_at)
            and start_date
            <= _date_value(item.created_at)
            <= end_date
        )
    ]

    total_requests = len(week_requests)

    completed = sum(
        1
        for item in week_requests
        if str(item.status or "").lower()
        in {
            "completed",
            "processed",
            "approved",
        }
    )

    pending = sum(
        1
        for item in week_requests
        if str(item.status or "").lower()
        in {
            "pending",
            "pending_review",
            "review",
            "processing",
        }
    )

    failed = sum(
        1
        for item in week_requests
        if str(item.status or "").lower()
        in {
            "failed",
            "error",
        }
    )

    activity_counts = {}

    for activity in week_activities:
        action = str(
            activity.action or "UNKNOWN"
        )

        activity_counts[action] = (
            activity_counts.get(action, 0) + 1
        )

    major_activities = sorted(
        activity_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:10]

    issues = [
        {
            "action": activity.action,
            "status": activity.status,
            "message": activity.message,
            "date": str(
                _date_value(activity.created_at)
            ),
        }
        for activity in week_activities
        if str(activity.status or "").upper()
        in {
            "FAILED",
            "BLOCKED",
        }
    ]

    recommendations = []

    if failed:
        recommendations.append(
            "Review failed requests and "
            "automation incidents."
        )

    if pending:
        recommendations.append(
            "Review pending requests and "
            "human approval items."
        )

    if not failed:
        recommendations.append(
            "Automation reliability was stable "
            "during the reporting period."
        )

    if not recommendations:
        recommendations.append(
            "Continue monitoring workflow performance."
        )

    return {
        "report": "Weekly Operations Report",
        "period": {
            "start": str(start_date),
            "end": str(end_date),
        },
        "summary": {
            "total_requests": total_requests,
            "completed_requests": completed,
            "pending_requests": pending,
            "failed_requests": failed,
        },
        "major_activities": [
            {
                "action": action,
                "count": count,
            }
            for action, count in major_activities
        ],
        "issues": issues[:20],
        "trends": {
            "completion_rate": _success_rate(
                completed,
                total_requests,
            ),
            "failure_rate": _success_rate(
                failed,
                total_requests,
            ),
        },
        "recommendations": recommendations,
    }


def generate_ai_performance_report(
    db: Session,
    start_date=None,
    end_date=None,
):
    """
    Generate an AI performance report.

    Includes:
    - Requests
    - Accuracy indicator
    - Failed responses
    - Average response time indicator
    """

    if end_date is None:
        end_date = datetime.now().date()

    if start_date is None:
        start_date = end_date - timedelta(days=6)

    requests = db.query(Request).all()
    activities = db.query(ActivityLog).all()

    period_requests = [
        item
        for item in requests
        if (
            _date_value(item.created_at)
            and start_date
            <= _date_value(item.created_at)
            <= end_date
        )
    ]

    period_activities = [
        item
        for item in activities
        if (
            _date_value(item.created_at)
            and start_date
            <= _date_value(item.created_at)
            <= end_date
        )
    ]

    ai_activities = [
        item
        for item in period_activities
        if str(item.action or "").upper()
        == "AI_ANALYSIS"
    ]

    failed_ai = [
        item
        for item in ai_activities
        if str(item.status or "").upper()
        in {
            "FAILED",
            "ERROR",
        }
    ]

    successful_ai = [
        item
        for item in ai_activities
        if str(item.status or "").upper()
        in {
            "SUCCESS",
            "FALLBACK",
        }
    ]

    confidence_values = [
        float(item.confidence_score)
        for item in period_requests
        if item.confidence_score is not None
    ]

    average_confidence = (
        round(
            sum(confidence_values)
            / len(confidence_values),
            3,
        )
        if confidence_values
        else 0.0
    )

    return {
        "report": "AI Performance Report",
        "period": {
            "start": str(start_date),
            "end": str(end_date),
        },
        "requests": len(period_requests),
        "ai_analysis_requests": len(ai_activities),
        "successful_ai_responses": len(successful_ai),
        "failed_ai_responses": len(failed_ai),
        "accuracy_indicator": (
            _success_rate(
                len(successful_ai),
                len(ai_activities),
            )
        ),
        "average_confidence": average_confidence,
        "average_response_time": (
            "Not available: execution-time "
            "timestamps are not stored."
        ),
        "note": (
            "Accuracy is represented using successful "
            "AI-analysis completion as an operational "
            "indicator. Ground-truth accuracy requires "
            "the separate 20-case evaluation dataset."
        ),
    }