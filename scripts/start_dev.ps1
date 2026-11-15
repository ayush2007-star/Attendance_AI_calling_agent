param(
    [switch]$SkipVoiceAgent = $false
)

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  ATTENDWISE AI 2026 - LAUNCHING LOCAL DEVELOPMENT STACK  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Backend in new window
Start-Process powershell -ArgumentList "-NoExit", "-File", (Join-Path $root "scripts\start_backend.ps1")

# 2. Start Voice Agent in new window
if (-not $SkipVoiceAgent) {
    Start-Sleep -Seconds 1
    Start-Process powershell -ArgumentList "-NoExit", "-File", (Join-Path $root "scripts\start_voice.ps1")
}

# 3. Wait 2 seconds for services to initialize
Start-Sleep -Seconds 2

# 4. Start Frontend in new window
Start-Process powershell -ArgumentList "-NoExit", "-File", (Join-Path $root "scripts\start_frontend.ps1")

# 5. Open Browser
Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

Write-Host "Services running:" -ForegroundColor Green
Write-Host "  • Backend API:      http://127.0.0.1:8000 (Docs: /docs)" -ForegroundColor Yellow
if (-not $SkipVoiceAgent) {
    Write-Host "  • Voice Agent:      http://127.0.0.1:8001 (Health: /health)" -ForegroundColor Yellow
}
Write-Host "  • Web App:          http://localhost:5173" -ForegroundColor Yellow
Write-Host "  • Ready for college demonstration." -ForegroundColor White
