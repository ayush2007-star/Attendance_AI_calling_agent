from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.leave import LeaveCreate, LeaveResponse
from app.services.leave_service import create_leave, list_leaves, transition_leave


router = APIRouter(
    prefix="/leaves",
    tags=["Leave"],
)


@router.post(
    "",
    response_model=LeaveResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_leave_endpoint(
    data: LeaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave.create")),
):
    return create_leave(db, data, current_user)


@router.get(
    "",
    response_model=list[LeaveResponse],
)
def list_leave_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave.read")),
):
    return list_leaves(db, current_user)


@router.post(
    "/{leave_id}/approve",
    response_model=LeaveResponse,
)
def approve_leave(
    leave_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave.approve")),
):
    return transition_leave(db, leave_id, "APPROVED", current_user)


@router.post(
    "/{leave_id}/reject",
    response_model=LeaveResponse,
)
def reject_leave(
    leave_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("leave.reject")),
):
    return transition_leave(db, leave_id, "REJECTED", current_user)
