from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from app.models.ai_analysis import AIAnalysis
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation
from app.models.followup import Followup
from app.models.parent import Parent
from app.models.campaign import CallCampaign
from app.models.attendance import AttendanceRecord
from app.integrations.calling.base import CallRequest, CallingProvider
from app.models.call_attempt import CallAttempt
from app.models.campaign_target import CampaignTarget
from app.models.class_model import ClassModel
from app.models.student import Student
from app.models.student_parent import StudentParent
from app.models.transcript import Transcript
from app.models.user import User
from app.models.authorization import user_scopes
from app.schemas.calling import (
    CallAnalysisPayload,
    CallCompletionPayload,
    TranscriptTurnPayload,
)


def queue_campaign_target(
    db: Session,
    campaign_target_id: UUID,
    current_user: User,
) -> CallAttempt:
    query = (
        select(CampaignTarget, CallCampaign, Student)
        .join(Student, Student.id == CampaignTarget.student_id)
        .join(CallCampaign, CallCampaign.id == CampaignTarget.campaign_id)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .where(
            CampaignTarget.id == campaign_target_id,
            Student.is_active.is_(True),
            ClassModel.is_active.is_(True),
        )
    )
    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)

    target_context = db.execute(query).one_or_none()
    if target_context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign target not found",
        )

    target, campaign, student = target_context
    attendance_is_absent = db.execute(
        select(AttendanceRecord.id).where(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.attendance_date == campaign.attendance_date,
            AttendanceRecord.status == "ABSENT",
        )
    ).scalar_one_or_none()
    if attendance_is_absent is None:
        target.status = "CANCELLED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is no longer marked absent for this campaign date",
        )

    if not getattr(target, "contact_authorized", True) or not _has_current_primary_contact(db, target, student):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign guardian contact is not authorized, active, or primary",
        )

    if target.status not in {"PENDING", "FAILED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign target is not available for queueing",
        )

    if target.parent_id is None or not target.selected_phone_number:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign target has no callable contact",
        )

    last_attempt_number = db.execute(
        select(func.max(CallAttempt.attempt_number)).where(
            CallAttempt.campaign_target_id == campaign_target_id,
        )
    ).scalar_one()

    attempt = CallAttempt(
        campaign_id=target.campaign_id,
        campaign_target_id=target.id,
        absence_event_id=None,
        parent_id=target.parent_id,
        attempt_number=(last_attempt_number or 0) + 1,
        phone_number=target.selected_phone_number,
        status="QUEUED",
    )
    target.status = "QUEUED"
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt

def get_campaign_target_context(
    db: Session,
    campaign_target_id: UUID,
    current_user: User,
):
    query = (
        select(
            CampaignTarget,
            Student,
            Parent,
            CallCampaign,
        )
        .join(Student, Student.id == CampaignTarget.student_id)
        .join(Parent, Parent.id == CampaignTarget.parent_id)
        .join(CallCampaign, CallCampaign.id == CampaignTarget.campaign_id)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .where(CampaignTarget.id == campaign_target_id)
    )

    if current_user.role != "SUPER_ADMIN":
        query = query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(
            user_scopes.c.user_id == current_user.id
        )

    result = db.execute(query).one_or_none()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign target not found",
        )

    target, student, parent, campaign = result

    if not target.selected_phone_number:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign target has no callable contact",
        )

    return {
        "campaign_target_id": target.id,
        "campaign_id": target.campaign_id,
        "student_id": student.id,
        "student_name": f"{student.first_name} {student.last_name or ''}".strip(),
        "student_code": student.student_code,
        "parent_id": parent.id,
        "parent_name": parent.name,
        "phone_number": target.selected_phone_number,
        "preferred_language": parent.preferred_language,
        "attendance_percentage": float(target.attendance_percentage_used),
        "threshold": float(target.threshold_used),
        "eligibility_reason": target.eligibility_reason,
        "attendance_date": campaign.attendance_date,
        "attendance_period_start": campaign.attendance_period_start,
        "attendance_period_end": campaign.attendance_period_end,
    }
def dispatch_call(
    db: Session,
    attempt_id: UUID,
    provider: CallingProvider,
    current_user: User,
) -> CallAttempt:
    query = select(CallAttempt).where(CallAttempt.id == attempt_id)
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
            detail="Call attempt not found",
        )

    if attempt.status != "QUEUED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Call attempt is not queued",
        )

    validation_query = (
        select(CampaignTarget, CallCampaign, Student)
        .select_from(CallAttempt)
        .join(CampaignTarget, CampaignTarget.id == CallAttempt.campaign_target_id)
        .join(CallCampaign, CallCampaign.id == CampaignTarget.campaign_id)
        .join(Student, Student.id == CampaignTarget.student_id)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .where(
            CallAttempt.id == attempt_id,
            Student.is_active.is_(True),
            ClassModel.is_active.is_(True),
        )
    )
    if current_user.role != "SUPER_ADMIN":
        validation_query = validation_query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)
    target_context = db.execute(validation_query).one_or_none()
    if target_context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call attempt not found",
        )

    target, campaign, student = target_context
    attendance_is_absent = db.execute(
        select(AttendanceRecord.id).where(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.attendance_date == campaign.attendance_date,
            AttendanceRecord.status == "ABSENT",
        )
    ).scalar_one_or_none()
    if attendance_is_absent is None:
        attempt.status = "CANCELLED"
        target.status = "CANCELLED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is no longer marked absent for this campaign date",
        )
    if not getattr(target, "contact_authorized", True) or not _has_current_primary_contact(db, target, student):
        attempt.status = "CANCELLED"
        target.status = "CANCELLED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign guardian contact is not active, authorized, or primary",
        )

    parent = db.get(Parent, target.parent_id) if target.parent_id else None
    context = {
        "campaign_target_id": str(target.id),
        "student_id": str(student.id),
        "student_name": f"{student.first_name} {student.last_name or ''}".strip(),
        "parent_name": parent.name if parent else "Guardian",
        "phone_number": attempt.phone_number,
        "attendance_date": str(campaign.attendance_date),
        "preferred_language": parent.preferred_language if parent else "hi-IN",
        "attendance_percentage": float(target.attendance_percentage_used),
        "threshold": float(target.threshold_used),
        "student_code": student.student_code or student.roll_number,
    }

    result = provider.start_call(
        CallRequest(
            attempt_id=attempt.id,
            phone_number=attempt.phone_number,
            campaign_id=attempt.campaign_id,
            context=context,
        )
    )
    attempt.provider_call_id = result.provider_call_id
    attempt.status = result.status
    attempt.started_at = result.started_at or datetime.now(timezone.utc)
    target.status = "RINGING"
    db.commit()
    db.refresh(attempt)
    return attempt


def _has_current_primary_contact(
    db: Session,
    target: CampaignTarget,
    student: Student,
) -> bool:
    if target.parent_id is None or not target.selected_phone_number:
        return False
    return db.execute(
        select(Parent.id).join(
            StudentParent,
            StudentParent.parent_id == Parent.id,
        ).where(
            Parent.id == target.parent_id,
            Parent.is_active.is_(True),
            Parent.call_consent.is_(True),
            Parent.call_opt_out.is_(False),
            Parent.primary_phone == target.selected_phone_number,
            StudentParent.student_id == student.id,
            StudentParent.is_primary.is_(True),
        )
    ).scalar_one_or_none() is not None


def list_call_attempts(
    db: Session,
    current_user: User,
    campaign_id: UUID | None = None,
    status_filter: str | None = None,
    student_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    query = (
        select(
            CallAttempt,
            Student,
            Parent,
            CallCampaign,
        )
        .outerjoin(CampaignTarget, CampaignTarget.id == CallAttempt.campaign_target_id)
        .outerjoin(Student, Student.id == CampaignTarget.student_id)
        .outerjoin(Parent, Parent.id == CallAttempt.parent_id)
        .join(CallCampaign, CallCampaign.id == CallAttempt.campaign_id)
        .order_by(desc(CallAttempt.created_at))
    )

    if current_user.role != "SUPER_ADMIN":
        query = (
            query.join(ClassModel, ClassModel.id == Student.class_id)
            .join(user_scopes, user_scopes.c.scope_id == ClassModel.scope_id)
            .where(user_scopes.c.user_id == current_user.id)
        )

    if campaign_id:
        query = query.where(CallAttempt.campaign_id == campaign_id)
    if status_filter:
        query = query.where(CallAttempt.status == status_filter.upper())
    if student_id:
        query = query.where(CampaignTarget.student_id == student_id)

    rows = db.execute(query.offset(offset).limit(limit)).all()
    results = []
    for attempt, student, parent, campaign in rows:
        is_demo = str(attempt.provider_call_id or "").startswith("demo-") or str(attempt.provider_call_id or "").startswith("local-")
        results.append(
            {
                "id": attempt.id,
                "campaign_id": attempt.campaign_id,
                "campaign_name": campaign.name if campaign else None,
                "campaign_target_id": attempt.campaign_target_id,
                "student_id": student.id if student else None,
                "student_name": f"{student.first_name} {student.last_name or ''}".strip() if student else "Unknown",
                "student_roll": student.roll_number if student else None,
                "parent_id": attempt.parent_id,
                "parent_name": parent.name if parent else "Guardian",
                "attempt_number": attempt.attempt_number,
                "phone_number": attempt.phone_number,
                "status": attempt.status,
                "provider_call_id": attempt.provider_call_id,
                "started_at": attempt.started_at,
                "ended_at": attempt.ended_at,
                "duration_seconds": attempt.duration_seconds,
                "failure_reason": attempt.failure_reason,
                "is_demo": is_demo,
            }
        )
    return results


def get_call_attempt_detail(
    db: Session,
    attempt_id: UUID,
    current_user: User,
) -> dict:
    query = (
        select(
            CallAttempt,
            Student,
            Parent,
            CallCampaign,
        )
        .outerjoin(CampaignTarget, CampaignTarget.id == CallAttempt.campaign_target_id)
        .outerjoin(Student, Student.id == CampaignTarget.student_id)
        .outerjoin(Parent, Parent.id == CallAttempt.parent_id)
        .join(CallCampaign, CallCampaign.id == CallAttempt.campaign_id)
        .where(CallAttempt.id == attempt_id)
    )

    if current_user.role != "SUPER_ADMIN":
        query = (
            query.join(ClassModel, ClassModel.id == Student.class_id)
            .join(user_scopes, user_scopes.c.scope_id == ClassModel.scope_id)
            .where(user_scopes.c.user_id == current_user.id)
        )

    row = db.execute(query).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call attempt not found",
        )

    attempt, student, parent, campaign = row
    is_demo = str(attempt.provider_call_id or "").startswith("demo-") or str(attempt.provider_call_id or "").startswith("local-")

    # Load conversation if exists
    conv_query = select(Conversation).where(Conversation.call_attempt_id == attempt.id)
    conversation = db.execute(conv_query).scalar_one_or_none()

    conv_data = None
    if conversation:
        transcripts_query = (
            select(Transcript)
            .where(Transcript.conversation_id == conversation.id)
            .order_by(Transcript.sequence_number)
        )
        transcripts = db.execute(transcripts_query).scalars().all()

        analysis_query = select(AIAnalysis).where(AIAnalysis.conversation_id == conversation.id)
        analysis = db.execute(analysis_query).scalar_one_or_none()

        conv_data = {
            "id": conversation.id,
            "call_attempt_id": conversation.call_attempt_id,
            "started_at": conversation.started_at,
            "ended_at": conversation.ended_at,
            "language": conversation.language,
            "status": conversation.status,
            "transcripts": [
                {
                    "id": t.id,
                    "speaker": t.speaker,
                    "text": t.text,
                    "sequence_number": t.sequence_number,
                    "confidence": t.confidence,
                }
                for t in transcripts
            ],
            "analysis": (
                {
                    "id": analysis.id,
                    "category": analysis.category,
                    "summary": analysis.summary,
                    "followup_required": analysis.followup_required,
                    "confidence": analysis.confidence,
                    "model_name": analysis.model_name,
                    "model_version": analysis.model_version,
                }
                if analysis
                else None
            ),
        }

    return {
        "id": attempt.id,
        "campaign_id": attempt.campaign_id,
        "campaign_name": campaign.name if campaign else None,
        "campaign_target_id": attempt.campaign_target_id,
        "student_id": student.id if student else None,
        "student_name": f"{student.first_name} {student.last_name or ''}".strip() if student else "Unknown",
        "student_roll": student.roll_number if student else None,
        "parent_id": attempt.parent_id,
        "parent_name": parent.name if parent else "Guardian",
        "attempt_number": attempt.attempt_number,
        "phone_number": attempt.phone_number,
        "status": attempt.status,
        "provider_call_id": attempt.provider_call_id,
        "started_at": attempt.started_at,
        "ended_at": attempt.ended_at,
        "duration_seconds": attempt.duration_seconds,
        "failure_reason": attempt.failure_reason,
        "is_demo": is_demo,
        "conversation": conv_data,
    }


