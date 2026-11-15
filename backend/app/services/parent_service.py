from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models.parent import Parent
from app.schemas.parent import ParentCreate, ParentUpdate


def create_parent(
    db: Session,
    data: ParentCreate,
) -> Parent:
    parent = Parent(
        name=data.name,
        primary_phone=data.primary_phone,
        alternate_phone=data.alternate_phone,
        preferred_language=data.preferred_language,
        is_active=data.is_active,
        call_consent=data.call_consent,
        call_opt_out=data.call_opt_out,
    )

    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


def list_parents(
    db: Session,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Parent]:
    query = select(Parent).order_by(desc(Parent.created_at))
    if search:
        search_filter = f"%{search.strip()}%"
        query = query.where(
            or_(
                Parent.name.ilike(search_filter),
                Parent.primary_phone.ilike(search_filter),
            )
        )
    return list(db.execute(query.offset(offset).limit(limit)).scalars().all())


def get_parent(db: Session, parent_id: UUID) -> Parent:
    parent = db.get(Parent, parent_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent record not found",
        )
    return parent


def update_parent(
    db: Session,
    parent_id: UUID,
    data: ParentUpdate,
) -> Parent:
    parent = get_parent(db, parent_id)
    if data.name is not None:
        parent.name = data.name
    if data.primary_phone is not None:
        parent.primary_phone = data.primary_phone
    if data.alternate_phone is not None:
        parent.alternate_phone = data.alternate_phone
    if data.preferred_language is not None:
        parent.preferred_language = data.preferred_language
    if data.is_active is not None:
        parent.is_active = data.is_active
    if data.call_consent is not None:
        parent.call_consent = data.call_consent
    if data.call_opt_out is not None:
        parent.call_opt_out = data.call_opt_out

    db.commit()
    db.refresh(parent)
    return parent
