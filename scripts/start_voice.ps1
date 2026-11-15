$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location (Join-Path $root "voice-agent")
Write-Host "Starting AttendWise 2026 AI Telephony Voice Agent on http://127.0.0.1:8001 ..." -ForegroundColor Cyan
& ".\run_server.ps1" -Port 8001
