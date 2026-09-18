from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.student_parent import (
    StudentParentCreate,
    StudentParentResponse,
)
from app.services.student_parent_service import create_student_parent


router = APIRouter(
    prefix="/student-parents",
    tags=["Student Parents"],
)


@router.post(
    "",
    response_model=StudentParentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_student_parent_endpoint(
    data: StudentParentCreate,
    db: Session = Depends(get_db),
):
    return create_student_parent(db, data)