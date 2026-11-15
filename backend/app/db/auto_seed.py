import logging
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.authorization import Scope
from app.models.class_model import ClassModel
from app.models.parent import Parent
from app.models.student import Student
from app.models.student_parent import StudentParent
from app.models.attendance import AttendanceRecord
from app.models.attendance_summary import AttendanceSummary
from app.models.attendance_import import AttendanceImportBatch
from app.models.absence import AbsenceEvent
from app.models.user import User

logger = logging.getLogger(__name__)


def auto_seed_database(db: Session) -> None:
    """Seed optional local sample records after an administrator is bootstrapped."""

    # 2. Ensure Scopes exist
    scopes_data = [
        ("college", "default"),
        ("department", "Computer Science & Engineering (CSE)"),
        ("department", "Information Technology (IT)"),
        ("department", "Electronics & Comm. (ECE)"),
        ("department", "Mechanical Engineering (ME)"),
    ]

    scopes_dict: dict[str, Scope] = {}
    for scope_type, scope_value in scopes_data:
        scope = db.execute(
            select(Scope).where(
                Scope.scope_type == scope_type,
                Scope.scope_value == scope_value,
            )
        ).scalars().first()
        if not scope:
            scope = Scope(
                id=uuid4(),
                scope_type=scope_type,
                scope_value=scope_value,
            )
            db.add(scope)
            db.flush()
        scopes_dict[scope_value] = scope

    default_scope = scopes_dict.get("default")
    cse_scope = scopes_dict.get("Computer Science & Engineering (CSE)")

    administrator = db.execute(
        select(User).where(User.role == "SUPER_ADMIN").order_by(User.created_at)
    ).scalars().first()
    if administrator is None:
        db.commit()
        logger.info(
            "Demo departments are ready. Create the first director with "
            "'python -m app.bootstrap_admin' before seeding sample records."
        )
        return

    # 3. Ensure sample classes exist
    cse_class = db.execute(
        select(ClassModel).where(
            ClassModel.course_name == "B.Tech Computer Science",
            ClassModel.section == "A",
        )
    ).scalars().first()

    scope_for_class = cse_scope or default_scope

    if not cse_class and scope_for_class:
        cse_class = ClassModel(
            id=uuid4(),
            course_name="B.Tech Computer Science",
            year=3,
            semester=5,
            section="A",
            academic_year="2026-2027",
            class_teacher_id=None,
            scope_id=scope_for_class.id,
            is_active=True,
        )
        db.add(cse_class)
        db.flush()

    cse_class_b = db.execute(
        select(ClassModel).where(
            ClassModel.course_name == "B.Tech Computer Science",
            ClassModel.section == "B",
        )
    ).scalars().first()

    if not cse_class_b and scope_for_class:
        cse_class_b = ClassModel(
            id=uuid4(),
            course_name="B.Tech Computer Science",
            year=3,
            semester=5,
            section="B",
            academic_year="2026-2027",
            class_teacher_id=None,
            scope_id=scope_for_class.id,
            is_active=True,
        )
        db.add(cse_class_b)
        db.flush()

    # 5. Ensure Students exist with varying attendance profiles
    target_class = cse_class or cse_class_b
    if target_class:
        student_count = db.scalar(
            select(func.count(Student.id)).where(Student.class_id == target_class.id)
        ) or 0

        if student_count < 6:
            demo_students = [
                ("STU-101", "101", "Aarav", "Sharma", "aarav.sharma@college.edu", "+919876543210", "Rajesh Sharma", 92.5),
                ("STU-102", "102", "Diya", "Patel", "diya.patel@college.edu", "+919876543211", "Sunil Patel", 87.0),
                ("STU-103", "103", "Rohan", "Mehta", "rohan.mehta@college.edu", "+919876543212", "Suresh Mehta", 74.0),
                ("STU-104", "104", "Ananya", "Singh", "ananya.singh@college.edu", "+919876543213", "Vikram Singh", 68.5),
                ("STU-105", "105", "Kabir", "Kapoor", "kabir.kapoor@college.edu", "+919876543214", "Deepak Kapoor", 54.0),
                ("STU-106", "106", "Sneha", "Reddy", "sneha.reddy@college.edu", "+919876543215", "Venkat Reddy", 48.0),
                ("STU-107", "107", "Ishaan", "Verma", "ishaan.verma@college.edu", "+919876543216", "Manoj Verma", 81.0),
                ("STU-108", "108", "Priya", "Nair", "priya.nair@college.edu", "+919876543217", "Ravi Nair", 62.0),
            ]

            batch = db.execute(select(AttendanceImportBatch)).scalars().first()
            if not batch:
                batch = AttendanceImportBatch(
                    id=uuid4(),
                    file_name="initial_demo_roster.xlsx",
                    file_type="xlsx",
                    attendance_date=date.today(),
                    class_id=target_class.id,
                    status="SUCCESS",
                    total_rows=len(demo_students),
                    valid_rows=len(demo_students),
                    invalid_rows=0,
                    duplicate_rows=0,
                    uploaded_by=administrator.id,
                )
                db.add(batch)
                db.flush()

            today = date.today()

            for code, roll, fname, lname, email, phone, parent_name, att_pct in demo_students:
                existing_st = db.execute(
                    select(Student).where(Student.student_code == code)
                ).scalars().first()

                if not existing_st:
                    st = Student(
                        id=uuid4(),
                        student_code=code,
                        roll_number=roll,
                        first_name=fname,
                        last_name=lname,
                        email=email,
                        class_id=target_class.id,
                        is_active=True,
                    )
                    db.add(st)
                    db.flush()

                    # Add parent
                    p = Parent(
                        id=uuid4(),
                        name=parent_name,
                        primary_phone=phone,
                        preferred_language="hi",
                        is_active=True,
                    )
                    db.add(p)
                    db.flush()

                    sp = StudentParent(
                        id=uuid4(),
                        student_id=st.id,
                        parent_id=p.id,
                        relationship_type="Father",
                        is_primary=True,
                    )
                    db.add(sp)

                    # Add attendance summary
                    summary = AttendanceSummary(
                        id=uuid4(),
                        student_id=st.id,
                        import_batch_id=batch.id,
                        attendance_percentage=att_pct,
                        period_start=today - timedelta(days=60),
                        period_end=today,
                        source_type="SYSTEM_SEED",
                        calculation_method="PERCENTAGE_METRIC",
                    )
                    db.add(summary)

                    # Add today's attendance record (for terminal display)
                    status = "PRESENT" if att_pct >= 75.0 else ("ABSENT" if att_pct < 60.0 else ("LATE" if roll == "104" else "ABSENT"))
                    att_rec = AttendanceRecord(
                        id=uuid4(),
                        student_id=st.id,
                        attendance_date=today,
                        status=status,
                        source_type="FACULTY_APP",
                        source_reference="Morning Roll Call",
                    )
                    db.add(att_rec)
                    db.flush()

                    if status == "ABSENT":
                        abs_ev = AbsenceEvent(
                            id=uuid4(),
                            student_id=st.id,
                            attendance_record_id=att_rec.id,
                            absence_date=today,
                            status="PENDING",
                            eligible_for_call=True,
                        )
                        db.add(abs_ev)

    db.commit()
    logger.info("Optional local sample attendance data seeded.")


def run_auto_seed() -> None:
    if not settings.auto_seed_demo_data:
        return
    if settings.environment.lower() == "production":
        raise RuntimeError("Demo data seeding is forbidden in production")
    with SessionLocal() as db:
        try:
            auto_seed_database(db)
        except Exception as exc:
            db.rollback()
            logger.error("Auto-seed failed: %s", exc)
