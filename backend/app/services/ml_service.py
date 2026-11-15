from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord
from app.models.attendance_summary import AttendanceSummary
from app.models.class_model import ClassModel
from app.models.leave import LeaveRecord
from app.models.parent import Parent
from app.models.student import Student
from app.models.student_parent import StudentParent
from app.models.user import User
from app.models.authorization import user_scopes


def get_student_ml_insights(
    db: Session,
    current_user: User,
    class_id: UUID | None = None,
    risk_tier: str | None = None,
    search_query: str | None = None,
) -> dict[str, Any]:
    """Calculate advisory attendance indicators from recorded data."""
    students_query = (
        select(Student, ClassModel)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .where(
            Student.is_active.is_(True),
            ClassModel.is_active.is_(True),
        )
    )

    if current_user.role != "SUPER_ADMIN":
        # Scoped access for HOD and Staff
        user_scope_ids = select(user_scopes.c.scope_id).where(
            user_scopes.c.user_id == current_user.id
        )
        students_query = students_query.where(ClassModel.scope_id.in_(user_scope_ids))

    if class_id:
        students_query = students_query.where(Student.class_id == class_id)

    if search_query and search_query.strip():
        term = f"%{search_query.strip().lower()}%"
        students_query = students_query.where(
            or_(
                func.lower(Student.first_name).like(term),
                func.lower(Student.last_name).like(term),
                func.lower(Student.roll_number).like(term),
                func.lower(Student.student_code).like(term),
            )
        )

    results = db.execute(students_query).all()

    today = date.today()
    students_data = []

    total_critical = 0
    total_elevated = 0
    total_normal = 0
    total_no_data = 0
    anomaly_count = 0
    attendance_percentages: list[float] = []

    for student, class_obj in results:
        # Fetch latest attendance summary
        summary = db.execute(
            select(AttendanceSummary)
            .where(AttendanceSummary.student_id == student.id)
            .order_by(desc(AttendanceSummary.recorded_at))
        ).scalars().first()

        all_records = db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.attendance_date <= today,
            )
        ).scalars().all()
        approved_leaves = db.execute(
            select(LeaveRecord).where(
                LeaveRecord.student_id == student.id,
                LeaveRecord.status == "APPROVED",
                LeaveRecord.start_date <= today,
            )
        ).scalars().all()
        approved_leave_dates = {
            record.attendance_date
            for record in all_records
            if any(
                leave.start_date <= record.attendance_date <= leave.end_date
                for leave in approved_leaves
            )
        }
        if summary:
            att_pct = float(summary.attendance_percentage)
        else:
            all_marked_records = [
                record
                for record in all_records
                if record.status in {"PRESENT", "ABSENT", "LATE"}
                and record.attendance_date not in approved_leave_dates
            ]
            att_pct = (
                round(
                    sum(record.status in {"PRESENT", "LATE"} for record in all_marked_records)
                    / len(all_marked_records)
                    * 100,
                    2,
                )
                if all_marked_records
                else None
            )

        # Compare recent attendance with the all-time recorded rate.
        recent_records = db.execute(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.attendance_date >= today - timedelta(days=21),
                AttendanceRecord.attendance_date <= today,
            )
            .order_by(desc(AttendanceRecord.attendance_date))
        ).scalars().all()

        marked_recent_records = [
            record
            for record in recent_records
            if record.status in {"PRESENT", "ABSENT", "LATE"}
            and record.attendance_date not in approved_leave_dates
        ]
        absent_count = sum(
            record.status == "ABSENT" for record in marked_recent_records
        )
        recent_pct = (
            (
                len(marked_recent_records) - absent_count
            )
            / len(marked_recent_records)
            * 100.0
            if marked_recent_records
            else None
        )

        # Calculate slope/trend
        trend_slope = (
            round((recent_pct - att_pct) / 21.0, 2)
            if recent_pct is not None and att_pct is not None
            else None
        )

        # Count consecutive absent attendance records from most recent backward.
        consecutive_absent = 0
        for r in recent_records:
            if r.attendance_date in approved_leave_dates:
                break
            if r.status == "ABSENT":
                consecutive_absent += 1
            else:
                break

        leaves_count = len(approved_leaves)

        # Primary Parent
        parent_link = db.execute(
            select(StudentParent, Parent)
            .join(Parent, Parent.id == StudentParent.parent_id)
            .where(
                StudentParent.student_id == student.id,
                StudentParent.is_primary.is_(True),
                Parent.is_active.is_(True),
            )
            .order_by(Parent.created_at)
        ).first()

        parent_info = {
            "name": parent_link[1].name if parent_link else "Parent/Guardian",
            "phone": parent_link[1].primary_phone if parent_link else "N/A",
        }

        # Multi-factor ML Risk Classification
        # Features: attendance %, negative slope, consecutive absents, leaves
        urgency_score = (
            min(
                100.0,
                max(
                    0.0,
                    ((75.0 - att_pct) * 1.5)
                    + (consecutive_absent * 8.0)
                    + (max(0.0, -(trend_slope or 0.0) * 15.0)),
                ),
            )
            if att_pct is not None
            else None
        )

        anomalies: list[dict[str, str]] = []

        if att_pct is None:
            computed_tier = "NO_DATA"
            total_no_data += 1
        elif att_pct < 60.0 or consecutive_absent >= 3 or urgency_score >= 60.0:
            computed_tier = "CRITICAL"
            total_critical += 1
        elif (
            att_pct < 75.0
            or (trend_slope is not None and trend_slope < -0.8)
            or consecutive_absent >= 2
        ):
            computed_tier = "ELEVATED"
            total_elevated += 1
        else:
            computed_tier = "NORMAL"
            total_normal += 1

        # Anomaly Heuristics
        if trend_slope is not None and trend_slope < -0.5:
            anomalies.append({
                "type": "SHARP_DROP",
                "label": "Recent attendance drop",
                "detail": f"Recent attendance is {abs(trend_slope * 21):.1f} percentage points below the cumulative rate",
                "severity": "high",
            })
            anomaly_count += 1

        if consecutive_absent >= 3:
            anomalies.append({
                "type": "STREAK_ABSENT",
                "label": "Recorded absence streak",
                "detail": f"{consecutive_absent} consecutive attendance records are marked absent",
                "severity": "high",
            })
            anomaly_count += 1

        # AI Recommendation
        if computed_tier == "CRITICAL":
            recommendation = (
                "Review attendance and guardian contact, then follow the institution's approved outreach policy."
            )
        elif computed_tier == "ELEVATED":
            recommendation = f"Attendance is {att_pct:.1f}%. Review the record and consider a guardian follow-up."
        elif computed_tier == "NO_DATA":
            recommendation = "No attendance data is available yet; import or record attendance before risk review."
        else:
            recommendation = "No current attendance-risk indicators. Continue routine monitoring."

        student_entry = {
            "id": str(student.id),
            "student_code": student.student_code,
            "roll_number": student.roll_number,
            "full_name": f"{student.first_name} {student.last_name or ''}".strip(),
            "first_name": student.first_name,
            "last_name": student.last_name,
            "email": student.email,
            "class_id": str(class_obj.id),
            "class_name": f"{class_obj.course_name} - {class_obj.section}",
            "academic_year": class_obj.academic_year,
            "semester": class_obj.semester,
            "attendance_percentage": att_pct,
            "trend_slope": trend_slope,
            "consecutive_absent": consecutive_absent,
            "urgency_score": round(urgency_score, 1) if urgency_score is not None else None,
            "risk_tier": computed_tier,
            "anomalies": anomalies,
            "ai_recommendation": recommendation,
            "parent": parent_info,
            "approved_leaves": leaves_count,
        }

        if att_pct is not None:
            attendance_percentages.append(att_pct)
        if risk_tier and risk_tier.upper() != "ALL" and computed_tier != risk_tier.upper():
            continue

        students_data.append(student_entry)

    # Sort students by urgency_score descending
    students_data.sort(
        key=lambda student: student["urgency_score"] or 0,
        reverse=True,
    )

    # High-level institutional metrics
    total_scanned = len(results)
    avg_college_attendance = (
        round(sum(attendance_percentages) / len(attendance_percentages), 1)
        if attendance_percentages
        else None
    )

    return {
        "metrics": {
            "total_students": total_scanned,
            "students_with_attendance": len(attendance_percentages),
            "average_attendance": avg_college_attendance,
            "critical_risk_count": total_critical,
            "elevated_risk_count": total_elevated,
            "normal_risk_count": total_normal,
            "no_attendance_data_count": total_no_data,
            "anomalies_detected": anomaly_count,
        },
        "students": students_data,
        "executive_summary": {
            "director_headline": (
                f"Average recorded attendance: {avg_college_attendance}%. "
                f"{total_critical} students have critical attendance indicators."
                if avg_college_attendance is not None
                else "No attendance records are available for this scope."
            ),
            "action_priority": "High" if total_critical > 0 else "Normal",
            "model_version": "rule-based-v1",
        },
    }
