from typing import Any
import numpy as np

RESPONSE_CATEGORIES = [
    "WILL_ATTEND",
    "MEDICAL_REASON",
    "LEAVE_RELATED",
    "CALLBACK_REQUESTED",
    "WILL_NOT_ATTEND",
    "WRONG_NUMBER",
    "DISPUTED",
    "OTHER",
]

REPEAT_CALL_FEATURE_NAMES = [
    "attendance_percentage",
    "attendance_gap",
    "previous_call_count",
    "previous_unanswered_count",
    "unanswered_ratio",
    "days_since_last_call",
    "consecutive_absent_days",
    "is_below_60",
    "urgency_index",
] + [f"cat_{c.lower()}" for c in RESPONSE_CATEGORIES]


def extract_repeat_call_features(data: dict[str, Any]) -> np.ndarray:
    """Extract and engineer features for repeat-call prediction."""
    att_pct = float(data.get("attendance_percentage", 75.0))
    threshold = float(data.get("attendance_threshold", 75.0))
    prev_calls = int(data.get("previous_call_count", 0))
    prev_unanswered = int(data.get("previous_unanswered_count", 0))
    days_since = int(data.get("days_since_last_call", 0))
    consecutive_absent = int(data.get("consecutive_absent_days", 0))
    last_cat = str(data.get("last_response_category") or "OTHER").upper()

    attendance_gap = max(0.0, threshold - att_pct)
    unanswered_ratio = prev_unanswered / (prev_calls + 1.0)
    is_below_60 = 1.0 if att_pct < 60.0 else 0.0
    urgency_index = (days_since * 0.1) + (attendance_gap * 0.2) + (consecutive_absent * 0.3)

    features = [
        att_pct,
        attendance_gap,
        float(prev_calls),
        float(prev_unanswered),
        unanswered_ratio,
        float(days_since),
        float(consecutive_absent),
        is_below_60,
        urgency_index,
    ]

    # One-hot encoding of last_response_category
    for cat in RESPONSE_CATEGORIES:
        features.append(1.0 if last_cat == cat else 0.0)

    return np.array(features, dtype=np.float32)


DROPOUT_FEATURE_NAMES = [
    "attendance_percentage",
    "trend_slope",
    "approved_leave_count",
    "unapproved_absent_count",
    "unapproved_ratio",
    "semester",
    "critical_threshold_gap",
]


def extract_dropout_features(data: dict[str, Any]) -> np.ndarray:
    """Extract features for chronic absenteeism / dropout risk prediction."""
    att_pct = float(data.get("attendance_percentage", 75.0))
    slope = float(data.get("trend_slope", 0.0))
    approved = int(data.get("approved_leave_count", 0))
    unapproved = int(data.get("unapproved_absent_count", 0))
    semester = int(data.get("semester", 1))

    total_absent = approved + unapproved
    unapproved_ratio = (unapproved / total_absent) if total_absent > 0 else 0.0
    critical_gap = max(0.0, 75.0 - att_pct)

    return np.array(
        [
            att_pct,
            slope,
            float(approved),
            float(unapproved),
            unapproved_ratio,
            float(semester),
            critical_gap,
        ],
        dtype=np.float32,
    )
