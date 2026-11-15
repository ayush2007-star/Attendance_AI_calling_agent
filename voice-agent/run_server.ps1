# Voice Agent Server Starter
param(
    [int]$Port = 8001
)

if ($env:VOICE_PORT) {
    $Port = [int]$env:VOICE_PORT
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Starting Attendance Voice Agent Server on http://127.0.0.1:$Port..." -ForegroundColor Green
& .\.venv\Scripts\python.exe -m uvicorn app.telephony.server:app --host 127.0.0.1 --port $Port
