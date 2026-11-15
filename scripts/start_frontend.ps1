$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location (Join-Path $root "frontend")
Write-Host "Starting AttendWise 2026 Quantum Frontend on http://localhost:5173 ..." -ForegroundColor Green
npm run dev
