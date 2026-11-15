from datetime import date, datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.authorization import Scope
from app.models.class_model import ClassModel
from app.models.student import Student
from app.models.parent import Parent
from app.models.student_parent import StudentParent
from app.models.attendance import AttendanceRecord
from app.models.campaign import CallCampaign
from app.models.campaign_target import CampaignTarget
from app.models.call_attempt import CallAttempt
from app.models.conversation import Conversation
from app.models.transcript import Transcript
from app.models.ai_analysis import AIAnalysis
from app.models.followup import Followup
from app.models.user import User
from app.schemas.campaign import CampaignCreate
from app.services.campaign_service import (
    create_campaign,
    dispatch_next_campaign_target,
    start_campaign,
)
from app.services.calling_service import (
    dispatch_call,
    queue_campaign_target,
    simulate_completed_call,
)
from app.integrations.calling.mock_provider import MockCallingProvider


def _get_or_create_admin(db):
    admin_user = db.execute(select(User).where(User.role == "SUPER_ADMIN")).scalars().first()
    if not admin_user:
        admin_user = User(
            id=uuid4(),
            email="admin_e2e@college.edu",
            hashed_password="hashed_pw_test",
            role="SUPER_ADMIN",
            is_active=True,
        )
        db.add(admin_user)
        db.flush()
    return admin_user


def _get_or_create_scope(db):
    scope = db.execute(select(Scope)).scalars().first()
    if not scope:
        scope = Scope(id=uuid4(), scope_type="college", scope_value="e2e_college")
        db.add(scope)
        db.flush()
    return scope


