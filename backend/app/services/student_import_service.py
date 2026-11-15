import csv
from io import BytesIO, StringIO
from pathlib import Path
import re
from typing import Any
from uuid import UUID
from zipfile import BadZipFile

from fastapi import HTTPException, status
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
import xlrd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.parent import Parent
from app.models.student import Student
from app.models.student_parent import StudentParent
from app.models.user import User
from app.services.class_service import get_class


SUPPORTED_STUDENT_EXTENSIONS = {".xlsx", ".xls", ".csv"}

HEADER_ALIASES = {
    "student_code": {"student id", "student code", "enrollment no", "enrollment number"},
    "roll_number": {"roll no", "roll number", "rollno", "roll"},
    "name": {"name", "student name", "full name"},
    "first_name": {"first name"},
    "last_name": {"last name", "surname"},
    "parent_name": {"parent name", "guardian name", "father name", "mother name"},
    "parent_phone": {"parent phone", "guardian phone", "parent mobile", "guardian mobile", "phone number", "guardian contact number"},
    "relationship": {"relationship", "relation", "guardian relationship"},
}


def import_students(
    db: Session,
    file_name: str,
    content: bytes,
    class_id: UUID,
    uploaded_by: User,
) -> dict[str, Any]:
    selected_class = get_class(db, class_id, uploaded_by)
    if selected_class is None or not selected_class.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected class does not exist or is inactive",
        )

    extension = Path(file_name).suffix.lower()
    if extension not in SUPPORTED_STUDENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Student files must be XLSX, XLS, or CSV",
        )

    try:
        rows = _read_rows(content, extension)
    except (
        BadZipFile,
        InvalidFileException,
        ValueError,
        OSError,
        UnicodeDecodeError,
        xlrd.biffh.XLRDError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read the student file: {error}",
        ) from error

    header_index = _find_header_row(rows)
    if header_index is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Student file needs Roll Number and Name columns",
        )

    headers = [_normalize_header(value) for value in rows[header_index]]
    columns = {
        field: next(
            (index for index, header in enumerate(headers) if header in aliases),
            None,
        )
        for field, aliases in HEADER_ALIASES.items()
    }
    if columns["roll_number"] is None or not (
        columns["name"] is not None or columns["first_name"] is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Student file needs Roll Number and Name (or First Name) columns",
        )

    summary: dict[str, Any] = {
        "total_rows": 0,
        "created_rows": 0,
        "invalid_rows": 0,
        "duplicate_rows": 0,
        "errors": [],
    }
    seen_codes: set[str] = set()
    seen_roll_numbers: set[str] = set()

    for row_number, values in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(_clean_text(value) for value in values):
            continue
        summary["total_rows"] += 1

        roll_number = _cell_text(_get_cell(values, columns["roll_number"]))
        full_name = _cell_text(_get_cell(values, columns["name"]))
        first_name = _cell_text(_get_cell(values, columns["first_name"]))
        last_name = _cell_text(_get_cell(values, columns["last_name"]))
        if not first_name and full_name:
            name_parts = full_name.split(maxsplit=1)
            first_name = name_parts[0]
            last_name = last_name or (name_parts[1] if len(name_parts) > 1 else "")

        raw_code = _cell_text(_get_cell(values, columns["student_code"]))
        student_code = raw_code or f"{class_id.hex[:8]}-{roll_number}"
        parent_name = _cell_text(_get_cell(values, columns["parent_name"]))
        parent_phone = _cell_text(_get_cell(values, columns["parent_phone"]))

        errors: list[str] = []
        duplicate_in_file = False
        if not roll_number:
            errors.append("missing roll number")
        if not first_name:
            errors.append("missing student name")
        if bool(parent_name) != bool(parent_phone):
            errors.append("parent name and phone must both be provided")
        if len(student_code) > 50:
            errors.append("student ID exceeds 50 characters")
        if len(roll_number) > 50:
            errors.append("roll number exceeds 50 characters")
        if len(first_name) > 100 or len(last_name) > 100:
            errors.append("student name exceeds 100 characters")
        if len(parent_name) > 200:
            errors.append("parent name exceeds 200 characters")
        if len(parent_phone) > 30:
            errors.append("parent phone exceeds 30 characters")
        if student_code and student_code in seen_codes:
            duplicate_in_file = True
            errors.append(f"duplicate student ID: {student_code}")
        if roll_number and roll_number in seen_roll_numbers:
            duplicate_in_file = True
            errors.append(f"duplicate roll number in file: {roll_number}")
        if duplicate_in_file:
            summary["duplicate_rows"] += 1

        if student_code:
            seen_codes.add(student_code)
        if roll_number:
            seen_roll_numbers.add(roll_number)

        if errors:
            summary["invalid_rows"] += 1
            summary["errors"].extend(
                f"row {row_number}: {message}" for message in errors
            )
            continue

        existing = db.execute(
            select(Student.id).where(
                (Student.student_code == student_code)
                | (
                    (Student.class_id == class_id)
                    & (Student.roll_number == roll_number)
                )
            )
        ).scalars().first()
        if existing is not None:
            summary["duplicate_rows"] += 1
            summary["errors"].append(
                f"row {row_number}: student ID or roll number already exists"
            )
            continue

        student = Student(
            student_code=student_code,
            roll_number=roll_number,
            first_name=first_name,
            last_name=last_name or None,
            class_id=class_id,
            is_active=True,
        )
        db.add(student)
        if parent_name and parent_phone:
            parent = Parent(
                name=parent_name,
                primary_phone=parent_phone,
            )
            db.add(parent)
            db.add(
                StudentParent(
                    student=student,
                    parent=parent,
                    relationship_type=(
                        _cell_text(_get_cell(values, columns["relationship"]))
                        or "Guardian"
                    ),
                    is_primary=True,
                )
            )
        summary["created_rows"] += 1

    db.commit()
    return summary


def _read_rows(content: bytes, extension: str) -> list[list[Any]]:
    if extension == ".xlsx":
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        try:
            worksheet = workbook.active
            return [list(row) for row in worksheet.iter_rows(values_only=True)]
        finally:
            workbook.close()
    if extension == ".xls":
        workbook = xlrd.open_workbook(file_contents=content)
        sheet = workbook.sheet_by_index(0)
        return [
            sheet.row_values(row_number)
            for row_number in range(sheet.nrows)
        ]
    return [
        list(row)
        for row in csv.reader(StringIO(content.decode("utf-8-sig")))
    ]


def _find_header_row(rows: list[list[Any]]) -> int | None:
    for index, row in enumerate(rows[:20]):
        headers = {_normalize_header(value) for value in row}
        has_roll = bool(headers & HEADER_ALIASES["roll_number"])
        has_name = bool(headers & (HEADER_ALIASES["name"] | HEADER_ALIASES["first_name"]))
        if has_roll and has_name:
            return index
    return None


def _normalize_header(value: Any) -> str:
    text = _clean_text(value).lower()
    return re.sub(r"[\s._-]+", " ", text).strip()


def _cell_text(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return _clean_text(value)


def _clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _get_cell(values: list[Any], index: int | None) -> Any:
    return values[index] if index is not None and index < len(values) else None
