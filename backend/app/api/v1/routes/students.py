from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.student_schema import (
    StudentCreate,
    StudentResponse,
)
from app.services.student_service import (
    create_student,
    get_student,
    get_students,
)


router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_student_endpoint(
    data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student.create")),
):
    return create_student(db, data, current_user)


@router.get(
    "",
    response_model=list[StudentResponse],
)
def get_students_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student.read")),
):
    return get_students(db, current_user)


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
)
def get_student_endpoint(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student.read")),
):
    return get_student(db, student_id, current_user)