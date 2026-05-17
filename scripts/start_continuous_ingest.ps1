# Continuous flight ingest: every 30 minutes, 14 departure days starting 3 days from today.
# Run: powershell -ExecutionPolicy Bypass -File .\scripts\start_continuous_ingest.ps1

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"

& $py -m flights.ingest `
  --provider google `
  --interval-seconds 1800 `
  --max-days 14 `
  --start-offset-days 3
