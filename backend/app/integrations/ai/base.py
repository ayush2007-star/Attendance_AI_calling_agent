from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class AnalysisResult:
    category: str
    summary: str | None
    followup_required: bool
    confidence: float | None
    model_name: str
    model_version: str | None
    raw_result: dict | None


class AIAnalyzer(Protocol):
    def analyze(
        self,
        conversation_id: UUID,
        transcript: list[dict[str, str]],
    ) -> AnalysisResult:
        """Return an advisory analysis without executing business actions."""
