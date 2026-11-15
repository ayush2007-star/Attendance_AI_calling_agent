$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location (Join-Path $root "backend")
Write-Host "Starting AttendWise 2026 FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
