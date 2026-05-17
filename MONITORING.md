# Monitoring (English)

## Price alerts every 15 minutes (recommended — no PowerShell script policy)

From the project root:

```powershell
cd C:\Users\Avishay\projects\agents-mcp-intensive
.\.venv\Scripts\python.exe -m flights.alert_cli --watch --interval-seconds 900 --threshold 250 --recent-runs 3
```

- **`--watch`** — loop forever.
- **`--interval-seconds 900`** — wait **15 minutes** between checks (900 seconds).
- **`--threshold 250`** — alert if any **one-way leg** (2 pax) is below $250.
- **`--recent-runs 3`** — look at the last 3 ingest runs.

Output lines starting with **`[ALERT]`** mean at least one matching offer exists; **`[OK]`** means none.

One-shot (no loop):

```powershell
.\.venv\Scripts\python.exe -m flights.alert_cli --threshold 250 --recent-runs 3
```

Exit code **2** = alert (useful for Task Scheduler). **0** = no alert.

### Optional: LLM summary after each check

```powershell
.\.venv\Scripts\python.exe -m flights.alert_cli --threshold 250 --recent-runs 3 --agent
```

(No `--watch` in one command; combine with an outer loop if needed.)

---

## PowerShell wrapper (if execution policy allows)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\watch_alerts.ps1
```

Default interval is 900 seconds (15 minutes).

---

## Background minimized window (alerts only)

```powershell
Start-Process -FilePath "C:\Users\Avishay\projects\agents-mcp-intensive\.venv\Scripts\python.exe" `
  -ArgumentList "-m","flights.alert_cli","--watch","--interval-seconds","900","--threshold","250","--recent-runs","3" `
  -WorkingDirectory "C:\Users\Avishay\projects\agents-mcp-intensive" `
  -WindowStyle Minimized
```

---

## Cursor MCP

After **Reload Window**, you can ask:

```text
Using flights-tracker, call offers_below_price with threshold_usd 250.
```
