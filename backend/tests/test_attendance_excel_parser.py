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
        date(2026, 9, 1): "PRESENT",
        date(2026, 9, 2): "ABSENT",
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


def test_parser_matches_roll_number_and_yearless_date_headers() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(
        ["S.No", "Roll Number", "Name", "03 Aug", "05 aug", "Tot.(%)", "NF"]
    )
    worksheet.append([1, 1207, "Asha", "P", "A", None, None])
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)

    summary = parse_attendance_workbook(
        stream,
        reference_date=date(2026, 8, 27),
    )

    assert summary.valid_rows == 1
    assert summary.rows[0].student_code == "1207"
    assert summary.rows[0].attendance_by_date == {
        date(2026, 8, 3): "PRESENT",
        date(2026, 8, 5): "ABSENT",
    }
    assert summary.rows[0].college_percentage == 50
    assert (
        summary.rows[0].percentage_calculation_method
        == "DATE_WISE_MARKED_DAYS"
    )


def test_parser_accepts_unpadded_iso_date_header() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Roll Number", "Name", "2026-8-14"])
    worksheet.append(["1207", "Asha", "A"])
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)

    summary = parse_attendance_workbook(stream)

    assert summary.valid_rows == 1
    assert summary.rows[0].attendance_by_date == {
        date(2026, 8, 14): "ABSENT",
    }


def test_parser_rejects_unrecognized_date_status() -> None:
    summary = parse_attendance_workbook(
        workbook_bytes([[1, "ST-001", "Asha", "X", "A", "68.5%", ""]])
    )

    assert summary.valid_rows == 0
    assert summary.invalid_rows == 1
    assert any("invalid attendance status" in error for error in summary.errors)
