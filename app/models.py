from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
)

from .database import Base


# =========================================================
# BUSINESS REQUEST
# =========================================================

class Request(Base):
    __tablename__ = "requests"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    request_id = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    customer_name = Column(
        String(100),
        nullable=False,
    )

    customer_email = Column(
        String(150),
        nullable=False,
    )

    input_text = Column(
        Text,
        nullable=False,
    )

    intent = Column(
        String(100),
        nullable=True,
    )

    priority = Column(
        String(20),
        nullable=True,
    )

    confidence_score = Column(
        Float,
        nullable=True,
    )

    ai_summary = Column(
        Text,
        nullable=True,
    )

    status = Column(
        String(50),
        default="received",
        nullable=False,
    )

    action_taken = Column(
        Text,
        nullable=True,
    )

    error_message = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


# =========================================================
# ACTIVITY / AUDIT LOG
# =========================================================

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    request_id = Column(
        String(50),
        nullable=False,
        index=True,
    )

    action = Column(
        String(100),
        nullable=False,
    )

    status = Column(
        String(30),
        nullable=False,
    )

    message = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


# =========================================================
# HUMAN REVIEW QUEUE
# =========================================================

class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    request_id = Column(
        String(50),
        nullable=False,
        index=True,
    )

    reason = Column(
        Text,
        nullable=False,
    )

    status = Column(
        String(30),
        default="pending",
        nullable=False,
    )

    reviewer_note = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    reviewed_at = Column(
        DateTime,
        nullable=True,
    )


# =========================================================
# AUTOMATION / SCHEDULER ACTION
# =========================================================

class AutomationAction(Base):
    __tablename__ = "automation_actions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    request_id = Column(
        String(50),
        nullable=False,
        index=True,
    )

    action_type = Column(
        String(100),
        nullable=False,
    )

    # scheduled / running / completed / failed / cancelled
    status = Column(
        String(30),
        default="scheduled",
        nullable=False,
        index=True,
    )

    message = Column(
        Text,
        nullable=True,
    )

    # Time when automation should execute
    scheduled_for = Column(
        DateTime,
        nullable=True,
        index=True,
    )

    # Time when execution started
    started_at = Column(
        DateTime,
        nullable=True,
    )

    # Time when execution completed
    completed_at = Column(
        DateTime,
        nullable=True,
    )

    # Last execution error
    error_message = Column(
        Text,
        nullable=True,
    )

    # Number of execution attempts
    retry_count = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # Maximum number of retries allowed
    max_retries = Column(
        Integer,
        default=3,
        nullable=False,
    )

    # Last retry timestamp
    last_retry_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


# =========================================================
# TASK
# =========================================================

class Task(Base):
    __tablename__ = "tasks"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(
        String(200),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=False,
    )

    category = Column(
        String(100),
        nullable=True,
    )

    priority = Column(
        String(20),
        default="MEDIUM",
        nullable=False,
    )

    status = Column(
        String(30),
        default="PENDING",
        nullable=False,
    )

    assignee = Column(
        String(200),
        nullable=True,
    )

    due_date = Column(
        String(50),
        nullable=True,
    )

    next_action = Column(
        Text,
        nullable=True,
    )

    dependencies = Column(
        Text,
        nullable=True,
    )

    estimated_effort = Column(
        String(100),
        nullable=True,
    )

    confidence_score = Column(
        Float,
        nullable=True,
    )

    analysis_source = Column(
        String(50),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

# =========================================================
# AI USAGE / COST CONTROL
# =========================================================

class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    request_id = Column(
        String(50),
        nullable=True,
        index=True
    )

    provider = Column(
        String(50),
        nullable=False
    )

    model = Column(
        String(100),
        nullable=False
    )

    input_tokens = Column(
        Integer,
        default=0,
        nullable=False
    )

    output_tokens = Column(
        Integer,
        default=0,
        nullable=False
    )

    total_tokens = Column(
        Integer,
        default=0,
        nullable=False
    )

    estimated_cost = Column(
        Float,
        default=0.0,
        nullable=False
    )

    purpose = Column(
        String(100),
        nullable=True
    )

    status = Column(
        String(30),
        default="SUCCESS",
        nullable=False
    )

    error_message = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )