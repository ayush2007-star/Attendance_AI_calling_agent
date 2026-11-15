from datetime import date
import re
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.absence import AbsenceEvent
from app.models.attendance import AttendanceRecord
from app.models.attendance_summary import AttendanceSummary
from app.models.class_model import ClassModel
from app.models.parent import Parent
from app.models.student import Student
from app.models.student_parent import StudentParent
from app.models.authorization import (
    Permission,
    role_permissions,
    user_roles,
    user_scopes,
)
from app.models.user import User
from app.services.student_service import get_student

router = APIRouter(prefix="/voice", tags=["AI Voice Agent & Telephony"])


class VoiceCommandRequest(BaseModel):
    command: str
    class_id: str | None = None


class SimulateCallRequest(BaseModel):
    student_id: UUID
    reason_preset: str | None = "MEDICAL_REASON"  # MEDICAL_REASON, WILL_ATTEND, DISPUTED, OUT_OF_STATION


@router.post("/parse-command")
def parse_voice_command(
    req: VoiceCommandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Parse natural voice instructions in Hindi/English and execute immediate attendance action."""
    raw = req.command.strip()
    cmd = raw.lower()

    # 1. Roll marking detection: "roll 105 absent", "mark 102 present", "101 absent"
    match_mark = re.search(r"(?:roll\s*|mark\s*)?(\d{2,4})\s*(present|absent|late|excused)", cmd)
    if match_mark:
        can_mark_attendance = db.execute(
            select(Permission.id)
            .join(
                role_permissions,
                role_permissions.c.permission_id == Permission.id,
            )
            .join(
                user_roles,
                user_roles.c.role_id == role_permissions.c.role_id,
            )
            .where(
                user_roles.c.user_id == current_user.id,
                Permission.name == "attendance.create",
            )
        ).scalar_one_or_none()
        if can_mark_attendance is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to mark attendance",
            )

        roll_num = match_mark.group(1)
        action_status = match_mark.group(2).upper()

        student_query = (
            select(Student)
            .join(ClassModel, ClassModel.id == Student.class_id)
            .where(
                Student.roll_number == roll_num,
                Student.is_active.is_(True),
                ClassModel.is_active.is_(True),
            )
        )
        if current_user.role != "SUPER_ADMIN":
            student_query = student_query.join(
                user_scopes,
                user_scopes.c.scope_id == ClassModel.scope_id,
            ).where(user_scopes.c.user_id == current_user.id)
        if req.class_id:
            try:
                requested_class_id = UUID(req.class_id)
            except ValueError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="class_id must be a valid UUID",
                ) from error
            student_query = student_query.where(
                Student.class_id == requested_class_id
            )
        matching_students = db.scalars(student_query).unique().all()
        student = matching_students[0] if len(matching_students) == 1 else None

        if student:
            today = date.today()
            att_rec = db.execute(
                select(AttendanceRecord).where(
                    AttendanceRecord.student_id == student.id,
                    AttendanceRecord.attendance_date == today,
                )
            ).scalars().first()

            if not att_rec:
                att_rec = AttendanceRecord(
                    id=uuid4(),
                    student_id=student.id,
                    attendance_date=today,
                    status=action_status,
                    source_type="VOICE_AGENT",
                    source_reference=f"Voice Command: {raw}",
                )
                db.add(att_rec)
            else:
                att_rec.status = action_status
                att_rec.source_type = "VOICE_AGENT"
                att_rec.source_reference = f"Voice Command: {raw}"

            if action_status == "ABSENT":
                abs_ev = db.execute(
                    select(AbsenceEvent).where(
                        AbsenceEvent.student_id == student.id,
                        AbsenceEvent.absence_date == today,
                    )
                ).scalars().first()
                if not abs_ev:
                    abs_ev = AbsenceEvent(
                        id=uuid4(),
                        student_id=student.id,
                        attendance_record_id=att_rec.id,
                        absence_date=today,
                        status="PENDING",
                        eligible_for_call=True,
                    )
                    db.add(abs_ev)
                else:
                    abs_ev.status = "PENDING"
                    abs_ev.eligible_for_call = True
            else:
                abs_ev = db.execute(
                    select(AbsenceEvent).where(
                        AbsenceEvent.student_id == student.id,
                        AbsenceEvent.absence_date == today,
                    )
                ).scalar_one_or_none()
                if abs_ev is not None:
                    abs_ev.status = "CANCELLED"
                    abs_ev.eligible_for_call = False

            db.commit()

            spoken_hindi = (
                f"Roll number {roll_num}, {student.first_name} ko successfully {action_status.lower()} mark kar diya gaya hai."
            )
            return {
                "intent": "MARK_ATTENDANCE",
                "success": True,
                "spoken_response": spoken_hindi,
                "details": {
                    "student_name": f"{student.first_name} {student.last_name or ''}".strip(),
                    "roll_number": roll_num,
                    "status": action_status,
                },
            }

        return {
            "intent": "MARK_ATTENDANCE",
            "success": False,
            "spoken_response": (
                f"Roll number {roll_num} ka unique student aapke selected scope me nahi mila. "
                "Class select karein ya record verify karein."
            ),
            "details": {"roll_number": roll_num, "status": action_status},
        }

    # 2. Query low attendance: "kiska attendance 75 se kam hai", "below 75", "low attendance", "absent students"
    if any(k in cmd for k in ["75", "kam", "low", "absent", "risk", "critical"]):
        query_absent_records = (
            "absent" in cmd
            and "75" not in cmd
            and "below" not in cmd
            and "low" not in cmd
        )
        if query_absent_records:
            results_query = (
                select(Student, AttendanceRecord)
                .join(AttendanceRecord, AttendanceRecord.student_id == Student.id)
                .join(ClassModel, ClassModel.id == Student.class_id)
                .where(
                    AttendanceRecord.attendance_date == date.today(),
                    AttendanceRecord.status == "ABSENT",
                    Student.is_active.is_(True),
                    ClassModel.is_active.is_(True),
                )
                .order_by(Student.roll_number)
            )
        else:
            results_query = (
                select(Student, AttendanceSummary)
                .join(AttendanceSummary, AttendanceSummary.student_id == Student.id)
                .join(ClassModel, ClassModel.id == Student.class_id)
                .where(
                    AttendanceSummary.attendance_percentage < 75.0,
                    Student.is_active.is_(True),
                    ClassModel.is_active.is_(True),
                )
                .order_by(AttendanceSummary.attendance_percentage)
            )
        if current_user.role != "SUPER_ADMIN":
            results_query = results_query.join(
                user_scopes,
                user_scopes.c.scope_id == ClassModel.scope_id,
            ).where(user_scopes.c.user_id == current_user.id)
        if req.class_id:
            try:
                requested_class_id = UUID(req.class_id)
            except ValueError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="class_id must be a valid UUID",
                ) from error
            results_query = results_query.where(
                Student.class_id == requested_class_id
            )
        summaries = db.execute(results_query.limit(5)).all()

        count = len(summaries)
        names = [
            f"{student.first_name} "
            + (
                "(absent today)"
                if query_absent_records
                else f"({record.attendance_percentage:.0f}%)"
            )
            for student, record in summaries
        ]
        names_str = ", ".join(names) if names else "Koi student nahi hai"

        spoken_hindi = (
            f"Currently {count} students ka attendance critical hai: {names_str}. "
            "Guardian follow-up review ki ja sakti hai; call preview demo-only hai."
        )
        return {
            "intent": "QUERY_LOW_ATTENDANCE",
            "success": True,
            "spoken_response": spoken_hindi,
            "details": {
                "count": count,
                "students": [
                    {
                        "name": f"{student.first_name} {student.last_name or ''}".strip(),
                        "roll": student.roll_number,
                        "percentage": (
                            None
                            if query_absent_records
                            else float(record.attendance_percentage)
                        ),
                        "status": "ABSENT" if query_absent_records else None,
                    }
                    for student, record in summaries
                ],
            },
        }

    # 3. Default College / Department Summary intent
    students_query = (
        select(func.count(Student.id))
        .join(ClassModel, ClassModel.id == Student.class_id)
        .where(
            Student.is_active.is_(True),
            ClassModel.is_active.is_(True),
        )
    )
    if current_user.role != "SUPER_ADMIN":
        students_query = students_query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)
    if req.class_id:
        try:
            requested_class_id = UUID(req.class_id)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="class_id must be a valid UUID",
            ) from error
        students_query = students_query.where(
            Student.class_id == requested_class_id
        )
    total_students = db.scalar(students_query) or 0
    today = date.today()
    absences_query = (
        select(func.count(AttendanceRecord.id))
        .join(Student, Student.id == AttendanceRecord.student_id)
        .join(ClassModel, ClassModel.id == Student.class_id)
        .where(
            AttendanceRecord.attendance_date == today,
            AttendanceRecord.status == "ABSENT",
            Student.is_active.is_(True),
            ClassModel.is_active.is_(True),
        )
    )
    if current_user.role != "SUPER_ADMIN":
        absences_query = absences_query.join(
            user_scopes,
            user_scopes.c.scope_id == ClassModel.scope_id,
        ).where(user_scopes.c.user_id == current_user.id)
    if req.class_id:
        absences_query = absences_query.where(
            Student.class_id == requested_class_id
        )
    absent_today = db.scalar(absences_query) or 0

    spoken_hindi = (
        f"Namaste {current_user.full_name}. College me total {total_students} students registered hain. "
        f"Aaj ke record me {absent_today} students absent mark hain."
    )
    return {
        "intent": "GENERAL_QUERY",
        "success": True,
        "spoken_response": spoken_hindi,
        "details": {
            "total_students": total_students,
            "absent_today": absent_today,
            "received_command": raw,
        },
    }


@router.post("/simulate-call")
def simulate_voice_call(
    req: SimulateCallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return a synthetic conversation preview without placing or recording a call."""
    student = get_student(db, req.student_id, current_user)
    if not student.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot preview calls for an inactive student",
        )

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

    parent_name = parent_link[1].name if parent_link else "Guardian"
    parent_phone = parent_link[1].primary_phone if parent_link else None

    # Multi-turn conversational script in natural Hindi
    dialogue = [
        {
            "speaker": "AI Voice Agent (Swara)",
            "text": f"Namaste {parent_name} ji! Main College Attendance Cell se bol rahi hoon. {student.first_name} aaj class me upasthit nahi hain. Kya sab kushal mangal hai?",
            "time": "00:03",
        },
    ]

    preset = (req.reason_preset or "MEDICAL_REASON").upper()

    if preset == "MEDICAL_REASON":
        parent_reply = "Haan mam, kal raat se use tezz bukhar tha, isliye aaj college nahi bhej paye. Doctor ko dikhaya hai."
        agent_closing = "Theek hai {parent_name} ji, hum medical leave note kar rahe hain. Unhe aaraam karne dijiye aur college aane par prescription submit kar dijiyega. Jaldi swasth hone ki kamna karte hain."
        category = "MEDICAL_REASON"
        sentiment = "COOPERATIVE"
        outcome_action = "LEAVE_LOGGED"
    elif preset == "WILL_ATTEND":
        parent_reply = "Namaste. Bus miss ho gayi thi isliye late ho gaya, abhi nikal chuka hai, aadhe ghante me college pahunch jayega."
        agent_closing = "Dhanyawad batane ke liye! Jaise hi {student.first_name} campus pahunchenge, class me attend kar lenge. Shubh din!"
        category = "WILL_ATTEND"
        sentiment = "POSITIVE"
        outcome_action = "LATE_EXPECTED"
    elif preset == "OUT_OF_STATION":
        parent_reply = "Family me shaadi function tha gaon me, isliye poori family bahar aayi hui hai. Monday se regular aayega."
        agent_closing = "Samajh gaye {parent_name} ji. Kripya Monday ko HOD office me leave application submit karwa dijiyega taaki attendance shortage na ho. Dhanyawad!"
        category = "LEAVE_RELATED"
        sentiment = "INFORMATIVE"
        outcome_action = "FAMILY_LEAVE_PENDING"
    else:
        parent_reply = "Aap galat number par call kar rahe hain, yahan koi iss naam ka nahi hai."
        agent_closing = "Kshama chahte hain, hum record verify kar lete hain. Dhanyawad."
        category = "WRONG_NUMBER"
        sentiment = "NEUTRAL"
        outcome_action = "CONTACT_VERIFICATION_REQUIRED"

    dialogue.append({"speaker": f"Parent ({parent_name})", "text": parent_reply, "time": "00:09"})
    dialogue.append({"speaker": "AI Voice Agent (Swara)", "text": agent_closing.format(parent_name=parent_name, student=student), "time": "00:16"})

    return {
        "status": "SIMULATED",
        "live_call": False,
        "persisted": False,
        "student": {
            "id": str(student.id),
            "name": f"{student.first_name} {student.last_name or ''}".strip(),
            "roll_number": student.roll_number,
        },
        "parent": {
            "name": parent_name,
            "phone": parent_phone,
        },
        "extracted_intent": {
            "category": category,
            "sentiment": sentiment,
            "action_taken": outcome_action,
            "confidence_score": 0.94,
        },
        "dialogue": dialogue,
        "duration": "22 seconds",
        "voice_persona": "Swara (Hindi Neural Natural)",
        "audio_sample_url": "/voice/recordings/test_hindi_greeting.mp3",
    }