def process_call_webhook_completion(
    db: Session,
    payload: CallCompletionPayload,
) -> CallAttempt:
    """
    Synchronizes completed call result from telephony/mock into the backend source of truth.
    Updates CallAttempt, creates Conversation, saves Transcripts, saves AIAnalysis,
    schedules Followup if required, updates CampaignTarget & Campaign stats, and logs Audit.
    """
    query = select(CallAttempt)
    if payload.attempt_id:
        query = query.where(CallAttempt.id == payload.attempt_id)
    else:
        query = query.where(CallAttempt.provider_call_id == payload.provider_call_id)

    attempt = db.execute(query).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call attempt not found for provider ID {payload.provider_call_id}",
        )

    target = db.get(CampaignTarget, attempt.campaign_target_id) if attempt.campaign_target_id else None
    campaign = db.get(CallCampaign, attempt.campaign_id)

    now = datetime.now(timezone.utc)
    normalized_status = payload.status.upper()
    attempt.status = normalized_status
    attempt.ended_at = now
    if payload.duration_seconds is not None:
        attempt.duration_seconds = payload.duration_seconds
    elif attempt.started_at:
        attempt.duration_seconds = max(1, int((now - attempt.started_at).total_seconds()))
    if payload.failure_reason:
        attempt.failure_reason = payload.failure_reason

    # Create/update conversation
    conv = db.execute(
        select(Conversation).where(Conversation.call_attempt_id == attempt.id)
    ).scalar_one_or_none()
    if not conv:
        conv = Conversation(
            call_attempt_id=attempt.id,
            language=payload.language or "hi-IN",
            status="COMPLETED",
            started_at=attempt.started_at or now,
            ended_at=now,
        )
        db.add(conv)
        db.flush()
    else:
        conv.status = "COMPLETED"
        conv.ended_at = now

    # Save transcripts
    if payload.turns:
        for index, turn in enumerate(payload.turns, start=1):
            db.add(
                Transcript(
                    conversation_id=conv.id,
                    speaker=turn.speaker.upper(),
                    text=turn.text,
                    sequence_number=turn.sequence_number or index,
                    confidence=turn.confidence,
                )
            )

    # Save AI Analysis
    analysis_record = None
    if payload.analysis:
        existing_analysis = db.execute(
            select(AIAnalysis).where(AIAnalysis.conversation_id == conv.id)
        ).scalar_one_or_none()
        if not existing_analysis:
            analysis_record = AIAnalysis(
                conversation_id=conv.id,
                category=payload.analysis.category,
                summary=payload.analysis.summary,
                followup_required=payload.analysis.followup_required,
                confidence=payload.analysis.confidence,
                model_name=payload.analysis.model_name,
                model_version="1.0",
                raw_result=payload.analysis.raw_dict or {"sentiment": payload.analysis.sentiment},
            )
            db.add(analysis_record)

    # If followup is required, schedule it
    if payload.analysis and payload.analysis.followup_required and target:
        student = db.get(Student, target.student_id)
        due_time = payload.analysis.callback_at or (now + timedelta(hours=4))
        followup = Followup(
            student_id=target.student_id,
            conversation_id=conv.id,
            campaign_id=attempt.campaign_id,
            campaign_target_id=target.id,
            parent_id=attempt.parent_id,
            reason=payload.analysis.summary or f"Parent follow-up needed for {student.first_name if student else 'student'}",
            priority="HIGH" if payload.analysis.category in ("DISPUTED", "CALLBACK_REQUESTED") else "MEDIUM",
            status="SCHEDULED",
            due_at=due_time,
            scheduled_for=due_time,
            timezone_name="Asia/Kolkata",
            retry_count=0,
        )
        db.add(followup)

    # Update target and campaign statistics
    if target:
        if normalized_status == "COMPLETED":
            target.status = "COMPLETED"
            if campaign:
                campaign.completed_calls += 1
        elif normalized_status == "CANCELLED":
            target.status = "CANCELLED"
        else:
            target.status = "FAILED"
            if campaign:
                campaign.failed_calls += 1

    # Audit log
    db.add(
        AuditLog(
            user_id=campaign.created_by if campaign else None,
            action="VOICE_CALL_COMPLETED",
            entity_type="CallAttempt",
            entity_id=str(attempt.id),
            new_values={
                "status": normalized_status,
                "duration": attempt.duration_seconds,
                "category": payload.analysis.category if payload.analysis else None,
                "is_demo": payload.is_demo,
            },
        )
    )

    db.commit()
    db.refresh(attempt)
    return attempt


