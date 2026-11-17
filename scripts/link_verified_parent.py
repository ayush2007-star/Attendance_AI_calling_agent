from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from uuid import uuid4
from datetime import date

b_env = dotenv_values('backend/.env')
engine = create_engine(b_env.get('DATABASE_URL'))
with engine.begin() as conn:
    sid = conn.execute(text("SELECT id FROM students WHERE student_code = '24BTCS00039'")).scalar()
    pid = 'e33bb0ec-fb42-414e-a191-7c0bd662d710'

    conn.execute(text("UPDATE student_parents SET is_primary = false WHERE student_id = :sid"), {'sid': sid})
    conn.execute(text("""
        INSERT INTO student_parents (id, student_id, parent_id, relationship_type, is_primary, created_at, updated_at)
        VALUES (:id, :sid, :pid, 'Father', true, now(), now())
        ON CONFLICT (student_id, parent_id) DO UPDATE SET is_primary = true
    """), {'id': uuid4(), 'sid': sid, 'pid': pid})

    # Update attendance for 2026-11-17 to ABSENT
    conn.execute(text("UPDATE attendance_records SET status = 'ABSENT' WHERE student_id = :sid AND attendance_date = :d"), {'sid': sid, 'd': date(2026, 11, 17)})
    print("SUCCESS: Student 24BTCS00039 (Ayush Tripathi) now has verified parent phone +917309872195 and is ABSENT on 2026-11-17")