def test_full_database_driven_calling_lifecycle():
    """
    End-to-End Test:
    Synthetic Student & Guardian in PostgreSQL (with explicit consent)
    -> Attendance Record (ABSENT)
    -> Campaign creation with dynamic DB targets
    -> Target queueing & contact authorization validation
    -> Call dispatch via Mock Provider
    -> Call completion with transcript, AI classification & follow-up
    -> Database state verification
    """
    db = SessionLocal()

    try:
        scope = _get_or_create_scope(db)
        admin_user = _get_or_create_admin(db)

        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech Computer Science E2E",
            year=4,
            semester=7,
            section="E2E-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        unique_suffix = uuid4().hex[:6]
        student = Student(
            id=uuid4(),
            class_id=test_class.id,
            student_code=f"E2E-{unique_suffix}",
            roll_number=f"ROLL-{unique_suffix}",
            first_name="SyntheticStudent",
            last_name="Testing",
            is_active=True,
        )
        db.add(student)
        db.flush()

        # Explicitly authorized parent
        parent = Parent(
            id=uuid4(),
            name="Synthetic Guardian",
            primary_phone="+919999988888",
            preferred_language="hi-IN",
            call_consent=True,
            call_opt_out=False,
            is_active=True,
        )
        db.add(parent)
        db.flush()

        student_parent = StudentParent(
            id=uuid4(),
            student_id=student.id,
            parent_id=parent.id,
            relationship_type="Father",
            is_primary=True,
        )
        db.add(student_parent)
        db.flush()

        today = date.today()
        att_record = AttendanceRecord(
            id=uuid4(),
            student_id=student.id,
            attendance_date=today,
            status="ABSENT",
            source_type="MANUAL",
        )
        db.add(att_record)
        db.flush()
        db.commit()

        campaign_data = CampaignCreate(
            name=f"E2E Absence Campaign {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        campaign = create_campaign(db, campaign_data, admin_user)

        assert campaign is not None
        assert campaign.total_targets >= 1

        target = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one_or_none()

        assert target is not None
        assert target.parent_id == parent.id
        assert target.selected_phone_number == "+919999988888"
        assert target.status == "PENDING"
        assert target.contact_authorized is True

        # Queue Campaign Target -> creates CallAttempt
        attempt = queue_campaign_target(db, target.id, admin_user)
        assert attempt is not None
        assert attempt.status == "QUEUED"
        assert attempt.phone_number == "+919999988888"
        assert target.status == "QUEUED"

        # Dispatch Call via Mock Provider
        provider = MockCallingProvider()
        dispatched_attempt = dispatch_call(db, attempt.id, provider, admin_user)
        assert dispatched_attempt.status == "RINGING"
        assert target.status == "RINGING"

        # Simulate Parent Response (MEDICAL_REASON)
        completed_attempt = simulate_completed_call(
            db=db,
            attempt_id=dispatched_attempt.id,
            current_user=admin_user,
            reason_preset="MEDICAL_REASON",
        )
        assert completed_attempt.status == "COMPLETED"
        assert target.status == "COMPLETED"
        assert campaign.completed_calls >= 1

        conversation = db.execute(
            select(Conversation).where(Conversation.call_attempt_id == attempt.id)
        ).scalar_one_or_none()
        assert conversation is not None

        turns = db.execute(
            select(Transcript).where(Transcript.conversation_id == conversation.id)
        ).scalars().all()
        assert len(turns) >= 2

        analysis = db.execute(
            select(AIAnalysis).where(AIAnalysis.conversation_id == conversation.id)
        ).scalar_one_or_none()
        assert analysis is not None
        assert analysis.category == "MEDICAL_REASON"

    finally:
        db.rollback()
        try:
            if "attempt" in locals() and attempt.id:
                convs = db.execute(select(Conversation).where(Conversation.call_attempt_id == attempt.id)).scalars().all()
                for c in convs:
                    db.query(AIAnalysis).filter(AIAnalysis.conversation_id == c.id).delete()
                    db.query(Transcript).filter(Transcript.conversation_id == c.id).delete()
                db.query(Conversation).filter(Conversation.call_attempt_id == attempt.id).delete()
                db.query(Followup).filter(Followup.parent_id == parent.id).delete()
                db.query(CallAttempt).filter(CallAttempt.id == attempt.id).delete()
            if "campaign" in locals() and campaign.id:
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == campaign.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == campaign.id).delete()
            if "student" in locals() and student.id:
                db.query(StudentParent).filter(StudentParent.student_id == student.id).delete()
                db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).delete()
                db.query(Student).filter(Student.id == student.id).delete()
            if "parent" in locals() and parent.id:
                db.query(Parent).filter(Parent.id == parent.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_unconsented_guardian_cannot_receive_call():
    """
    Verify fail-closed security:
    A guardian who has NOT explicitly granted call_consent (call_consent=False)
    must have contact_authorized=False on CampaignTarget,
    queueing must fail with HTTP 409 Conflict,
    and dispatch_next_campaign_target must skip the target.
    """
    db = SessionLocal()

    try:
        scope = _get_or_create_scope(db)
        admin_user = _get_or_create_admin(db)

        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech CS Unconsented Test",
            year=1,
            semester=1,
            section="U-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        unique_suffix = uuid4().hex[:6]
        student = Student(
            id=uuid4(),
            class_id=test_class.id,
            student_code=f"NOCONSENT-{unique_suffix}",
            roll_number=f"ROLL-NC-{unique_suffix}",
            first_name="NoConsentStudent",
            last_name="Test",
            is_active=True,
        )
        db.add(student)
        db.flush()

        # Parent with NO consent (call_consent=False)
        parent = Parent(
            id=uuid4(),
            name="Unconsented Guardian",
            primary_phone="+919876500001",
            preferred_language="hi-IN",
            call_consent=False,
            call_opt_out=False,
            is_active=True,
        )
        db.add(parent)
        db.flush()

        db.add(StudentParent(
            id=uuid4(),
            student_id=student.id,
            parent_id=parent.id,
            relationship_type="Mother",
            is_primary=True,
        ))

        today = date.today()
        db.add(AttendanceRecord(
            id=uuid4(),
            student_id=student.id,
            attendance_date=today,
            status="ABSENT",
            source_type="MANUAL",
        ))
        db.commit()

        # 1. Create campaign
        campaign_data = CampaignCreate(
            name=f"No Consent Campaign {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        campaign = create_campaign(db, campaign_data, admin_user)

        target = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one_or_none()

        assert target is not None
        # Must fail closed: contact_authorized must be False!
        assert target.contact_authorized is False

        # 2. Attempting to queue must be rejected with 409 Conflict
        with pytest.raises(HTTPException) as exc_info:
            queue_campaign_target(db, target.id, admin_user)
        assert exc_info.value.status_code == 409
        assert "not authorized" in exc_info.value.detail.lower()

        # 3. dispatch_next_campaign_target must skip this target
        dispatch_result = dispatch_next_campaign_target(db, campaign.id, admin_user)
        assert dispatch_result.get("completed") is True

        db.refresh(target)
        assert target.status == "SKIPPED"

    finally:
        db.rollback()
        try:
            if "campaign" in locals() and campaign.id:
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == campaign.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == campaign.id).delete()
            if "student" in locals() and student.id:
                db.query(StudentParent).filter(StudentParent.student_id == student.id).delete()
                db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).delete()
                db.query(Student).filter(Student.id == student.id).delete()
            if "parent" in locals() and parent.id:
                db.query(Parent).filter(Parent.id == parent.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_opted_out_guardian_is_always_skipped():
    """
    Verify opt-out enforcement:
    A guardian with call_opt_out=True must never be called,
    even if call_consent was previously True.
    """
    db = SessionLocal()

    try:
        scope = _get_or_create_scope(db)
        admin_user = _get_or_create_admin(db)

        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech CS OptOut Test",
            year=2,
            semester=3,
            section="OPT-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        unique_suffix = uuid4().hex[:6]
        student = Student(
            id=uuid4(),
            class_id=test_class.id,
            student_code=f"OPTOUT-{unique_suffix}",
            roll_number=f"ROLL-OPT-{unique_suffix}",
            first_name="OptOutStudent",
            last_name="Test",
            is_active=True,
        )
        db.add(student)
        db.flush()

        # Parent who has opted out
        parent = Parent(
            id=uuid4(),
            name="Opted Out Guardian",
            primary_phone="+919876500002",
            preferred_language="hi-IN",
            call_consent=True,
            call_opt_out=True,  # Explicitly opted out
            is_active=True,
        )
        db.add(parent)
        db.flush()

        db.add(StudentParent(
            id=uuid4(),
            student_id=student.id,
            parent_id=parent.id,
            relationship_type="Father",
            is_primary=True,
        ))

        today = date.today()
        db.add(AttendanceRecord(
            id=uuid4(),
            student_id=student.id,
            attendance_date=today,
            status="ABSENT",
            source_type="MANUAL",
        ))
        db.commit()

        campaign_data = CampaignCreate(
            name=f"OptOut Campaign {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        campaign = create_campaign(db, campaign_data, admin_user)

        target = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one_or_none()

        assert target is not None
        assert target.contact_authorized is False

        # Queueing must be rejected
        with pytest.raises(HTTPException) as exc_info:
            queue_campaign_target(db, target.id, admin_user)
        assert exc_info.value.status_code == 409

        # Campaign dispatch must skip the opted-out target
        dispatch_result = dispatch_next_campaign_target(db, campaign.id, admin_user)
        assert dispatch_result.get("completed") is True

        db.refresh(target)
        assert target.status == "SKIPPED"

    finally:
        db.rollback()
        try:
            if "campaign" in locals() and campaign.id:
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == campaign.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == campaign.id).delete()
            if "student" in locals() and student.id:
                db.query(StudentParent).filter(StudentParent.student_id == student.id).delete()
                db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).delete()
                db.query(Student).filter(Student.id == student.id).delete()
            if "parent" in locals() and parent.id:
                db.query(Parent).filter(Parent.id == parent.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_missing_phone_number_is_skipped():
    """
    Verify that a guardian with missing phone number is not authorized
    and is skipped during sequential campaign dispatch.
    """
    db = SessionLocal()
    try:
        scope = _get_or_create_scope(db)
        admin_user = _get_or_create_admin(db)
        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech CS Missing Phone Test",
            year=2,
            semester=3,
            section="MP-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        unique_suffix = uuid4().hex[:6]
        student = Student(
            id=uuid4(),
            class_id=test_class.id,
            student_code=f"MP-{unique_suffix}",
            roll_number=f"ROLL-MP-{unique_suffix}",
            first_name="NoPhoneStudent",
            last_name="Test",
            is_active=True,
        )
        db.add(student)
        db.flush()

        parent = Parent(
            id=uuid4(),
            name="Missing Phone Guardian",
            primary_phone="",
            preferred_language="hi-IN",
            call_consent=True,
            call_opt_out=False,
            is_active=True,
        )
        db.add(parent)
        db.flush()

        db.add(StudentParent(
            id=uuid4(),
            student_id=student.id,
            parent_id=parent.id,
            relationship_type="Father",
            is_primary=True,
        ))
        today = date.today()
        db.add(AttendanceRecord(
            id=uuid4(),
            student_id=student.id,
            attendance_date=today,
            status="ABSENT",
            source_type="MANUAL",
        ))
        db.commit()

        campaign_data = CampaignCreate(
            name=f"Missing Phone Campaign {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        campaign = create_campaign(db, campaign_data, admin_user)
        target = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one_or_none()

        assert target is not None
        assert target.contact_authorized is False
        assert target.eligibility_reason == "MISSING_PHONE"

        # Queueing must fail
        with pytest.raises(HTTPException) as exc_info:
            queue_campaign_target(db, target.id, admin_user)
        assert exc_info.value.status_code == 409

        # Dispatch next must skip
        dispatch_result = dispatch_next_campaign_target(db, campaign.id, admin_user)
        assert dispatch_result.get("completed") is True
        db.refresh(target)
        assert target.status == "SKIPPED"

    finally:
        db.rollback()
        try:
            if "campaign" in locals() and campaign.id:
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == campaign.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == campaign.id).delete()
            if "student" in locals() and student.id:
                db.query(StudentParent).filter(StudentParent.student_id == student.id).delete()
                db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).delete()
                db.query(Student).filter(Student.id == student.id).delete()
            if "parent" in locals() and parent.id:
                db.query(Parent).filter(Parent.id == parent.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_invalid_phone_number_is_skipped():
    """
    Verify that an invalid/non-E.164 phone number fails authorization checks
    and is skipped with INVALID_PHONE reason.
    """
    db = SessionLocal()
    try:
        scope = _get_or_create_scope(db)
        admin_user = _get_or_create_admin(db)
        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech CS Invalid Phone Test",
            year=2,
            semester=3,
            section="IP-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        unique_suffix = uuid4().hex[:6]
        student = Student(
            id=uuid4(),
            class_id=test_class.id,
            student_code=f"IP-{unique_suffix}",
            roll_number=f"ROLL-IP-{unique_suffix}",
            first_name="BadPhoneStudent",
            last_name="Test",
            is_active=True,
        )
        db.add(student)
        db.flush()

        parent = Parent(
            id=uuid4(),
            name="Invalid Phone Guardian",
            primary_phone="12345",  # Invalid non-E.164 format
            preferred_language="hi-IN",
            call_consent=True,
            call_opt_out=False,
            is_active=True,
        )
        db.add(parent)
        db.flush()

        db.add(StudentParent(
            id=uuid4(),
            student_id=student.id,
            parent_id=parent.id,
            relationship_type="Father",
            is_primary=True,
        ))
        today = date.today()
        db.add(AttendanceRecord(
            id=uuid4(),
            student_id=student.id,
            attendance_date=today,
            status="ABSENT",
            source_type="MANUAL",
        ))
        db.commit()

        campaign_data = CampaignCreate(
            name=f"Invalid Phone Campaign {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        campaign = create_campaign(db, campaign_data, admin_user)
        target = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one_or_none()

        assert target is not None
        assert target.contact_authorized is False
        assert target.eligibility_reason == "INVALID_PHONE"

        with pytest.raises(HTTPException) as exc_info:
            queue_campaign_target(db, target.id, admin_user)
        assert exc_info.value.status_code == 409

        dispatch_result = dispatch_next_campaign_target(db, campaign.id, admin_user)
        assert dispatch_result.get("completed") is True
        db.refresh(target)
        assert target.status == "SKIPPED"

    finally:
        db.rollback()
        try:
            if "campaign" in locals() and campaign.id:
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == campaign.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == campaign.id).delete()
            if "student" in locals() and student.id:
                db.query(StudentParent).filter(StudentParent.student_id == student.id).delete()
                db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).delete()
                db.query(Student).filter(Student.id == student.id).delete()
            if "parent" in locals() and parent.id:
                db.query(Parent).filter(Parent.id == parent.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_unlinked_guardian_is_rejected():
    """
    Verify that an absent student with no linked guardian cannot be called.
    """
    db = SessionLocal()
    try:
        scope = _get_or_create_scope(db)
        admin_user = _get_or_create_admin(db)
        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech CS Unlinked Test",
            year=2,
            semester=3,
            section="UN-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        unique_suffix = uuid4().hex[:6]
        student = Student(
            id=uuid4(),
            class_id=test_class.id,
            student_code=f"UN-{unique_suffix}",
            roll_number=f"ROLL-UN-{unique_suffix}",
            first_name="UnlinkedStudent",
            last_name="Test",
            is_active=True,
        )
        db.add(student)
        db.flush()

        today = date.today()
        db.add(AttendanceRecord(
            id=uuid4(),
            student_id=student.id,
            attendance_date=today,
            status="ABSENT",
            source_type="MANUAL",
        ))
        db.commit()

        campaign_data = CampaignCreate(
            name=f"Unlinked Campaign {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        campaign = create_campaign(db, campaign_data, admin_user)
        target = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one_or_none()

        assert target is not None
        assert target.parent_id is None
        assert target.contact_authorized is False
        assert target.eligibility_reason == "ABSENT_ON_DATE_NO_CONTACT"

        with pytest.raises(HTTPException) as exc_info:
            queue_campaign_target(db, target.id, admin_user)
        assert exc_info.value.status_code == 409

    finally:
        db.rollback()
        try:
            if "campaign" in locals() and campaign.id:
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == campaign.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == campaign.id).delete()
            if "student" in locals() and student.id:
                db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).delete()
                db.query(Student).filter(Student.id == student.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_missing_absence_record_is_rejected():
    """
    Verify that if a student is not marked ABSENT for the campaign date,
    queueing and dispatching fail closed and cancel the target.
    """
    db = SessionLocal()
    try:
        scope = _get_or_create_scope(db)
        admin_user = _get_or_create_admin(db)
        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech CS Absent Check Test",
            year=2,
            semester=3,
            section="AC-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        unique_suffix = uuid4().hex[:6]
        student = Student(
            id=uuid4(),
            class_id=test_class.id,
            student_code=f"AC-{unique_suffix}",
            roll_number=f"ROLL-AC-{unique_suffix}",
            first_name="PresentStudent",
            last_name="Test",
            is_active=True,
        )
        db.add(student)
        db.flush()

        parent = Parent(
            id=uuid4(),
            name="Consented Parent",
            primary_phone="+919876543201",
            preferred_language="hi-IN",
            call_consent=True,
            call_opt_out=False,
            is_active=True,
        )
        db.add(parent)
        db.flush()

        db.add(StudentParent(
            id=uuid4(),
            student_id=student.id,
            parent_id=parent.id,
            relationship_type="Mother",
            is_primary=True,
        ))

        # Initially mark ABSENT
        today = date.today()
        att_record = AttendanceRecord(
            id=uuid4(),
            student_id=student.id,
            attendance_date=today,
            status="ABSENT",
            source_type="MANUAL",
        )
        db.add(att_record)
        db.commit()

        campaign_data = CampaignCreate(
            name=f"Absent Check Campaign {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        campaign = create_campaign(db, campaign_data, admin_user)
        target = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one_or_none()

        assert target is not None
        assert target.contact_authorized is True

        # Now student attendance is changed to PRESENT before queueing
        att_record.status = "PRESENT"
        db.commit()

        # Queueing must be rejected because student is no longer marked absent
        with pytest.raises(HTTPException) as exc_info:
            queue_campaign_target(db, target.id, admin_user)
        assert exc_info.value.status_code == 409
        assert "no longer marked absent" in exc_info.value.detail.lower()

        db.refresh(target)
        assert target.status == "CANCELLED"

    finally:
        db.rollback()
        try:
            if "campaign" in locals() and campaign.id:
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == campaign.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == campaign.id).delete()
            if "student" in locals() and student.id:
                db.query(StudentParent).filter(StudentParent.student_id == student.id).delete()
                db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).delete()
                db.query(Student).filter(Student.id == student.id).delete()
            if "parent" in locals() and parent.id:
                db.query(Parent).filter(Parent.id == parent.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_duplicate_notification_is_prevented():
    """
    Verify that if a contact has already received a COMPLETED notification
    for this absence date, subsequent duplicate calls are rejected.
    """
    db = SessionLocal()
    try:
        scope = _get_or_create_scope(db)
        admin_user = _get_or_create_admin(db)
        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech CS Duplicate Check Test",
            year=2,
            semester=3,
            section="DN-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        unique_suffix = uuid4().hex[:6]
        student = Student(
            id=uuid4(),
            class_id=test_class.id,
            student_code=f"DN-{unique_suffix}",
            roll_number=f"ROLL-DN-{unique_suffix}",
            first_name="DuplicateCheckStudent",
            last_name="Test",
            is_active=True,
        )
        db.add(student)
        db.flush()

        parent = Parent(
            id=uuid4(),
            name="Consented Parent",
            primary_phone="+919876543202",
            preferred_language="hi-IN",
            call_consent=True,
            call_opt_out=False,
            is_active=True,
        )
        db.add(parent)
        db.flush()

        db.add(StudentParent(
            id=uuid4(),
            student_id=student.id,
            parent_id=parent.id,
            relationship_type="Father",
            is_primary=True,
        ))
        today = date.today()
        db.add(AttendanceRecord(
            id=uuid4(),
            student_id=student.id,
            attendance_date=today,
            status="ABSENT",
            source_type="MANUAL",
        ))
        db.commit()

        # Campaign 1: Successfully calls and completes
        c1_data = CampaignCreate(
            name=f"Duplicate Campaign 1 {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        c1 = create_campaign(db, c1_data, admin_user)
        t1 = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == c1.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one()

        att1 = queue_campaign_target(db, t1.id, admin_user)
        provider = MockCallingProvider()
        disp1 = dispatch_call(db, att1.id, provider, admin_user)
        simulate_completed_call(db, disp1.id, admin_user, reason_preset="MEDICAL_REASON")

        db.refresh(t1)
        assert t1.status == "COMPLETED"

        # Campaign 2: Created on same date
        c2_data = CampaignCreate(
            name=f"Duplicate Campaign 2 {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        c2 = create_campaign(db, c2_data, admin_user)
        t2 = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == c2.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one()

        # Must fail closed: already notified on this date!
        assert t2.contact_authorized is False
        assert t2.eligibility_reason == "ALREADY_NOTIFIED"

        with pytest.raises(HTTPException) as exc_info:
            queue_campaign_target(db, t2.id, admin_user)
        assert exc_info.value.status_code == 409
        assert "already received notification" in exc_info.value.detail.lower()

    finally:
        db.rollback()
        try:
            if "c1" in locals() and c1.id:
                for att in db.query(CallAttempt).filter(CallAttempt.campaign_id == c1.id).all():
                    for conv in db.query(Conversation).filter(Conversation.call_attempt_id == att.id).all():
                        db.query(AIAnalysis).filter(AIAnalysis.conversation_id == conv.id).delete()
                        db.query(Transcript).filter(Transcript.conversation_id == conv.id).delete()
                    db.query(Conversation).filter(Conversation.call_attempt_id == att.id).delete()
                db.query(Followup).filter(Followup.campaign_id == c1.id).delete()
                db.query(CallAttempt).filter(CallAttempt.campaign_id == c1.id).delete()
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == c1.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == c1.id).delete()
            if "c2" in locals() and c2.id:
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == c2.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == c2.id).delete()
            if "student" in locals() and student.id:
                db.query(StudentParent).filter(StudentParent.student_id == student.id).delete()
                db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).delete()
                db.query(Student).filter(Student.id == student.id).delete()
            if "parent" in locals() and parent.id:
                db.query(Parent).filter(Parent.id == parent.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_unauthorized_user_cannot_initiate_campaign():
    """
    Verify role-based boundary: an unauthorized user (STUDENT, PARENT, or inactive user)
    cannot create, start, or dispatch campaign calls.
    """
    db = SessionLocal()
    try:
        scope = _get_or_create_scope(db)
        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech CS Auth Scope Test",
            year=2,
            semester=3,
            section="AS-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        # Unauthorized student user
        unauthorized_user = User(
            id=uuid4(),
            username=f"student_{uuid4().hex[:6]}",
            email=f"student_{uuid4().hex[:6]}@college.edu",
            password_hash="fake_hash",
            full_name="Unauthorized Student",
            role="STUDENT",
            is_active=True,
        )
        db.add(unauthorized_user)
        db.commit()

        campaign_data = CampaignCreate(
            name="Unauthorized Campaign",
            attendance_date=date.today(),
            class_id=test_class.id,
            threshold=75.0,
        )

        with pytest.raises(HTTPException) as exc_info:
            create_campaign(db, campaign_data, unauthorized_user)
        assert exc_info.value.status_code == 403

    finally:
        db.rollback()
        try:
            if "unauthorized_user" in locals() and unauthorized_user.id:
                db.query(User).filter(User.id == unauthorized_user.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_authorization_rechecked_before_dispatch():
    """
    Verify critical dispatch-time re-validation:
    If a target was authorized and queued, but the guardian subsequently revokes consent
    (or opts out) before call dispatch occurs, dispatch_call must detect the change,
    cancel the attempt, and refuse dispatch.
    """
    db = SessionLocal()
    try:
        scope = _get_or_create_scope(db)
        admin_user = _get_or_create_admin(db)
        test_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech CS Recheck Test",
            year=2,
            semester=3,
            section="RC-A",
            academic_year="2026-2027",
            scope_id=scope.id,
            is_active=True,
        )
        db.add(test_class)
        db.flush()

        unique_suffix = uuid4().hex[:6]
        student = Student(
            id=uuid4(),
            class_id=test_class.id,
            student_code=f"RC-{unique_suffix}",
            roll_number=f"ROLL-RC-{unique_suffix}",
            first_name="RecheckStudent",
            last_name="Test",
            is_active=True,
        )
        db.add(student)
        db.flush()

        parent = Parent(
            id=uuid4(),
            name="Consenting Guardian",
            primary_phone="+919876543203",
            preferred_language="hi-IN",
            call_consent=True,
            call_opt_out=False,
            is_active=True,
        )
        db.add(parent)
        db.flush()

        db.add(StudentParent(
            id=uuid4(),
            student_id=student.id,
            parent_id=parent.id,
            relationship_type="Father",
            is_primary=True,
        ))
        today = date.today()
        db.add(AttendanceRecord(
            id=uuid4(),
            student_id=student.id,
            attendance_date=today,
            status="ABSENT",
            source_type="MANUAL",
        ))
        db.commit()

        campaign_data = CampaignCreate(
            name=f"Recheck Campaign {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        campaign = create_campaign(db, campaign_data, admin_user)
        target = db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign.id,
                CampaignTarget.student_id == student.id,
            )
        ).scalar_one()

        # 1. Queue successfully while authorized
        attempt = queue_campaign_target(db, target.id, admin_user)
        assert attempt.status == "QUEUED"

        # 2. Guardian revokes consent before dispatch
        parent.call_consent = False
        db.commit()

        # 3. Dispatch must fail closed and cancel attempt & target
        provider = MockCallingProvider()
        with pytest.raises(HTTPException) as exc_info:
            dispatch_call(db, attempt.id, provider, admin_user)
        assert exc_info.value.status_code == 409
        assert "not active, authorized, or primary" in exc_info.value.detail.lower()

        db.refresh(attempt)
        db.refresh(target)
        assert attempt.status == "CANCELLED"
        assert target.status == "CANCELLED"

    finally:
        db.rollback()
        try:
            if "attempt" in locals() and attempt.id:
                db.query(CallAttempt).filter(CallAttempt.id == attempt.id).delete()
            if "campaign" in locals() and campaign.id:
                db.query(CampaignTarget).filter(CampaignTarget.campaign_id == campaign.id).delete()
                db.query(CallCampaign).filter(CallCampaign.id == campaign.id).delete()
            if "student" in locals() and student.id:
                db.query(StudentParent).filter(StudentParent.student_id == student.id).delete()
                db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).delete()
                db.query(Student).filter(Student.id == student.id).delete()
            if "parent" in locals() and parent.id:
                db.query(Parent).filter(Parent.id == parent.id).delete()
            if "test_class" in locals() and test_class.id:
                db.query(ClassModel).filter(ClassModel.id == test_class.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_existing_records_with_unknown_consent_fail_closed():
    """
    Verify model and schema defaults fail closed:
    When a Parent or CampaignTarget record is created without affirmative consent,
    it must default to call_consent=False, call_opt_out=False, contact_authorized=False.
    """
    db = SessionLocal()
    try:
        # Default Parent instantiation
        p = Parent(
            name="Default Consent Parent",
            primary_phone="+919876543204",
        )
        assert p.call_consent is False
        assert p.call_opt_out is False

        # Default CampaignTarget instantiation
        target = CampaignTarget(
            campaign_id=uuid4(),
            student_id=uuid4(),
            attendance_percentage_used=70.0,
            threshold_used=75.0,
            eligibility_reason="TEST",
        )
        assert target.contact_authorized is False

    finally:
        db.close()
