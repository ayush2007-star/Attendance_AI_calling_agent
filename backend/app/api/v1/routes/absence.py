from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.absence import (
    AbsenceCreate,
    AbsenceResponse,
)
from app.services.absence_service import create_absence


router = APIRouter(
    prefix="/absence-events",
    tags=["Absence Events"],
)


@router.post(
    "",
    response_model=AbsenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_absence_endpoint(
    data: AbsenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    return create_absence(db, data, current_user)