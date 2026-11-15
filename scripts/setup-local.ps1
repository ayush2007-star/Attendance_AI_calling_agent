<#
.SYNOPSIS
    AttendWise Local Environment Setup Script
.DESCRIPTION
    Sets up python virtual environments, installs backend, voice-agent, and frontend dependencies,
    initializes environment files, runs database migrations, and bootstraps initial admin user.
#>

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       ATTENDWISE - LOCAL ENVIRONMENT SETUP               " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python and Node
Write-Host "`n[1/6] Checking system tools..." -ForegroundColor Yellow
try {
    $pythonVer = (& python --version 2>&1)
    Write-Host "  Found Python: $pythonVer" -ForegroundColor Green
} catch {
    throw "Python is not installed or not in PATH."
}

try {
    $nodeVer = (& node --version 2>&1)
    $npmVer = (& npm --version 2>&1)
    Write-Host "  Found Node: $nodeVer, NPM: $npmVer" -ForegroundColor Green
} catch {
    throw "Node.js/npm is not installed or not in PATH."
}

# 2. Environment files initialization
Write-Host "`n[2/6] Ensuring environment configuration files exist..." -ForegroundColor Yellow
$backendEnv = Join-Path $root "backend\.env"
$backendEnvEx = Join-Path $root "backend\.env.example"
$voiceEnv = Join-Path $root "voice-agent\.env"
$voiceEnvEx = Join-Path $root "voice-agent\.env.example"
$frontEnv = Join-Path $root "frontend\.env"
$frontEnvEx = Join-Path $root "frontend\.env.example"

# Generate strong random secrets helper
function New-RandomHexKey([int]$length = 32) {
    $bytes = [byte[]]::new($length)
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return -join ($bytes | ForEach-Object { "{0:x2}" -f $_ })
}

$sharedInternalApiKey = New-RandomHexKey 32

if (-not (Test-Path $backendEnv) -and (Test-Path $backendEnvEx)) {
    $jwtSecret = New-RandomHexKey 32
    $content = Get-Content -Raw -Path $backendEnvEx
    $content = $content -replace "JWT_SECRET_KEY=replace-with-a-long-random-secret", "JWT_SECRET_KEY=$jwtSecret"
    $content = $content -replace "VOICE_AGENT_API_KEY=", "VOICE_AGENT_API_KEY=$sharedInternalApiKey"
    $content | Set-Content -Path $backendEnv
    Write-Host "  Created backend\.env with strong random secrets" -ForegroundColor Green
} else {
    Write-Host "  backend\.env preserved (existing credentials untouched)" -ForegroundColor Green
}

if (-not (Test-Path $voiceEnv) -and (Test-Path $voiceEnvEx)) {
    $content = Get-Content -Raw -Path $voiceEnvEx
    $content = $content -replace "CALL_API_KEY=", "CALL_API_KEY=$sharedInternalApiKey"
    $content | Set-Content -Path $voiceEnv
    Write-Host "  Created voice-agent\.env with synchronized internal API key" -ForegroundColor Green
} else {
    Write-Host "  voice-agent\.env preserved (existing credentials untouched)" -ForegroundColor Green
}

if (-not (Test-Path $frontEnv) -and (Test-Path $frontEnvEx)) {
    Copy-Item $frontEnvEx $frontEnv
    Write-Host "  Created frontend\.env from template" -ForegroundColor Green
} else {
    Write-Host "  frontend\.env verified" -ForegroundColor Green
}

# 3. Setup Backend Virtual Environment
Write-Host "`n[3/6] Setting up Backend Python environment..." -ForegroundColor Yellow
$backendVenv = Join-Path $root "backend\.venv"
$backendPython = Join-Path $backendVenv "Scripts\python.exe"
if (-not (Test-Path $backendPython)) {
    Write-Host "  Creating virtual environment in backend\.venv..." -ForegroundColor Gray
    & python -m venv $backendVenv
}
Write-Host "  Installing backend dependencies..." -ForegroundColor Gray
& $backendPython -m pip install --upgrade pip -q
& $backendPython -m pip install -r (Join-Path $root "backend\requirements.txt") -q
Write-Host "  Backend dependencies installed successfully." -ForegroundColor Green

# 4. Setup Voice Agent Virtual Environment
Write-Host "`n[4/6] Setting up Voice Agent Python environment..." -ForegroundColor Yellow
$voiceVenv = Join-Path $root "voice-agent\.venv"
$voicePython = Join-Path $voiceVenv "Scripts\python.exe"
if (-not (Test-Path $voicePython)) {
    Write-Host "  Creating virtual environment in voice-agent\.venv..." -ForegroundColor Gray
    & python -m venv $voiceVenv
}
Write-Host "  Installing voice-agent dependencies..." -ForegroundColor Gray
& $voicePython -m pip install --upgrade pip -q
& $voicePython -m pip install -r (Join-Path $root "voice-agent\requirements.txt") -q
Write-Host "  Voice-agent dependencies installed successfully." -ForegroundColor Green

# 5. Setup Frontend Dependencies
Write-Host "`n[5/6] Setting up Frontend dependencies..." -ForegroundColor Yellow
Push-Location (Join-Path $root "frontend")
try {
    Write-Host "  Installing npm packages..." -ForegroundColor Gray
    npm install --silent
    Write-Host "  Frontend dependencies installed successfully." -ForegroundColor Green
} finally {
    Pop-Location
}

# 6. Database Verification & Migrations
Write-Host "`n[6/6] Connecting to PostgreSQL and applying migrations..." -ForegroundColor Yellow
Push-Location (Join-Path $root "backend")
try {
    $dbCheck = & $backendPython -c "from app.db.session import engine; conn = engine.connect(); conn.close(); print('CONNECTED')" 2>&1
    if ($dbCheck -notmatch "CONNECTED") {
        Write-Host "  WARNING: Could not connect to PostgreSQL database." -ForegroundColor Red
        Write-Host "  Please ensure PostgreSQL is running locally and credentials in backend\.env are correct." -ForegroundColor Red
    } else {
        Write-Host "  PostgreSQL connected successfully." -ForegroundColor Green
        Write-Host "  Running Alembic database migrations..." -ForegroundColor Gray
        & $backendVenv\Scripts\alembic.exe upgrade head
        Write-Host "  Database migrations applied to HEAD." -ForegroundColor Green

        # Bootstrap admin user if needed
        Write-Host "  Checking admin user..." -ForegroundColor Gray
        & $backendPython -m app.bootstrap_admin
    }
} finally {
    Pop-Location
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "       ATTENDWISE SETUP COMPLETED SUCCESSFULLY!           " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Next step: Run '.\scripts\start-local.ps1' to launch all services." -ForegroundColor White
