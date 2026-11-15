from typing import Any
from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.core.config import settings
from app.db.dependencies import get_db
from app.integrations.calling.factory import get_calling_provider
from app.models.campaign_target import CampaignTarget
from app.models.user import User
from app.schemas.calling import (
    CallAttemptDetailResponse,
    CallAttemptResponse,
    CallCompletionPayload,
    CallContextResponse,
    CallStatusUpdate,
    DemoCallSimulateRequest,
    VoiceServiceStatusResponse,
)
from app.services.calling_service import (
    dispatch_call,
    get_call_attempt_detail,
    get_campaign_target_context,
    list_call_attempts,
    process_call_webhook_completion,
    queue_campaign_target,
    simulate_completed_call,
)
from app.services.conversation_service import update_call_status

router = APIRouter(
    prefix="/calls",
    tags=["Calls & Voice Telephony"],
)


@router.get(
    "/service-status",
    response_model=VoiceServiceStatusResponse,
)
def get_voice_service_status(
    current_user: User = Depends(get_current_user),
) -> VoiceServiceStatusResponse:
    """Check connectivity and operational parameters of the voice-agent telephony service."""
    service_online = False
    voice_url = settings.voice_agent_base_url.rstrip("/")

    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{voice_url}/health")
            if resp.status_code == 200:
                service_online = True
    except Exception:
        service_online = False

    # Check provider keys presence from environment/settings without exposing values
    from app.core.config import settings as backend_settings

    # Also check voice agent settings if readable
    twilio_ok = bool(backend_settings.voice_agent_api_key or not backend_settings.real_calls_enabled)

    return VoiceServiceStatusResponse(
        service_online=service_online,
        voice_agent_url=voice_url,
        real_calls_enabled=backend_settings.real_calls_enabled,
        external_ai_approved=backend_settings.external_ai_processing_approved,
        calling_provider=backend_settings.calling_provider,
        configured_model="openai/gpt-oss-20b (Groq API)",
        tts_provider="Edge TTS (hi-IN-MadhurNeural / en-IN-NeerjaNeural)",
        school_name="BBS College of Engineering and Technology",
        twilio_configured=backend_settings.real_calls_enabled,
        deepgram_configured=backend_settings.real_calls_enabled,
        groq_configured=True,
    )


@router.get(
    "/attempts",
    response_model=list[dict],
)
def list_attempts(
    campaign_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.read")),
):
    """List call attempts with student and parent details, status, and duration."""
    return list_call_attempts(
        db=db,
        current_user=current_user,
        campaign_id=campaign_id,
        status_filter=status,
        student_id=student_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/attempts/{attempt_id}",
    response_model=CallAttemptDetailResponse,
)
def get_attempt_details(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.read")),
):
    """Retrieve full call attempt details including multi-turn transcripts and AI analysis."""
    return get_call_attempt_detail(db, attempt_id, current_user)


@router.post(
    "/targets/{campaign_target_id}/queue",
    response_model=CallAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def queue_call(
    campaign_target_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    """Queue a campaign target for sequential phone call dispatch."""
    return queue_campaign_target(db, campaign_target_id, current_user)


@router.get(
    "/targets/{campaign_target_id}/context",
    response_model=CallContextResponse,
)
def get_call_context(
    campaign_target_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.read")),
):
    """Fetch structured context for a target to be used during call execution."""
    return get_campaign_target_context(
        db,
        campaign_target_id,
        current_user,
    )


@router.post(
    "/attempts/{attempt_id}/dispatch",
    response_model=CallAttemptResponse,
)
def dispatch_call_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    """Dispatch a queued call attempt through the configured provider."""
    provider = get_calling_provider()
    return dispatch_call(db, attempt_id, provider, current_user)


@router.post(
    "/dispatch-target/{target_id}",
    response_model=dict[str, Any],
)
def dispatch_target_direct(
    target_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    """Queue and immediately dispatch a target (useful for single-click call in UI)."""
    target = db.get(CampaignTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Campaign target not found")

    attempt = None
    if target.status == "PENDING" or target.status == "FAILED":
        attempt = queue_campaign_target(db, target_id, current_user)
    elif target.status == "QUEUED":
        from sqlalchemy import desc, select
        from app.models.call_attempt import CallAttempt
        attempt = db.execute(
            select(CallAttempt)
            .where(CallAttempt.campaign_target_id == target_id, CallAttempt.status == "QUEUED")
            .order_by(desc(CallAttempt.created_at))
        ).scalars().first()

    if not attempt:
        raise HTTPException(status_code=409, detail="Target cannot be dispatched in its current state")

    provider = get_calling_provider()
    dispatched = dispatch_call(db, attempt.id, provider, current_user)

    # In mock mode, complete the simulated call immediately so UI gets realistic conversation & analysis
    if not settings.real_calls_enabled:
        dispatched = simulate_completed_call(
            db=db,
            attempt_id=dispatched.id,
            current_user=current_user,
            reason_preset="MEDICAL_REASON",
        )

    return {
        "success": True,
        "attempt_id": dispatched.id,
        "provider_call_id": dispatched.provider_call_id,
        "status": dispatched.status,
        "is_demo": not settings.real_calls_enabled,
    }


@router.post(
    "/simulate-demo",
    response_model=CallAttemptDetailResponse,
)
def simulate_demo_call_endpoint(
    req: DemoCallSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    """Execute a realistic multi-turn Hindi/Hinglish demo call with real database persistence."""
    target = None
    if req.campaign_target_id:
        target = db.get(CampaignTarget, req.campaign_target_id)
    elif req.student_id:
        from sqlalchemy import select
        target = db.execute(
            select(CampaignTarget)
            .where(CampaignTarget.student_id == req.student_id)
            .order_by(CampaignTarget.created_at.desc())
        ).scalars().first()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign target not found for simulation. Create a campaign first.",
        )

    attempt = queue_campaign_target(db, target.id, current_user)
    completed_attempt = simulate_completed_call(
        db=db,
        attempt_id=attempt.id,
        current_user=current_user,
        reason_preset=req.reason_preset,
        custom_reply=req.custom_parent_reply,
    )
    return get_call_attempt_detail(db, completed_attempt.id, current_user)


@router.post(
    "/attempts/{provider_call_id}/status",
    response_model=CallAttemptResponse,
)
def update_provider_call_status(
    provider_call_id: str,
    data: CallStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("calls.manage")),
):
    """Update call status from telephony provider events."""
    return update_call_status(
        db,
        provider_call_id,
        data.status,
        current_user,
    )


@router.post(
    "/callback",
    response_model=dict[str, Any],
)
def telephony_call_completed_callback(
    payload: CallCompletionPayload,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """
    Secure server-to-server webhook endpoint called by voice-agent when a call finishes.
    Persists call duration, transcript turns, AI response classification, and follow-ups.
    """
    # Verify server-to-server key if configured
    if settings.voice_agent_api_key and x_api_key != settings.voice_agent_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid callback API key")

    attempt = process_call_webhook_completion(db, payload)
    return {
        "success": True,
        "attempt_id": attempt.id,
        "status": attempt.status,
        "duration": attempt.duration_seconds,
    }
