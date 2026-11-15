param(
    [Parameter(Mandatory=$true, HelpMessage="Recipient phone number in E.164 format (+91...)")]
    [string]$Phone,
    [Parameter(Mandatory=$true, HelpMessage="Student name")]
    [string]$Student,
    [Parameter(Mandatory=$true, HelpMessage="Parent or guardian name")]
    [string]$Parent,
    [double]$Percentage = 65.0
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Today = (Get-Date).ToString("yyyy-MM-dd")

Write-Host "Placing Voice Call to $Parent ($Phone) for Student $Student (Attendance: $Percentage%)..." -ForegroundColor Yellow

$callArgs = @(
    "app/telephony/trigger_call.py",
    "--campaign-target-id", [guid]::NewGuid().ToString(),
    "--student-id", [guid]::NewGuid().ToString(),
    "--student-name", $Student,
    "--parent-name", $Parent,
    "--phone-number", $Phone,
    "--attendance-date", $Today,
    "--preferred-language", "hi-IN",
    "--attendance-percentage", $Percentage,
    "--parent-contact-authorized"
)

& .\.venv\Scripts\python.exe @callArgs
