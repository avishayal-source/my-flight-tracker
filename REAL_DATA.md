# Real data ingest (Google Flights)

## One-shot setup + runs (recommended)

From project root in PowerShell:

```powershell
cd C:\Users\Avishay\projects\agents-mcp-intensive
powershell -ExecutionPolicy Bypass -File .\scripts\real_data_workflow.ps1 -MaxDays 7
```

This will: stop old ingest → reset DB → install Chromium → ingest twice (1 min apart) → start 30-min background job.

## Manual steps

### 1. Stop background ingest

```powershell
powershell -File .\scripts\stop_ingest.ps1
```

### 2. Clear database

```powershell
powershell -File .\scripts\reset_db.ps1
```

### 3. Playwright (once per machine)

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

### 4–5. Two ingests, 1 minute apart

```powershell
.\.venv\Scripts\python.exe -m flights.ingest --provider google --once --max-days 7
Start-Sleep -Seconds 60
.\.venv\Scripts\python.exe -m flights.ingest --provider google --once --max-days 7
```

Start with `--max-days 3` if you want a quicker test (6 Google searches).

**Skip near-term dates** (often flaky UI / few directs): first scrape **3 departures starting 3 days from today**:

```powershell
.\.venv\Scripts\python.exe -m flights.ingest --provider google --once --max-days 3 --start-offset-days 3 --headful
```

That queries **today+3, today+4, today+5** × TLV↔VIE (6 page loads). Then inspect `data/debug/*.png` if anything skips.

### 6. Background every 30 minutes

```powershell
Start-Process -FilePath "C:\Users\Avishay\projects\agents-mcp-intensive\.venv\Scripts\python.exe" -ArgumentList "-m","flights.ingest","--provider","google","--interval-seconds","1800","--max-days","7" -WorkingDirectory "C:\Users\Avishay\projects\agents-mcp-intensive" -WindowStyle Minimized
```

### 7. Verify price changes

```powershell
.\.venv\Scripts\python.exe -c "from flights.compare_runs import compare_runs_summary; print(compare_runs_summary('TLV_VIE'))"
.\.venv\Scripts\python.exe scripts\compare_runs.py
```

Or in Agent: *"Using flights-tracker, compare_runs for TLV_VIE"*

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Playwright executable missing | `.\.venv\Scripts\python.exe -m playwright install chromium` |
| No offers parsed | Run with visible browser: add `--headful` to ingest |
| Google consent/CAPTCHA | Complete manually in `--headful` window |
| Very slow | Lower `--max-days` (each day = 2 browser searches) |

**Note:** Google may block heavy automation. Use modest `--max-days` and 30-min intervals.
