from datetime import date
from io import BytesIO

from openpyxl import Workbook

from app.services.attendance_excel_parser import parse_attendance_workbook


def workbook_bytes(rows: list[list[object]]) -> BytesIO:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(
        [
            "S.No",
            "Roll No / Student ID",
            "Name",
            date(2026, 9, 1),
            date(2026, 9, 2),
            "Tot.(%)",
            "NF",
        ]
    )
    for row in rows:
        worksheet.append(row)

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


def test_parser_preserves_dynamic_dates_and_college_percentage() -> None:
    summary = parse_attendance_workbook(
        workbook_bytes([[1, "ST-001", "Asha", "P", "A", "68.5%", ""]])
    )

    assert summary.valid_rows == 1
    assert summary.invalid_rows == 0
    assert summary.rows[0].college_percentage == 68.5
    assert summary.rows[0].attendance_by_date == {
        date(2026, 9, 1): "P",
        date(2026, 9, 2): "A",
    }


def test_parser_rejects_duplicate_student_and_invalid_percentage() -> None:
    summary = parse_attendance_workbook(
        workbook_bytes(
            [
                [1, "ST-001", "Asha", "P", "A", 101, ""],
                [2, "ST-001", "Asha", "P", "A", 68, ""],
            ]
        )
    )

    assert summary.valid_rows == 0
    assert summary.invalid_rows == 2
    assert summary.duplicate_rows == 1
    assert any("out of range" in error for error in summary.errors)
