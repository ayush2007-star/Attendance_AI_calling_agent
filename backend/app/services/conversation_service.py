from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.ai.base import AIAnalyzer
from app.models.ai_analysis import AIAnalysis
from app.models.authorization import user_scopes
from app.models.call_attempt import CallAttempt
from app.models.campaign_target import CampaignTarget
from app.models.campaign import CallCampaign
from app.models.class_model import ClassModel
from app.models.conversation import Conversation
from app.models.student import Student
from app.models.transcript import Transcript
from app.models.user import User


CALL_STATUS_TRANSITIONS = {
    "QUEUED": {"RINGING", "FAILED", "CANCELLED"},
    "RINGING": {"CONNECTED", "NO_ANSWER", "BUSY", "FAILED", "CANCELLED"},
    "CONNECTED": {"COMPLETED", "FAILED", "CANCELLED"},
    "COMPLETED": set(),
    "NO_ANSWER": set(),
    "BUSY": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


def create_conversation(
    db: Session,
    call_attempt_id: UUID,
    language: str = "en",
) -> Conversation:
    attempt = db.get(CallAttempt, call_attempt_id)
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call attempt not found",
        )

    existing = db.execute(
        select(Conversation).where(
            Conversation.call_attempt_id == call_attempt_id
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    conversation = Conversation(
        call_attempt_id=call_attempt_id,
        language=language,
        status="ACTIVE",
        started_at=datetime.now(timezone.utc),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def update_call_status(
    db: Session,
    provider_call_id: str,
    new_status: str,
    current_user: User,
) -> CallAttempt:
    query = select(CallAttempt).where(
        CallAttempt.provider_call_id == provider_call_id
    )
    if current_user.role != "SUPER_ADMIN":
        query = (
            query.join(
                CampaignTarget,
                CampaignTarget.id == CallAttempt.campaign_target_id,
            )
            .join(Student, Student.id == CampaignTarget.student_id)
            .join(ClassModel, ClassModel.id == Student.class_id)
            .join(
                user_scopes,
                user_scopes.c.scope_id == ClassModel.scope_id,
            )
            .where(user_scopes.c.user_id == current_user.id)
        )
    attempt = db.execute(query).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider call was not found",
        )

    normalized_status = new_status.upper()
    allowed_statuses = CALL_STATUS_TRANSITIONS.get(attempt.status, set())
    if normalized_status not in allowed_statuses:
        if normalized_status == attempt.status:
            return attempt
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid call status transition",
        )

    attempt.status = normalized_status
    terminal_statuses = {
        "COMPLETED",
        "NO_ANSWER",
        "BUSY",
        "FAILED",
        "CANCELLED",
    }
    if normalized_status in terminal_statuses:
        attempt.ended_at = datetime.now(timezone.utc)
        if attempt.campaign_target_id is not None:
            target = db.get(CampaignTarget, attempt.campaign_target_id)
            campaign = db.get(CallCampaign, attempt.campaign_id)
            if target is not None and campaign is not None:
                if normalized_status == "COMPLETED":
                    target.status = "COMPLETED"
                    campaign.completed_calls += 1
                elif normalized_status == "CANCELLED":
                    target.status = "CANCELLED"
                else:
                    target.status = "FAILED"
                    campaign.failed_calls += 1
    db.commit()
    db.refresh(attempt)
    return attempt


def append_transcript_segment(
    db: Session,
    conversation_id: UUID,
    speaker: str,
    text: str,
    confidence: float | None = None,
) -> Transcript:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    if conversation.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation is not active",
        )

    last_sequence = db.execute(
        select(Transcript.sequence_number)
        .where(Transcript.conversation_id == conversation_id)
        .order_by(Transcript.sequence_number.desc())
        .limit(1)
    ).scalar_one_or_none()
    transcript = Transcript(
        conversation_id=conversation_id,
        speaker=speaker.upper(),
        text=text,
        sequence_number=(last_sequence or 0) + 1,
        confidence=confidence,
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript


def complete_conversation(
    db: Session,
    conversation_id: UUID,
) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    conversation.status = "COMPLETED"
    conversation.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversation)
    return conversation


def analyze_conversation(
    db: Session,
    conversation_id: UUID,
    analyzer: AIAnalyzer,
) -> AIAnalysis:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    transcript_rows = db.execute(
        select(Transcript)
        .where(Transcript.conversation_id == conversation_id)
        .order_by(Transcript.sequence_number)
    ).scalars().all()
    transcript = [
        {"speaker": row.speaker, "text": row.text}
        for row in transcript_rows
    ]
    result = analyzer.analyze(conversation_id, transcript)

    existing = db.execute(
        select(AIAnalysis).where(
            AIAnalysis.conversation_id == conversation_id
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    analysis = AIAnalysis(
        conversation_id=conversation_id,
        category=result.category,
        summary=result.summary,
        followup_required=result.followup_required,
        confidence=result.confidence,
        model_name=result.model_name,
        model_version=result.model_version,
        raw_result=result.raw_result,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis
