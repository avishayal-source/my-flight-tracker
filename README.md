# TLV ↔ VIE Flight Tracker

Personal bootcamp: **ingest flight prices → DuckDB → analyze → (later) MCP + agent**.

See **[PLAN.md](PLAN.md)** for step-by-step progress.

## Quick start

```powershell
cd C:\Users\Avishay\projects\agents-mcp-intensive
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy config.example.yaml config.yaml
.\.venv\Scripts\python.exe -m flights.db init
.\.venv\Scripts\python.exe -m flights.ingest --provider google --once --max-days 3
.\.venv\Scripts\python.exe -m flights.analyze roundtrip --trip-days 4
```

Offline testing: `--provider mock` instead of `google`.

## Architecture

```
Scheduler (your PC)  →  Google Flights (fast-flights) / mock  →  DuckDB  →  analyze
                                                              ↓
                                                    (later) MCP  →  agent
```

**Providers:** `google` (default, real prices) · `mock` (offline). No API keys for ingest.
