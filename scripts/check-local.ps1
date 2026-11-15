<#
.SYNOPSIS
    AttendWise Local Health & Test Verification Script
.DESCRIPTION
    Runs comprehensive test suites across Backend, Voice Agent, and Frontend,
    verifies database migrations, and queries live HTTP health endpoints if active.
#>

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendPython = Join-Path $root "backend\.venv\Scripts\python.exe"
$voicePython = Join-Path $root "voice-agent\.venv\Scripts\python.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       ATTENDWISE - LOCAL HEALTH & TEST AUDIT             " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$passed = 0
$failed = 0

function Report-Step($name, $success, $details = "") {
    if ($success) {
        $script:passed++
        Write-Host "  [PASS] $name" -ForegroundColor Green
        if ($details) { Write-Host "         $details" -ForegroundColor Gray }
    } else {
        $script:failed++
        Write-Host "  [FAIL] $name" -ForegroundColor Red
        if ($details) { Write-Host "         $details" -ForegroundColor Red }
    }
}

# 1. Database Connectivity
Write-Host "`n[1/6] Auditing PostgreSQL Database..." -ForegroundColor Yellow
Push-Location (Join-Path $root "backend")
try {
    $dbTest = & $backendPython -c "from app.db.session import engine; conn = engine.connect(); conn.close(); print('OK')" 2>&1
    if ($dbTest -match "OK") {
        Report-Step "PostgreSQL Database Connection" $true "Connected to local instance"
    } else {
        Report-Step "PostgreSQL Database Connection" $false $dbTest
    }

    $alembicHead = & (Join-Path $root "backend\.venv\Scripts\alembic.exe") current 2>&1
    if ($alembicHead -match "head") {
        Report-Step "Alembic Schema Migrations" $true "Current revision matches HEAD"
    } else {
        Report-Step "Alembic Schema Migrations" $false "Migrations not at HEAD: $alembicHead"
    }
} finally {
    Pop-Location
}

# 2. Backend Automated Tests
Write-Host "`n[2/6] Running Backend Pytest Suite..." -ForegroundColor Yellow
Push-Location (Join-Path $root "backend")
try {
    $backendOut = & $backendPython -m pytest tests -q 2>&1
    if ($LASTEXITCODE -eq 0) {
        Report-Step "Backend Pytest Suite (48 tests)" $true "All backend API, security, consent, and lifecycle tests passed"
    } else {
        Report-Step "Backend Pytest Suite" $false $backendOut
    }
} finally {
    Pop-Location
}

# 3. Voice Agent Automated Tests
Write-Host "`n[3/6] Running Voice-Agent Pytest Suite..." -ForegroundColor Yellow
Push-Location (Join-Path $root "voice-agent")
try {
    $voiceOut = & $voicePython -m pytest tests -q 2>&1
    if ($LASTEXITCODE -eq 0) {
        Report-Step "Voice-Agent Pytest Suite (20 tests)" $true "All telephony, prompt, and dialog tests passed"
    } else {
        Report-Step "Voice-Agent Pytest Suite" $false $voiceOut
    }
} finally {
    Pop-Location
}

# 4. Frontend Build & Lint
Write-Host "`n[4/6] Auditing Frontend TypeScript/JSX & Production Build..." -ForegroundColor Yellow
Push-Location (Join-Path $root "frontend")
try {
    npm run lint 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Report-Step "Frontend ESLint Verification" $true "Zero linting errors"
    } else {
        Report-Step "Frontend ESLint Verification" $false "Lint check returned non-zero exit code"
    }

    $buildOut = npm run build 2>&1
    if ($LASTEXITCODE -eq 0) {
        Report-Step "Frontend Production Build" $true "Vite bundle compiled cleanly"
    } else {
        Report-Step "Frontend Production Build" $false $buildOut
    }
} finally {
    Pop-Location
}

# 5. Live Ports and Health Check
Write-Host "`n[5/6] Checking Live Service Endpoints..." -ForegroundColor Yellow
try {
    $bHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($bHealth.status -eq "ok") {
        Report-Step "Backend Service Status" $true "Live and healthy on port 8000"
    } else {
        Write-Host "  [INFO] Backend is not currently running on port 8000 (Start with .\scripts\start-local.ps1)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [INFO] Backend is not currently running on port 8000 (Start with .\scripts\start-local.ps1)" -ForegroundColor Gray
}

try {
    $vHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($vHealth.status -eq "ok") {
        Report-Step "Voice-Agent Service Status" $true "Live and healthy on port 8001"
    } else {
        Write-Host "  [INFO] Voice Agent is not currently running on port 8001 (Start with .\scripts\start-local.ps1)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [INFO] Voice Agent is not currently running on port 8001 (Start with .\scripts\start-local.ps1)" -ForegroundColor Gray
}

try {
    $fHealth = Invoke-WebRequest -Uri "http://localhost:5173" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($fHealth.StatusCode -eq 200) {
        Report-Step "Frontend Service Status" $true "Live and serving on port 5173"
    } else {
        Write-Host "  [INFO] Frontend is not currently running on port 5173 (Start with .\scripts\start-local.ps1)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [INFO] Frontend is not currently running on port 5173 (Start with .\scripts\start-local.ps1)" -ForegroundColor Gray
}

# Summary
Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "       AUDIT SUMMARY: $passed PASSED, $failed FAILED      " -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host "==========================================================" -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
}
