from pydantic import BaseModel


class DashboardSummary(BaseModel):
    students: int
    eligible_targets: int
    active_campaigns: int
    completed_calls: int
    failed_calls: int
    unanswered_calls: int
    pending_followups: int
    due_followups: int
    scheduled_followups: int
