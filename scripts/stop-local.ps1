<#
.SYNOPSIS
    AttendWise Local Services Shutdown Script
.DESCRIPTION
    Terminates processes running on AttendWise ports 8000 (Backend), 8001 (Voice Agent), and 5173 (Frontend).
#>

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       ATTENDWISE - STOPPING LOCAL SERVICES               " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$targetPorts = @(8000, 8001, 5173)
$stoppedAny = $false

foreach ($port in $targetPorts) {
    try {
        $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($connections) {
            $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($procId in $pids) {
                try {
                    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                    if ($proc) {
                        Write-Host "  Stopping $($proc.ProcessName) (PID: $procId) on port $port..." -ForegroundColor Yellow
                        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                        $stoppedAny = $true
                    }
                } catch {
                    Write-Host "  Could not stop process PID $procId : $_" -ForegroundColor Red
                }
            }
            Write-Host "  ✓ Port $port cleared." -ForegroundColor Green
        } else {
            Write-Host "  • Port $port is already idle." -ForegroundColor Gray
        }
    } catch {
        Write-Host "  Notice checking port $port: $_" -ForegroundColor Gray
    }
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "       ALL LOCAL ATTENDWISE SERVICES STOPPED              " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
