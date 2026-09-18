from datetime import datetime

from fastapi import HTTPException, status


CALLBACK_REQUESTED = "CALLBACK_REQUESTED"


def validate_callback_decision(
    category: str,
    followup_required: bool,
    scheduled_for: datetime | None,
) -> None:
    if not followup_required:
        return

    if category.upper() == CALLBACK_REQUESTED and scheduled_for is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Callback request requires an explicit scheduled time",
        )

    if scheduled_for is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Follow-up requires an explicit scheduled time",
        )

    if scheduled_for.tzinfo is None or scheduled_for.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Follow-up time must include a timezone",
        )
