from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest

from app.integrations.calling.base import CallRequest, ProviderCallResult
from app.integrations.calling.factory import get_calling_provider
from app.integrations.calling.mock_provider import MockCallingProvider
from app.integrations.calling.voice_agent_provider import VoiceAgentCallingProvider
from app.models.campaign_target import CampaignTarget
from app.models.call_attempt import CallAttempt
from app.models.student import Student
from app.models.parent import Parent
from app.schemas.calling import (
    CallAnalysisPayload,
    CallCompletionPayload,
    TranscriptTurnPayload,
)
from app.services.calling_service import (
    dispatch_call,
    process_call_webhook_completion,
    simulate_completed_call,
)


def test_mock_calling_provider_initiates_ringing_call() -> None:
    provider = MockCallingProvider()
    attempt_id = uuid4()
    campaign_id = uuid4()
    req = CallRequest(
        attempt_id=attempt_id,
        campaign_id=campaign_id,
        phone_number="+919876543210",
        context={"student_name": "Rahul Sharma", "parent_name": "Sunil Sharma"},
    )
    result = provider.start_call(req)

    assert isinstance(result, ProviderCallResult)
    assert result.status == "RINGING"
    assert result.provider_call_id == f"demo-{attempt_id}"
    assert result.started_at is not None


def test_voice_agent_provider_fails_closed_when_real_calls_disabled(monkeypatch) -> None:
    from app.core.config import settings
    monkeypatch.setattr(settings, "real_calls_enabled", False)

    provider = VoiceAgentCallingProvider()
    req = CallRequest(
        attempt_id=uuid4(),
        campaign_id=uuid4(),
        phone_number="+919876543210",
    )
    with pytest.raises(RuntimeError, match="Real phone calling is disabled by configuration"):
        provider.start_call(req)


def test_voice_agent_provider_requires_e164_format(monkeypatch) -> None:
    from app.core.config import settings
    monkeypatch.setattr(settings, "real_calls_enabled", True)
    monkeypatch.setattr(settings, "external_ai_processing_approved", True)

    provider = VoiceAgentCallingProvider()
    req = CallRequest(
        attempt_id=uuid4(),
        campaign_id=uuid4(),
        phone_number="9876543210",  # Missing +
    )
    with pytest.raises(ValueError, match="Phone number must be E.164"):
        provider.start_call(req)


def test_calling_factory_defaults_to_mock(monkeypatch) -> None:
    from app.core.config import settings
    monkeypatch.setattr(settings, "real_calls_enabled", False)
    provider = get_calling_provider()
    assert isinstance(provider, MockCallingProvider)


def test_process_call_webhook_completion_creates_records_and_followup() -> None:
    db = MagicMock()
    attempt_id = uuid4()
    target_id = uuid4()
    parent_id = uuid4()
    student_id = uuid4()

    mock_attempt = SimpleNamespace(
        id=attempt_id,
        campaign_target_id=target_id,
        parent_id=parent_id,
        status="RINGING",
        provider_call_id="CA1234567890",
        duration_seconds=0,
    )
    mock_target = SimpleNamespace(
        id=target_id,
        student_id=student_id,
        status="CALLING",
    )

    def mock_get(model_cls, obj_id):
        if model_cls is CallAttempt:
            return mock_attempt
        if model_cls is CampaignTarget:
            return mock_target
        return None

    db.get.side_effect = mock_get
    db.execute.return_value.scalars.return_value.first.return_value = mock_attempt

    payload = CallCompletionPayload(
        provider_call_id="CA1234567890",
        status="COMPLETED",
        duration_seconds=42,
        turns=[
            TranscriptTurnPayload(speaker="AGENT", text="Namaste ji! Kya meri baat Rahul ke guardian se ho rahi hai?", confidence=0.99),
            TranscriptTurnPayload(speaker="PARENT", text="Haan ji, main Rahul ka father bol raha hoon.", confidence=0.95),
            TranscriptTurnPayload(speaker="AGENT", text="Rahul aaj college nahi aaye. Kya aap reason bata sakte hain?", confidence=0.99),
            TranscriptTurnPayload(speaker="PARENT", text="Usko fever hai, doctor ke paas le ja rahe hain.", confidence=0.92),
        ],
        analysis=CallAnalysisPayload(
            category="MEDICAL_REASON",
            summary="Parent confirmed student is unwell with fever and visiting doctor.",
            followup_required=True,
            callback_at=None,
            model_name="openai/gpt-oss-20b (Groq Voice Agent)",
            sentiment="NEUTRAL",
        ),
        is_demo=False,
    )

    result = process_call_webhook_completion(db, payload)

    assert result.status == "COMPLETED"
    assert result.duration_seconds == 42
    assert mock_target.status == "COMPLETED"
    assert db.add.call_count >= 3  # Conversation, TranscriptTurns, AIAnalysis, FollowUp, AuditLog
    db.commit.assert_called()


def test_simulate_completed_call_generates_hindi_dialogue() -> None:
    db = MagicMock()
    attempt_id = uuid4()
    target_id = uuid4()
    student_id = uuid4()
    parent_id = uuid4()

    mock_attempt = SimpleNamespace(
        id=attempt_id,
        campaign_target_id=target_id,
        parent_id=parent_id,
        status="RINGING",
        provider_call_id="demo-test",
    )
    mock_target = SimpleNamespace(
        id=target_id,
        student_id=student_id,
        attendance_percentage_used=68.5,
    )
    mock_student = SimpleNamespace(
        id=student_id,
        first_name="Aarav",
        last_name="Sharma",
    )
    mock_parent = SimpleNamespace(
        id=parent_id,
        name="Sunil Sharma",
    )

    def mock_get(model_cls, obj_id):
        if model_cls is CallAttempt:
            return mock_attempt
        if model_cls is CampaignTarget:
            return mock_target
        if model_cls is Student:
            return mock_student
        if model_cls is Parent:
            return mock_parent
        return None

    db.get.side_effect = mock_get
    db.execute.return_value.scalars.return_value.first.return_value = mock_attempt

    current_user = SimpleNamespace(id=uuid4(), role="SUPER_ADMIN", full_name="Admin User")

    completed = simulate_completed_call(
        db=db,
        attempt_id=attempt_id,
        current_user=current_user,
        reason_preset="MEDICAL_REASON",
    )

    assert completed.status == "COMPLETED"
    assert db.add.call_count >= 3
    db.commit.assert_called()
