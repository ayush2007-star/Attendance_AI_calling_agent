from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.authorization import user_scopes
from app.models.class_model import ClassModel
from app.models.user import User
from app.schemas.class_schema import ClassCreate
from app.services.authorization_service import resolve_scope_for_user


def create_class(
    db: Session,
    data: ClassCreate,
    current_user: User,
) -> ClassModel:
    scope_id = resolve_scope_for_user(
        db=db,
        user=current_user,
        requested_scope_id=data.scope_id,
    )

    class_obj = ClassModel(
        course_name=data.course_name,
        year=data.year,
        semester=data.semester,
        section=data.section,
        academic_year=data.academic_year,
        class_teacher_id=data.class_teacher_id,
        scope_id=scope_id,
        is_active=data.is_active,
    )

    db.add(class_obj)
    db.commit()
    db.refresh(class_obj)

    return class_obj


def get_classes(
    db: Session,
    current_user: User,
) -> list[ClassModel]:
    query = select(ClassModel)

    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)

    result = db.execute(query.order_by(ClassModel.course_name))

    return list(result.scalars().all())


def get_class(
    db: Session,
    class_id: UUID,
    current_user: User,
) -> ClassModel | None:
    query = select(ClassModel).where(ClassModel.id == class_id)

    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)

    return db.execute(query).scalar_one_or_none()