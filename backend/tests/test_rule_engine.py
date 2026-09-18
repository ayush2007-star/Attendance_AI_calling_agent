from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.services.rule_engine import validate_callback_decision


def test_callback_requires_timezone_aware_time() -> None:
    with pytest.raises(HTTPException) as error:
        validate_callback_decision(
            "CALLBACK_REQUESTED",
            True,
            datetime(2026, 9, 21, 10, 0),
        )

    assert error.value.status_code == 422


def test_callback_accepts_explicit_timezone() -> None:
    validate_callback_decision(
        "CALLBACK_REQUESTED",
        True,
        datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc),
    )


def test_no_followup_required_does_not_need_schedule() -> None:
    validate_callback_decision("WILL_ATTEND", False, None)
