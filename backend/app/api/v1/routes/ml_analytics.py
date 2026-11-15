from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.services.ml_service import get_student_ml_insights

router = APIRouter(prefix="/ml", tags=["Machine Learning & Risk Analytics"])


@router.get("/risk-analysis")
def get_risk_analysis(
    class_id: UUID | None = None,
    risk_tier: str | None = Query(None, description="CRITICAL, ELEVATED, NORMAL, or ALL"),
    search: str | None = Query(None, description="Search by student name or roll number"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve predictive attendance risk scoring, anomaly detection, and AI recommendations."""
    return get_student_ml_insights(
        db=db,
        current_user=current_user,
        class_id=class_id,
        risk_tier=risk_tier,
        search_query=search,
    )
