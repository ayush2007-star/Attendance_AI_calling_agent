from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.parent import Parent
from app.models.student_parent import StudentParent
from app.models.user import User
from app.schemas.student_parent import StudentParentCreate
from app.services.student_service import get_student


def create_student_parent(
    db: Session,
    data: StudentParentCreate,
    current_user: User,
) -> StudentParent:
    student = get_student(db, data.student_id, current_user)
    parent = db.get(Parent, data.parent_id)
    if parent is None or not parent.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active parent contact not found",
        )

    existing_link = db.execute(
        select(StudentParent).where(
            StudentParent.student_id == student.id,
            StudentParent.parent_id == parent.id,
        )
    ).scalar_one_or_none()
    if existing_link is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This parent is already linked to the student",
        )

    if data.is_primary:
        existing_primary_links = db.scalars(
            select(StudentParent).where(
                StudentParent.student_id == student.id,
                StudentParent.is_primary.is_(True),
            )
        ).all()
        for existing_primary in existing_primary_links:
            existing_primary.is_primary = False

    link = StudentParent(
        student_id=data.student_id,
        parent_id=data.parent_id,
        relationship_type=data.relationship_type,
        is_primary=data.is_primary,
    )

    db.add(link)
    db.commit()
    db.refresh(link)

    return link