$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

& .\.venv\Scripts\python.exe -c "
from app.telephony.settings import get_settings
from app.telephony.store import CallStore
from sqlalchemy import text

s = get_settings()
store = CallStore(s.database_url)
store.initialize()

with store.engine.connect() as conn:
    rows = conn.execute(text('SELECT student_name, response_text, recorded_at FROM parent_call_responses ORDER BY recorded_at DESC LIMIT 10')).fetchall()
    if not rows:
        print('Abhi tak koi response record nahi hua.')
    else:
        print('=== SAVED PARENT RESPONSES ===')
        for r in rows:
            print(f'Student: {r[0]} | Time: {r[2]}')
            print(f'Parent Response: {r[1]}')
            print('-' * 40)
"
