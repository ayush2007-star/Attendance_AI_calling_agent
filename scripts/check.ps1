$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendPython = Join-Path $root "backend\.venv\Scripts\python.exe"
$voicePython = Join-Path $root "voice-agent\.venv\Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
    throw "Backend environment not found. Follow the setup in README.md first."
}
if (-not (Test-Path $voicePython)) {
    throw "Voice-agent environment not found. Follow voice-agent/README.md first."
}

Push-Location (Join-Path $root "backend")
try {
    & $backendPython -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }
    & $backendPython -m compileall -q app migrations
    if ($LASTEXITCODE -ne 0) { throw "Backend syntax check failed." }
}
finally {
    Pop-Location
}

Push-Location (Join-Path $root "voice-agent")
try {
    & $voicePython -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { throw "Voice-agent tests failed." }
    & $voicePython -m compileall -q app migrations
    if ($LASTEXITCODE -ne 0) { throw "Voice-agent syntax check failed." }
}
finally {
    Pop-Location
}

Push-Location (Join-Path $root "frontend")
try {
    npm run lint
    if ($LASTEXITCODE -ne 0) { throw "Frontend lint failed." }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
}
finally {
    Pop-Location
}

Write-Host "All local checks passed."
