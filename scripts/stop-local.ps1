<#
.SYNOPSIS
    AttendWise Local Services Shutdown Script
.DESCRIPTION
    Safely terminates ONLY project-managed processes that were started by start-local.ps1
    and recorded in .run\pids.json. Verifies PID and command identity before termination.
    Never terminates unrelated applications or unmanaged ports.
#>

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pidsFile = Join-Path $root ".run\pids.json"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       ATTENDWISE - STOPPING PROJECT SERVICES             " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $pidsFile)) {
    Write-Host "  No active project run session found (.run\pids.json does not exist)." -ForegroundColor Yellow
    Write-Host "  No processes were stopped. Unrelated applications were preserved." -ForegroundColor Gray
    exit 0
}

try {
    $pidsJson = Get-Content -Raw -Path $pidsFile | ConvertFrom-Json
} catch {
    Write-Host "  Could not parse .run\pids.json. Removing corrupted file." -ForegroundColor Red
    Remove-Item -Path $pidsFile -Force -ErrorAction SilentlyContinue
    exit 1
}

$allowedProcessNames = @("powershell", "pwsh", "python", "node", "cmd")
$stoppedCount = 0

foreach ($prop in $pidsJson.PSObject.Properties) {
    $serviceKey = $prop.Name
    $entry = $prop.Value
    $targetPid = $entry.pid
    $serviceName = if ($entry.name) { $entry.name } else { $serviceKey }

    if (-not $targetPid) { continue }

    try {
        $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        if ($proc) {
            $pName = $proc.ProcessName.ToLower()
            $cmdLine = ""
            try {
                if ($proc.PSObject.Properties['CommandLine'] -and $proc.CommandLine) {
                    $cmdLine = $proc.CommandLine
                }
            } catch {}
            if (-not $cmdLine -and (Test-Path "/proc/$targetPid/cmdline")) {
                try {
                    $cmdLine = (Get-Content -Raw "/proc/$targetPid/cmdline" -ErrorAction SilentlyContinue) -replace "`0", " "
                } catch {}
            }
            if (-not $cmdLine) {
                try {
                    $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction SilentlyContinue
                    if ($cim -and $cim.CommandLine) { $cmdLine = $cim.CommandLine }
                } catch {}
            }

            # Identity verification: verify process name is an allowed runner AND command line matches expected marker, script, or root
            $isMatchingIdentity = $false
            if ($allowedProcessNames -contains $pName) {
                if ($entry.marker -and $cmdLine -like "*$($entry.marker)*") {
                    $isMatchingIdentity = $true
                } elseif ($entry.script -and $cmdLine -like "*$($entry.script)*") {
                    $isMatchingIdentity = $true
                } elseif (-not $entry.marker -and -not $entry.script) {
                    if ($cmdLine -like "*$root*") {
                        $isMatchingIdentity = $true
                    }
                }
            }

            if ($isMatchingIdentity) {
                # Stop child processes (e.g. uvicorn/python, vite/node) spawned by this wrapper
                try {
                    $children = @()
                    if (Test-Path "/proc") {
                        $childPids = (Get-ChildItem /proc/[0-9]*/stat -ErrorAction SilentlyContinue | ForEach-Object {
                            $stat = Get-Content $_.FullName -ErrorAction SilentlyContinue
                            if ($stat -match "^\d+\s+\([^)]+\)\s+[A-Za-z]\s+$targetPid\s+") {
                                $_.Directory.Name
                            }
                        })
                        foreach ($cpid in $childPids) {
                            $cp = Get-Process -Id $cpid -ErrorAction SilentlyContinue
                            if ($cp) { $children += $cp }
                        }
                    } else {
                        $cimChildren = Get-CimInstance Win32_Process -Filter "ParentProcessId = $targetPid" -ErrorAction SilentlyContinue
                        foreach ($child in $cimChildren) {
                            $cp = Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
                            if ($cp) { $children += $cp }
                        }
                    }
                    foreach ($childProc in $children) {
                        if ($childProc -and ($allowedProcessNames -contains $childProc.ProcessName.ToLower())) {
                            Write-Host "  Stopping child process $($childProc.ProcessName) (PID: $($childProc.Id)) for $serviceName..." -ForegroundColor Gray
                            Stop-Process -Id $childProc.Id -Force -ErrorAction SilentlyContinue
                        }
                    }
                } catch {}

                Write-Host "  Stopping $serviceName (PID: $targetPid, Process: $($proc.ProcessName))..." -ForegroundColor Yellow
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
                Write-Host "  ✓ $serviceName (PID: $targetPid) stopped." -ForegroundColor Green
                $stoppedCount++
            } else {
                Write-Host "  [SAFETY SHIELD] Process PID $targetPid command line '$cmdLine' does not match project service '$serviceName'! Skipped." -ForegroundColor Red
            }
        } else {
            Write-Host "  • $serviceName (PID: $targetPid) has already terminated." -ForegroundColor Gray
        }
    } catch {
        Write-Host "  Notice inspecting PID $targetPid : $_" -ForegroundColor Gray
    }
}

Remove-Item -Path $pidsFile -Force -ErrorAction SilentlyContinue

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "       PROJECT MANAGED SERVICES STOPPED SAFELY ($stoppedCount stopped)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
