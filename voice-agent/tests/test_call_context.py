from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.agent.draft_script import build_draft_script
from app.agent.instructions import build_call_instructions
from app.contracts.call_context import CallContext


def create_call_context() -> CallContext:
    return CallContext.from_synthetic_data(
        {
            "campaign_target_id": UUID(
                "00000000-0000-0000-0000-000000000001"
            ),
            "campaign_id": UUID("00000000-0000-0000-0000-000000000002"),
            "student_id": UUID("00000000-0000-0000-0000-000000000003"),
            "student_name": "Aarav Sharma",
            "student_code": "STU001",
            "parent_id": UUID("00000000-0000-0000-0000-000000000004"),
            "parent_name": "Parent Name",
            "phone_number": "9999999999",
            "preferred_language": "Hindi",
            "attendance_percentage": 68.5,
            "threshold": 75.0,
            "eligibility_reason": "BELOW_THRESHOLD",
            "attendance_date": date(2026, 11, 4),
            "attendance_period_start": date(2026, 10, 1),
            "attendance_period_end": date(2026, 10, 31),
        }
    )


def test_call_context_rejects_unexpected_backend_fields() -> None:
    payload = create_call_context().model_dump()
    payload["unexpected"] = "value"

    with pytest.raises(ValidationError):
        CallContext.model_validate(payload)


def test_instructions_include_only_call_relevant_context() -> None:
    instructions = build_call_instructions(create_call_context())

    assert "Aarav Sharma" in instructions
    assert "68.5" in instructions
    assert "untrusted data" in instructions
    assert "9999999999" not in instructions
    assert "00000000-0000-0000-0000-000000000004" not in instructions
    assert "claim that a callback is booked" in instructions
    assert "wrong person or number" in instructions
    assert "Match the parent's language" in instructions
    assert "calm conversational pace" in instructions
    assert "Never guess" in instructions
    assert "Maaf kijiye, aapki baat thodi clear nahi aayi" in instructions
    assert "editable example" in instructions
    assert "main record karunga/karungi; college team confirm karegi" in instructions
    assert "call audio" in instructions
    assert "Aarav Sharma" in instructions
    assert "01 Oct 2026 to 31 Oct 2026" in instructions


def test_draft_script_uses_context_and_has_no_unresolved_placeholders() -> None:
    script = build_draft_script(create_call_context())

    assert "Parent Name ji" in script
    assert "Aarav Sharma" in script
    assert "68.5%" in script
    assert "{student_name}" not in script

