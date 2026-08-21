from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.report_service import (
    generate_daily_automation_report,
    generate_weekly_operations_report,
    generate_ai_performance_report,
)

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
)


@router.get("/daily")
def daily_report(
    db: Session = Depends(get_db),
):
    return generate_daily_automation_report(db)


@router.get("/weekly")
def weekly_report(
    db: Session = Depends(get_db),
):
    return generate_weekly_operations_report(db)


@router.get("/ai-performance")
def ai_performance_report(
    db: Session = Depends(get_db),
):
    return generate_ai_performance_report(db)