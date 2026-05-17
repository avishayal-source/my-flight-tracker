# Price monitor: run alert check every 15 minutes (no LLM). Exit code 2 = alert (for Task Scheduler).
# Run: powershell -ExecutionPolicy Bypass -File .\scripts\watch_alerts.ps1

param(
    [int]$IntervalSeconds = 900,
    [double]$Threshold = 250,
    [int]$RecentRuns = 3
)

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "Monitoring every $IntervalSeconds s (threshold `$$Threshold, last $RecentRuns runs). Ctrl+C to stop."

while ($true) {
    & $py -m flights.alert_cli --threshold $Threshold --recent-runs $RecentRuns
    if ($LASTEXITCODE -eq 2) {
        Write-Host "ALERT at $(Get-Date -Format o)" -ForegroundColor Yellow
        # Add: Send-MailMessage, webhook, etc.
    }
    Start-Sleep -Seconds $IntervalSeconds
}
