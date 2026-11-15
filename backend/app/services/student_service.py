from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.authorization import user_scopes
from app.models.class_model import ClassModel
from app.models.parent import Parent
from app.models.student import Student
from app.models.student_parent import StudentParent
from app.models.user import User
from app.schemas.student_schema import StudentCreate
from app.services.class_service import get_class


def create_student(
    db: Session,
    data: StudentCreate,
    current_user: User,
) -> Student:

    parent_name = (data.parent_name or "").strip()
    parent_phone = (data.parent_phone or "").strip()
    student_code = data.student_code.strip()
    roll_number = data.roll_number.strip()
    if not student_code or not roll_number or not data.first_name.strip():
        raise HTTPException(
            status_code=422,
            detail="Student ID, roll number, and first name are required",
        )
    if bool(parent_name) != bool(parent_phone):
        raise HTTPException(
            status_code=422,
            detail="Provide both parent name and parent phone, or leave both empty",
        )

    # Make sure class exists
    class_obj = get_class(db, data.class_id, current_user)

    if class_obj is None:
        raise HTTPException(
            status_code=404,
            detail="Class not found",
        )

    # Prevent duplicate student code
    existing_student = db.execute(
        select(Student).where(
            Student.student_code == student_code
        )
    ).scalar_one_or_none()

    if existing_student:
        raise HTTPException(
            status_code=409,
            detail="Student code already exists",
        )

    student = Student(
        student_code=student_code,
        roll_number=roll_number,
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip() if data.last_name else None,
        class_id=data.class_id,
        email=data.email,
        is_active=data.is_active,
    )

    db.add(student)
    if parent_name and parent_phone:
        parent = Parent(
            name=parent_name,
            primary_phone=parent_phone,
        )
        db.add(parent)
        db.flush()
        db.add(
            StudentParent(
                student=student,
                parent=parent,
                relationship_type=(data.relationship or "Guardian").strip(),
                is_primary=True,
            )
        )
    db.commit()
    db.refresh(student)

    return student


def get_students(
    db: Session,
    current_user: User,
) -> list[Student]:
    query = select(Student).options(
        selectinload(Student.parent_links).selectinload(StudentParent.parent)
    )

    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            ClassModel,
            ClassModel.id == Student.class_id,
        ).join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)

    result = db.execute(query.order_by(Student.roll_number))

    return list(result.scalars().all())


def get_student(
    db: Session,
    student_id: UUID,
    current_user: User,
) -> Student:
    query = (
        select(Student)
        .options(
            selectinload(Student.parent_links).selectinload(StudentParent.parent)
        )
        .where(Student.id == student_id)
    )

    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            ClassModel,
            ClassModel.id == Student.class_id,
        ).join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)

    student = db.execute(query).scalar_one_or_none()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return student