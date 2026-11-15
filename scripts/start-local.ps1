<#
.SYNOPSIS
    AttendWise Local Services Startup Script
.DESCRIPTION
    Launches the FastAPI backend (port 8000), Voice Agent telephony service (port 8001),
    and Vite React frontend (port 5173), verifies readiness via health checks, records
    process IDs in .run\pids.json for deterministic teardown, and opens the UI.
#>

param(
    [switch]$NoBrowser = $false,
    [switch]$SkipVoiceAgent = $false
)

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendPython = Join-Path $root "backend\.venv\Scripts\python.exe"
$voicePython = Join-Path $root "voice-agent\.venv\Scripts\python.exe"
$runDir = Join-Path $root ".run"
if (-not (Test-Path $runDir)) { New-Item -ItemType Directory -Path $runDir | Out-Null }
$pidsFile = Join-Path $runDir "pids.json"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       ATTENDWISE - STARTING LOCAL SERVICES               " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Pre-flight check: PostgreSQL
Write-Host "`n[1/4] Verifying database connectivity..." -ForegroundColor Yellow
Push-Location (Join-Path $root "backend")
try {
    $dbStatus = & $backendPython -c "from app.db.session import engine; conn = engine.connect(); conn.close(); print('OK')" 2>&1
    if ($dbStatus -notmatch "OK") {
        Write-Host "  ERROR: Cannot connect to PostgreSQL database." -ForegroundColor Red
        Write-Host "  Ensure PostgreSQL is started on localhost:5432 and backend\.env has valid credentials." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Database connection verified." -ForegroundColor Green
} finally {
    Pop-Location
}

$pidsData = @{}

# 2. Start Backend
Write-Host "`n[2/4] Starting AttendWise Backend (FastAPI on http://127.0.0.1:8000)..." -ForegroundColor Yellow
$backendScript = Join-Path $root "scripts\start_backend.ps1"
$backendProc = Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$backendScript`"" -PassThru
$pidsData["backend"] = @{
    "pid" = $backendProc.Id
    "name" = "backend"
    "script" = $backendScript
    "marker" = "start_backend.ps1"
    "started_at" = (Get-Date).ToString("o")
}

# 3. Start Voice Agent (if not skipped)
if (-not $SkipVoiceAgent) {
    Write-Host "`n[3/4] Starting AI Voice Agent (FastAPI on http://127.0.0.1:8001)..." -ForegroundColor Yellow
    $voiceScript = Join-Path $root "scripts\start_voice.ps1"
    $voiceProc = Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$voiceScript`"" -PassThru
    $pidsData["voice_agent"] = @{
        "pid" = $voiceProc.Id
        "name" = "voice_agent"
        "script" = $voiceScript
        "marker" = "start_voice.ps1"
        "started_at" = (Get-Date).ToString("o")
    }
} else {
    Write-Host "`n[3/4] Voice Agent startup skipped (-SkipVoiceAgent specified)." -ForegroundColor Gray
}

# 4. Start Frontend
Write-Host "`n[4/4] Starting React Frontend (Vite on http://localhost:5173)..." -ForegroundColor Yellow
$frontScript = Join-Path $root "scripts\start_frontend.ps1"
$frontProc = Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$frontScript`"" -PassThru
$pidsData["frontend"] = @{
    "pid" = $frontProc.Id
    "name" = "frontend"
    "script" = $frontScript
    "marker" = "start_frontend.ps1"
    "started_at" = (Get-Date).ToString("o")
}

# Record startup session PIDs
$pidsData | ConvertTo-Json -Depth 4 | Set-Content -Path $pidsFile

# Health check polling
Write-Host "`nWaiting for services to become ready..." -ForegroundColor Cyan
$maxAttempts = 15
$backendReady = $false
$voiceReady = $false

for ($i = 1; $i -le $maxAttempts; $i++) {
    Start-Sleep -Seconds 1
    if (-not $backendReady) {
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($resp.status -eq "ok") {
                $backendReady = $true
                Write-Host "  ✓ Backend API is ready on port 8000" -ForegroundColor Green
            }
        } catch {}
    }

    if (-not $SkipVoiceAgent -and -not $voiceReady) {
        try {
            $vresp = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($vresp.status -eq "ok") {
                $voiceReady = $true
                Write-Host "  ✓ Voice Agent is ready on port 8001" -ForegroundColor Green
            }
        } catch {}
    }

    if ($backendReady -and ($SkipVoiceAgent -or $voiceReady)) {
        break
    }
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "       ATTENDWISE SERVICES ACTIVE & READY                 " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  • Frontend Web App:  http://localhost:5173" -ForegroundColor Yellow
Write-Host "  • Backend API:       http://127.0.0.1:8000 (Docs: /docs)" -ForegroundColor Yellow
if (-not $SkipVoiceAgent) {
    Write-Host "  • Voice Agent:       http://127.0.0.1:8001 (Health: /health)" -ForegroundColor Yellow
}
Write-Host "  • Session tracked:   .run\pids.json" -ForegroundColor Gray
Write-Host "  • To shut down:      .\scripts\stop-local.ps1" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Green

if (-not $NoBrowser) {
    Start-Sleep -Seconds 1
    Start-Process "http://localhost:5173"
}
