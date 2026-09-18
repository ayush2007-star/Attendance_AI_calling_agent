from sqlalchemy.orm import Session

from app.models.parent import Parent
from app.schemas.parent import ParentCreate


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
    )

    db.add(parent)
    db.commit()
    db.refresh(parent)

    return parent