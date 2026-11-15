from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.attendance_import import AttendanceImportResponse
from app.services.attendance_import_service import (
    MAX_UPLOAD_SIZE,
    process_attendance_upload,
)


router = APIRouter(
    prefix="/attendance-imports",
    tags=["Attendance Imports"],
)


@router.post(
    "",
    response_model=AttendanceImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_attendance_import(
    file: UploadFile = File(...),
    attendance_date: date = Form(...),
    class_id: UUID | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("attendance.import")
    ),
):
    file_content = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Attendance file exceeds the 10 MB limit",
        )
    return process_attendance_upload(
        db=db,
        file_name=file.filename or "",
        file_content=file_content,
        attendance_date=attendance_date,
        class_id=class_id,
        uploaded_by=current_user,
    )