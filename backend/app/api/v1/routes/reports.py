from datetime import date, timedelta
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.dependencies import get_db
from app.models.ai_analysis import AIAnalysis
from app.models.attendance import AttendanceRecord
from app.models.call_attempt import CallAttempt
from app.models.class_model import ClassModel
from app.models.followup import Followup
from app.models.student import Student
from app.models.user import User
from app.models.authorization import user_scopes

router = APIRouter(
    prefix="/reports",
    tags=["Reports & Analytics"],
)


@router.get("/summary")
def get_reports_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports.read")),
) -> dict[str, Any]:
    """Provide real reporting aggregations across classes, absences, calls, and categories."""
    # 1. Attendance breakdown by class
    class_query = select(ClassModel).where(ClassModel.is_active.is_(True))
    if current_user.role != "SUPER_ADMIN":
        class_query = class_query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)
    classes = db.execute(class_query).scalars().all()

    class_stats = []
    for c in classes:
        student_count = db.scalar(
            select(func.count(Student.id)).where(
                Student.class_id == c.id, Student.is_active.is_(True)
            )
        ) or 0

        # Absence count in last 30 days
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_absences = db.scalar(
            select(func.count(AttendanceRecord.id))
            .join(Student, Student.id == AttendanceRecord.student_id)
            .where(
                Student.class_id == c.id,
                AttendanceRecord.attendance_date >= thirty_days_ago,
                AttendanceRecord.status == "ABSENT",
            )
        ) or 0

        class_stats.append(
            {
                "class_id": str(c.id),
                "name": f"{c.course_name} {c.section} (Yr {c.year})",
                "students": student_count,
                "recent_absences": recent_absences,
            }
        )

    # 2. Daily absence trends (last 7 days)
    daily_trends = []
    for day_offset in range(6, -1, -1):
        target_date = date.today() - timedelta(days=day_offset)
        att_query = select(
            func.count(AttendanceRecord.id)
        ).join(Student, Student.id == AttendanceRecord.student_id).join(
            ClassModel, ClassModel.id == Student.class_id
        ).where(
            AttendanceRecord.attendance_date == target_date,
            AttendanceRecord.status == "ABSENT",
        )
        if current_user.role != "SUPER_ADMIN":
            att_query = att_query.join(
                user_scopes,
                user_scopes.c.scope_id == ClassModel.scope_id,
            ).where(user_scopes.c.user_id == current_user.id)

        absent_count = db.scalar(att_query) or 0
        daily_trends.append(
            {
                "date": target_date.strftime("%d %b"),
                "date_full": str(target_date),
                "absent_count": absent_count,
            }
        )

    # 3. Call outcomes breakdown
    call_query = select(CallAttempt.status, func.count(CallAttempt.id)).group_by(CallAttempt.status)
    call_rows = db.execute(call_query).all()
    call_outcomes = {status_name: count for status_name, count in call_rows}

    # 4. Response category breakdown from AI analysis
    category_query = select(AIAnalysis.category, func.count(AIAnalysis.id)).group_by(AIAnalysis.category)
    category_rows = db.execute(category_query).all()
    response_categories = {cat: count for cat, count in category_rows}

    # 5. Follow-up status breakdown
    followup_query = select(Followup.status, func.count(Followup.id)).group_by(Followup.status)
    followup_rows = db.execute(followup_query).all()
    followup_statuses = {st: count for st, count in followup_rows}

    return {
        "classes": class_stats,
        "daily_trends": daily_trends,
        "call_outcomes": call_outcomes,
        "response_categories": response_categories,
        "followup_statuses": followup_statuses,
    }
