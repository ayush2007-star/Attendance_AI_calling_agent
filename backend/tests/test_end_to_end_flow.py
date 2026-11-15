from datetime import date, datetime, timezone
from uuid import uuid4
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
from app.services.campaign_service import create_campaign
from app.services.calling_service import (
    dispatch_call,
    queue_campaign_target,
    simulate_completed_call,
)
from app.integrations.calling.mock_provider import MockCallingProvider


def test_full_database_driven_calling_lifecycle():
    """
    End-to-End Test:
    Synthetic Student & Guardian in PostgreSQL
    -> Attendance Record (ABSENT)
    -> Campaign creation with dynamic DB targets
    -> Target queueing & contact authorization validation
    -> Call dispatch via Mock Provider
    -> Call completion with transcript, AI classification & follow-up
    -> Database state verification
    """
    db = SessionLocal()
    created_entities = []

    try:
        # 1. Scope and Class
        scope = db.execute(select(Scope)).scalars().first()
        if not scope:
            scope = Scope(id=uuid4(), scope_type="college", scope_value="e2e_college")
            db.add(scope)
            db.flush()
            created_entities.append(scope)

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
        created_entities.append(test_class)

        # 2. Super Admin user for campaign creation
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
            created_entities.append(admin_user)

        # 3. Synthetic Student
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
        created_entities.append(student)

        # 4. Synthetic Guardian
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
        created_entities.append(parent)

        # 5. Link Student and Parent
        student_parent = StudentParent(
            id=uuid4(),
            student_id=student.id,
            parent_id=parent.id,
            relationship_type="Father",
            is_primary=True,
        )
        db.add(student_parent)
        db.flush()
        created_entities.append(student_parent)

        # 6. Mark Student ABSENT for today
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
        created_entities.append(att_record)
        db.commit()

        # 7. Create Call Campaign for today
        campaign_data = CampaignCreate(
            name=f"E2E Absence Campaign {unique_suffix}",
            attendance_date=today,
            class_id=test_class.id,
            threshold=75.0,
        )
        campaign = create_campaign(db, campaign_data, admin_user)
        created_entities.append(campaign)

        assert campaign is not None
        assert campaign.total_targets >= 1

        # 8. Query created target from DB
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

        # 9. Queue Campaign Target -> creates CallAttempt
        attempt = queue_campaign_target(db, target.id, admin_user)
        created_entities.append(attempt)

        assert attempt is not None
        assert attempt.status == "QUEUED"
        assert attempt.phone_number == "+919999988888"
        assert target.status == "QUEUED"

        # 10. Dispatch Call via Mock Provider
        provider = MockCallingProvider()
        dispatched_attempt = dispatch_call(db, attempt.id, provider, admin_user)
        assert dispatched_attempt.status == "RINGING"
        assert target.status == "RINGING"

        # 11. Simulate Parent Response (e.g. MEDICAL_REASON)
        completed_attempt = simulate_completed_call(
            db=db,
            attempt_id=dispatched_attempt.id,
            current_user=admin_user,
            reason_preset="MEDICAL_REASON",
        )
        assert completed_attempt.status == "COMPLETED"
        assert target.status == "COMPLETED"
        assert campaign.completed_calls >= 1

        # 12. Verify Transcript and AI Analysis in DB
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
        assert "fever" in analysis.summary.lower() or "medical" in analysis.summary.lower() or "unwell" in analysis.summary.lower()

    finally:
        # Clean up synthetic test records
        try:
            db.rollback()
            # Clean up in reverse dependency order
            if "attempt" in locals() and attempt.id:
                conv = db.execute(select(Conversation).where(Conversation.call_attempt_id == attempt.id)).scalars().all()
                for c in conv:
                    db.query(AIAnalysis).filter(AIAnalysis.conversation_id == c.id).delete()
                    db.query(Transcript).filter(Transcript.conversation_id == c.id).delete()
                    db.delete(c)
                db.query(Followup).filter(Followup.call_attempt_id == attempt.id).delete()
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
