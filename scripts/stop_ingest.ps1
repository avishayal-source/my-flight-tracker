# Stop background flight ingest (python running flights.ingest)
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'flights\.ingest' } |
    ForEach-Object {
        Write-Host "Stopping PID $($_.ProcessId): $($_.CommandLine)"
        Stop-Process -Id $_.ProcessId -Force
    }
Write-Host "Done. If ingest still runs, close the minimized PowerShell window manually."
