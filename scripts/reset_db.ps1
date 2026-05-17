# Delete warehouse and recreate empty schema
$root = Split-Path $PSScriptRoot -Parent
$db = Join-Path $root "data\flights.duckdb"
if (Test-Path $db) {
    Remove-Item $db -Force
    Write-Host "Removed $db"
}
Set-Location $root
& "$root\.venv\Scripts\python.exe" -m flights.db init
Write-Host "Fresh database ready."
