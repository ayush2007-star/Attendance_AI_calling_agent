from sqlalchemy.orm import Session

from app.models.student_parent import StudentParent
from app.schemas.student_parent import StudentParentCreate


def create_student_parent(
    db: Session,
    data: StudentParentCreate,
) -> StudentParent:

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