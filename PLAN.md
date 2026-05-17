# Flight Tracker Bootcamp — TLV ↔ VIE

**You are here:** Phase 4 → Step 10 (CLI agent)  
**Project:** `C:\Users\Avishay\projects\agents-mcp-intensive`

Track **direct** economy flights for **2 passengers**, **USD**, next **30 calendar days**.  
Ingest on a timer (short interval for debug). Analyze cheapest **N-day** round trips (any airline combo).

| Phase | Focus | Agent/MCP? |
|-------|--------|------------|
| **1** | DB + ingest (mock or **Google Flights**) | No — deterministic pipeline |
| **2** | Analysis CLI (cheapest 3/4/5-day trips) | No — SQL/Python |
| **3** | MCP server over your DB | MCP tools |
| **4** | Natural-language agent (sparse OpenAI) | Agent on tools only |

**Budget note:** Keep LLM for Phase 4. Phases 1–2 cost $0 (Google ingest uses `fast-flights`, no API key).

---

## Your decisions (locked in)

- Airports: **TLV** ↔ **VIE** only  
- Horizon: **30 calendar days** from today  
- Direct only, economy, 2 adults, USD  
- Round trip: **any** outbound + return combination  
- Trip length: parameter **3 / 4 / 5** days (more later)  
- Scheduler: **your PC**; use `--interval-seconds` for debug  
- Alerts: **later**

---

# Phase 1 — Ingest pipeline

## Step 1 — Install + init DB (~15 min)

```powershell
cd C:\Users\Avishay\projects\agents-mcp-intensive
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy config.example.yaml config.yaml
copy .env.example .env
.\.venv\Scripts\python.exe -m flights.db init
```

- [ ] Done

## Step 2 — Mock ingest (no API keys) (~10 min)

```powershell
.\.venv\Scripts\python.exe -m flights.ingest --provider mock --once
.\.venv\Scripts\python.exe -m flights.ingest --provider mock --once
```

Second run appends another snapshot (price history).

- [ ] Done

## Step 3 — Inspect data (~10 min)

```powershell
.\.venv\Scripts\python.exe -m flights.db stats
```

- [ ] Done

## Step 4 — Ingest (mock = working; google = blocked)

**Working (use this):**

```powershell
.\.venv\Scripts\python.exe -m flights.ingest --provider mock --once
```

**Google (`--provider google`):** currently **fails** — `fast-flights` waits for an old page element (`.eQ35Ce`). Not your setup. Real prices = later (custom scraper or another API).

- [x] Mock ingest works (run 6+ in `scrape_runs`)

## Step 5 — Debug scheduler (~10 min)

```powershell
.\.venv\Scripts\python.exe -m flights.ingest --provider mock --interval-seconds 30
```

Ctrl+C after 2–3 runs. Check `flights.db stats` — run count should grow.

- [x] Done

**Phase 1 complete.**

---

# Phase 2 — Analysis (no LLM)

## Step 6 — Cheapest round trip

```powershell
.\.venv\Scripts\python.exe -m flights.analyze roundtrip --trip-days 4
.\.venv\Scripts\python.exe -m flights.analyze roundtrip --trip-days 3 --trip-days 5
```

- [x] Done

## Step 7 — Price vs days-to-departure (stretch)

```powershell
.\.venv\Scripts\python.exe -m flights.analyze trend --direction TLV_VIE
```

- [x] Done

**Phase 2 complete.**

---

# Phase 3 — MCP server

## Step 8 — Run MCP server locally (~30 min)

Tools: `db_stats`, `cheapest_roundtrip`, `price_trend`.

```powershell
.\.venv\Scripts\python.exe -m flights.mcp_server
```

- [ ] Done

## Step 9 — Wire Cursor (~15 min)

Project file `.cursor/mcp.json` points at `scripts/run_flights_mcp.py` (fixes `No module named 'flights'`).

In Cursor: **Settings → MCP** → edit **flights-tracker** to match `.cursor/mcp.json`, then **Reload Window**.

Ask Agent: *"Use flights-tracker: cheapest 4-day TLV-VIE round trip?"*

- [x] Done

**Phase 3 complete.**

---

## Background ingest (while you work — optional)

**30 minutes** (new minimized window):

```powershell
Start-Process -FilePath "C:\Users\Avishay\projects\agents-mcp-intensive\.venv\Scripts\python.exe" -ArgumentList "-m","flights.ingest","--provider","mock","--interval-seconds","1800" -WorkingDirectory "C:\Users\Avishay\projects\agents-mcp-intensive" -WindowStyle Minimized
```

**Debug (30 seconds)** — use in a visible terminal, Ctrl+C to stop:

```powershell
.\.venv\Scripts\python.exe -m flights.ingest --provider mock --interval-seconds 30
```

---

# Phase 4 — Agent (CLI)

## Step 10 — Tool-calling assistant (~30 min)

Set `OPENAI_API_KEY` in `.env`, then:

```powershell
.\.venv\Scripts\python.exe -m flights.agent_cli "What is the cheapest 4-day round trip?"
.\.venv\Scripts\python.exe -m flights.agent_cli "Did prices change between runs for TLV to Vienna?"
```

Watch stderr for `-> tool ...` lines (same tools as MCP).

- [ ] Done

## Step 11 — Portfolio wrap-up (~20 min)

README diagram, demo script, CV bullet.

- [ ] Done

**Bootcamp complete** after Step 11.

---

## Command cheat sheet

| Task | Command |
|------|---------|
| Init DB | `.\.venv\Scripts\python.exe -m flights.db init` |
| Mock once | `.\.venv\Scripts\python.exe -m flights.ingest --provider mock --once` |
| Google once (3 days) | `.\.venv\Scripts\python.exe -m flights.ingest --provider google --once --max-days 3` |
| Poll every 60s | `.\.venv\Scripts\python.exe -m flights.ingest --provider mock --interval-seconds 60` |
| Cheapest 4-day RT | `.\.venv\Scripts\python.exe -m flights.analyze roundtrip --trip-days 4` |
| DB stats | `.\.venv\Scripts\python.exe -m flights.db stats` |

---

## Windows venv

Use `.\.venv\Scripts\python.exe` or `.\.venv\Scripts\activate.bat` (not `Activate.ps1` if blocked).
