from datetime import date
from io import BytesIO

from docx import Document

from app.services.attendance_file_parser import parse_attendance_file


def test_parser_accepts_csv() -> None:
    content = (
        "S.No,Roll No / Student ID,Name,2026-09-01,2026-09-02,Tot.(%),NF\n"
        "1,ST-001,Asha,P,A,68.5%,\n"
    ).encode()

    summary = parse_attendance_file(BytesIO(content), "attendance.csv")

    assert summary.valid_rows == 1
    assert summary.rows[0].attendance_by_date == {
        date(2026, 9, 1): "P",
        date(2026, 9, 2): "A",
    }


def test_parser_accepts_docx_table() -> None:
    document = Document()
    table = document.add_table(rows=2, cols=7)
    headers = ["S.No", "Roll No / Student ID", "Name", "2026-09-01", "2026-09-02", "Tot.(%)", "NF"]
    values = ["1", "ST-002", "Ravi", "P", "P", "90", ""]
    for cell, value in zip(table.rows[0].cells, headers):
        cell.text = value
    for cell, value in zip(table.rows[1].cells, values):
        cell.text = value

    content = BytesIO()
    document.save(content)
    content.seek(0)

    summary = parse_attendance_file(content, "attendance.docx")

    assert summary.valid_rows == 1
    assert summary.rows[0].student_code == "ST-002"


def test_parser_rejects_unsupported_extension() -> None:
    try:
        parse_attendance_file(BytesIO(b"data"), "attendance.txt")
    except ValueError as error:
        assert "Supported formats" in str(error)
    else:
        raise AssertionError("unsupported extension should be rejected")