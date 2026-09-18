from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceResponse,
)
from app.services.attendance_service import create_attendance


router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"],
)


@router.post(
    "",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance_endpoint(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("attendance.create")),
):
    return create_attendance(db, data, current_user)