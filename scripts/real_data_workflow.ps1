# Real Google Flights ingest workflow (run in project root PowerShell)
param(
    [int]$MaxDays = 7,
    [switch]$SkipBackground
)

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "=== 1. Stop old background ingest ===" -ForegroundColor Cyan
& "$PSScriptRoot\stop_ingest.ps1"

Write-Host "`n=== 2. Reset database ===" -ForegroundColor Cyan
& "$PSScriptRoot\reset_db.ps1"

Write-Host "`n=== 3. Ensure Playwright browser (once) ===" -ForegroundColor Cyan
& $py -m playwright install chromium

Write-Host "`n=== 4. First real ingest (may take several minutes) ===" -ForegroundColor Cyan
& $py -m flights.ingest --provider google --once --max-days $MaxDays

Write-Host "`nWaiting 60 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

Write-Host "`n=== 5. Second ingest (1 min later) ===" -ForegroundColor Cyan
& $py -m flights.ingest --provider google --once --max-days $MaxDays

Write-Host "`n=== 6. Compare runs ===" -ForegroundColor Cyan
& $py -c "from flights.compare_runs import compare_runs_summary; print(compare_runs_summary('TLV_VIE'))"

if (-not $SkipBackground) {
    Write-Host "`n=== 7. Start background ingest every 30 min (minimized) ===" -ForegroundColor Cyan
    Start-Process -FilePath $py -ArgumentList "-m","flights.ingest","--provider","google","--interval-seconds","1800","--max-days",$MaxDays -WorkingDirectory $root -WindowStyle Minimized
    Write-Host "Background ingest started. Stop with: scripts\stop_ingest.ps1"
}

Write-Host "`nDone. Check DBeaver or: $py -m flights.db stats" -ForegroundColor Green
