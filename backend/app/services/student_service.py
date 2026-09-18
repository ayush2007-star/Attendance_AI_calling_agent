from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_model import ClassModel
from app.models.student import Student
from app.models.user import User
from app.models.authorization import user_scopes
from app.schemas.student_schema import StudentCreate
from app.services.class_service import get_class


def create_student(
    db: Session,
    data: StudentCreate,
    current_user: User,
) -> Student:

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
            Student.student_code == data.student_code
        )
    ).scalar_one_or_none()

    if existing_student:
        raise HTTPException(
            status_code=409,
            detail="Student code already exists",
        )

    student = Student(
        student_code=data.student_code,
        roll_number=data.roll_number,
        first_name=data.first_name,
        last_name=data.last_name,
        class_id=data.class_id,
        email=data.email,
        is_active=data.is_active,
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    return student


def get_students(
    db: Session,
    current_user: User,
) -> list[Student]:
    query = select(Student)

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
    query = select(Student).where(Student.id == student_id)

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