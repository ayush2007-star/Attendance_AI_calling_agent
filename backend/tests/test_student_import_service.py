from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.services import student_import_service


def test_import_students_saves_student_and_primary_guardian(monkeypatch) -> None:
    class_id = uuid4()
    user = SimpleNamespace(role="SUPER_ADMIN", id=uuid4())
    db = MagicMock()
    db.execute.return_value.scalars.return_value.first.return_value = None
    monkeypatch.setattr(
        student_import_service,
        "get_class",
        lambda *_args: SimpleNamespace(id=class_id, is_active=True),
    )
    content = (
        "Student ID,Roll Number,Name,Parent Name,Parent Phone,Relationship\n"
        "ST-001,1207,Asha Sharma,Anita Sharma,9876543210,Mother\n"
    ).encode()

    result = student_import_service.import_students(
        db,
        "students.csv",
        content,
        class_id,
        user,
    )

    assert result["created_rows"] == 1
    assert result["invalid_rows"] == 0
    assert result["duplicate_rows"] == 0
    assert len(db.add.call_args_list) == 3
    student, parent, link = [call.args[0] for call in db.add.call_args_list]
    assert student.student_code == "ST-001"
    assert student.roll_number == "1207"
    assert student.first_name == "Asha"
    assert student.last_name == "Sharma"
    assert parent.primary_phone == "9876543210"
    assert link.is_primary is True
    assert link.relationship_type == "Mother"
    db.commit.assert_called_once()


def test_import_students_skips_bad_and_existing_rows(monkeypatch) -> None:
    class_id = uuid4()
    user = SimpleNamespace(role="SUPER_ADMIN", id=uuid4())
    db = MagicMock()
    db.execute.return_value.scalars.return_value.first.return_value = uuid4()
    monkeypatch.setattr(
        student_import_service,
        "get_class",
        lambda *_args: SimpleNamespace(id=class_id, is_active=True),
    )
    content = (
        "Roll Number,Name,Parent Name\n"
        "1207,Asha,Anita\n"
        "1208,Ravi,\n"
    ).encode()

    result = student_import_service.import_students(
        db,
        "students.csv",
        content,
        class_id,
        user,
    )

    assert result["created_rows"] == 0
    assert result["invalid_rows"] == 1
    assert result["duplicate_rows"] == 1
    assert len(result["errors"]) == 2
    db.add.assert_not_called()
    db.commit.assert_called_once()
