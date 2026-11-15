from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.student_import import StudentImportResponse
from app.services.student_import_service import import_students


MAX_UPLOAD_SIZE = 10 * 1024 * 1024

router = APIRouter(
    prefix="/student-imports",
    tags=["Student Imports"],
)


@router.post(
    "",
    response_model=StudentImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_student_import(
    file: UploadFile = File(...),
    class_id: UUID = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("student.create")),
):
    content = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Student file exceeds the 10 MB limit",
        )
    return import_students(
        db=db,
        file_name=file.filename or "",
        content=content,
        class_id=class_id,
        uploaded_by=current_user,
    )
