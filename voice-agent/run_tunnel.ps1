# Voice Agent Ngrok Tunnel Starter
param(
    [int]$Port = 8001,
    [string]$Domain = ""
)

if ($env:VOICE_PORT) {
    $Port = [int]$env:VOICE_PORT
}

# Resolve ngrok executable: check PATH first, then standard WinGet package paths
$ngrokCmd = Get-Command ngrok -ErrorAction SilentlyContinue
if ($ngrokCmd) {
    $NgrokPath = $ngrokCmd.Source
} else {
    $wingetPaths = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter "ngrok.exe" -Recurse -ErrorAction SilentlyContinue
    if ($wingetPaths.Count -gt 0) {
        $NgrokPath = $wingetPaths[0].FullName
    } else {
        $NgrokPath = "ngrok"
    }
}

# Determine tunnel domain if provided via param, environment, or default
$tunnelDomain = $Domain
if (-not $tunnelDomain -and $env:PUBLIC_TUNNEL_URL) {
    $tunnelDomain = $env:PUBLIC_TUNNEL_URL.Replace("https://", "").Replace("http://", "").TrimEnd("/")
}
if (-not $tunnelDomain) {
    $tunnelDomain = "dexterity-disobey-sloped.ngrok-free.dev"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Ngrok Tunnel on Port $Port" -ForegroundColor Green
Write-Host " Public URL: https://$tunnelDomain" -ForegroundColor Yellow
Write-Host " (Twilio webhook target: https://$tunnelDomain/twiml/{session_id})" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan

if ($tunnelDomain) {
    & $NgrokPath http $Port "--url=$tunnelDomain"
} else {
    & $NgrokPath http $Port
}