def simulate_completed_call(
    db: Session,
    attempt_id: UUID,
    current_user: User,
    reason_preset: str = "MEDICAL_REASON",
    custom_reply: str | None = None,
) -> CallAttempt:
    """
    Executes a deterministic, multi-turn conversational demo call.
    Uses realistic Hindi/Hinglish dialogues with BBS College attendance persona,
    classifies the parent response, and updates all database records.
    Clearly tags the attempt with is_demo=True.
    """
    attempt = db.get(CallAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call attempt not found",
        )

    target = db.get(CampaignTarget, attempt.campaign_target_id) if attempt.campaign_target_id else None
    student = db.get(Student, target.student_id) if target else None
    parent = db.get(Parent, attempt.parent_id) if attempt.parent_id else None

    student_name = f"{student.first_name} {student.last_name or ''}".strip() if student else "Student"
    parent_name = parent.name if parent else "Guardian"
    pct = float(target.attendance_percentage_used) if target else 68.0

    # Build multi-turn conversational Hindi dialogue
    turns = [
        {
            "speaker": "AGENT",
            "text": f"Namaste {parent_name} ji! Main BBS College of Engineering and Technology ke attendance department se bol raha hoon. Kya meri baat {student_name} ke guardian se ho rahi hai?",
            "confidence": 0.99,
        },
        {
            "speaker": "PARENT",
            "text": f"Haan ji namaste, main {parent_name} bol raha hoon {student_name} ka father. Boliye kya baat hai?",
            "confidence": 0.96,
        },
        {
            "speaker": "AGENT",
            "text": f"Ji, aapko inform karna tha ki {student_name} ki aaj college attendance mark nahi hui hai. Unki attendance abhi {pct:.0f}% hai. Kya aap absence ka reason batana chahenge?",
            "confidence": 0.98,
        },
    ]

    preset = (reason_preset or "MEDICAL_REASON").upper()
    if custom_reply:
        parent_speech = custom_reply
        category = "OTHER"
        summary = custom_reply
        followup_req = False
        closing = f"Ji samajh gaya {parent_name} ji. Humne aapka message note kar liya hai aur college team ko forward kar denge. Dhanyavaad."
    elif preset == "MEDICAL_REASON":
        parent_speech = "Haan ji, kal raat se use tezz bukhar aur sardi thi. Doctor ko dikhaya hai, abhi dawa chal rahi hai isliye aaj nahi bhej paye."
        category = "MEDICAL_REASON"
        summary = "Student was unwell with high fever; under doctor prescription."
        followup_req = False
        closing = f"Ji samajh gaya {parent_name} ji. Humne medical leave note kar li hai. Student ko aaraam karne dijiye aur college aane par prescription dikha dijiyega. Dhanyavaad."
    elif preset == "CALLBACK_REQUESTED":
        parent_speech = "Namaste, main abhi office meeting me hoon aur baat nahi kar sakta. Kripya kal subah 10 baje dubara call kariyega."
        category = "CALLBACK_REQUESTED"
        summary = "Parent busy at work; explicitly requested callback tomorrow at 10:00 AM."
        followup_req = True
        closing = f"Ji theek hai {parent_name} ji, humne note kar liya hai ki aap kal subah baat karenge. College team dubara call karegi. Dhanyavaad."
    elif preset == "WILL_ATTEND":
        parent_speech = "Namaste. Bus late thi isliye time lag gaya, wo campus ke liye nikal chuka hai aur agle 15 minute me pahunch jayega."
        category = "WILL_ATTEND"
        summary = "Student delayed by transit; arriving in 15 minutes."
        followup_req = False
        closing = f"Dhanyavaad batane ke liye! Campus pahunchte hi {student_name} class attend kar lenge. Shubh din!"
    elif preset == "OUT_OF_STATION":
        parent_speech = "Hamare parivar me shaadi thi gaon me, isliye poori family bahar aayi hui hai. Monday se regular aayega."
        category = "LEAVE_RELATED"
        summary = "Family attending wedding function out of station; returning Monday."
        followup_req = False
        closing = f"Samajh gaye {parent_name} ji. Kripya Monday ko HOD office me leave application submit karwa dijiyega. Dhanyavaad."
    elif preset == "WRONG_NUMBER":
        parent_speech = "Aap galat number par call kar rahe hain. Yahan koi is naam ka student nahi rehta."
        category = "WRONG_NUMBER"
        summary = "Wrong number reached; guardian contact verification required."
        followup_req = True
        closing = "Kshama chahte hain, hum college records verify kar lete hain. Aapko pareshan karne ke liye sorry. Namaste."
    else:
        parent_speech = "Ji mera beta to subah time se college ke liye nikla tha! Kya wo class me nahi pahuncha?"
        category = "DISPUTED"
        summary = "Discrepancy: Parent stated student departed for campus on time; attendance disputed."
        followup_req = True
        closing = f"Theek hai {parent_name} ji, hum attendance coordinator aur proctor team ko verify karne ke liye alert kar rahe hain. Dhanyavaad."

    turns.append({"speaker": "PARENT", "text": parent_speech, "confidence": 0.95})
    turns.append({"speaker": "AGENT", "text": closing, "confidence": 0.98})

    payload = CallCompletionPayload(
        provider_call_id=attempt.provider_call_id or f"demo-{attempt.id}",
        attempt_id=attempt.id,
        status="COMPLETED",
        duration_seconds=24,
        language="hi-IN",
        turns=[
            TranscriptTurnPayload(speaker=t["speaker"], text=t["text"], confidence=t["confidence"], sequence_number=i)
            for i, t in enumerate(turns, start=1)
        ],
        analysis=CallAnalysisPayload(
            category=category,
            summary=summary,
            followup_required=followup_req,
            callback_at=datetime.now(timezone.utc) + timedelta(days=1) if preset == "CALLBACK_REQUESTED" else None,
            model_name="openai/gpt-oss-20b (via Groq Simulation)",
            sentiment="cooperative" if not followup_req else "neutral",
        ),
        is_demo=True,
    )

    return process_call_webhook_completion(db, payload)
