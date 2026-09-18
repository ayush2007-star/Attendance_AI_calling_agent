from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.leave import LeaveCreate
from app.services.leave_service import ALLOWED_TRANSITIONS


def test_leave_rejects_reversed_date_range() -> None:
    with pytest.raises(ValidationError):
        LeaveCreate(
            student_id="00000000-0000-0000-0000-000000000001",
            start_date=date(2026, 9, 20),
            end_date=date(2026, 9, 19),
            reason="Medical",
        )


def test_leave_transitions_are_explicit() -> None:
    assert ALLOWED_TRANSITIONS["PENDING"] == {
        "APPROVED",
        "REJECTED",
        "CANCELLED",
    }
    assert ALLOWED_TRANSITIONS["REJECTED"] == set()
