# Agents & MCP — 4-Day Intensive (32 hours)

> **Step-by-step guide (start here):** [`PLAN.md`](PLAN.md)  
> Update checkboxes there as you progress.

**Pace:** 8 effective hours/day · **Outcome:** Portfolio repo with tool-calling CLI, agent loop, MCP server, evals, demo script.

## What you will have by Day 4

| Artifact | Purpose |
|----------|---------|
| `day01/` | Read-only SQL assistant with tool guardrails |
| `day02/` | Multi-step investigator agent + JSONL traces |
| `day03/mcp_server/` | Warehouse MCP server wired into Cursor |
| `day04/` | Capstone wiring + `evals/golden.yaml` + portfolio README |

---

## Day 1 — Tools, schemas, guardrails (today)

| Block | Hours | Goal | Done |
|-------|-------|------|------|
| 1 | 0:00–2:00 | Mental model + lab setup + seed data | ☐ |
| 2 | 2:00–4:00 | Run assistant; break it; fix guardrails | ☐ |
| 3 | 4:00–6:00 | Add tests + structured JSON responses | ☐ |
| 4 | 6:00–8:00 | Mini-RAG over schema docs; write `day01/LEARNINGS.md` | ☐ |

**Deliverable:** `python -m day01.src.assistant "How many orders last week?"` returns grounded answer.

---

## Day 2 — Agent loop (investigator)

| Block | Hours | Goal |
|-------|-------|------|
| 1 | 0:00–2:00 | ReAct loop: plan → tool → observe → stop |
| 2 | 2:00–4:00 | Simulated pipeline incident data (logs + metadata) |
| 3 | 4:00–6:00 | Max steps, timeouts, trace JSONL |
| 4 | 6:00–8:00 | 3 scripted incidents pass; document failure modes |

**Deliverable:** `python -m day02.src.investigator --incident inc_001` writes `traces/inc_001.jsonl`.

---

## Day 3 — MCP server

| Block | Hours | Goal |
|-------|-------|------|
| 1 | 0:00–2:00 | MCP architecture deep-read + skeleton server |
| 2 | 2:00–4:00 | Tools: `list_tables`, `describe_table`, `run_readonly_query` |
| 3 | 4:00–6:00 | Cursor `mcp.json` + manual tool calls in Agent |
| 4 | 6:00–8:00 | Security doc: allowlist, limits, audit log |

**Deliverable:** Ask Cursor Agent a warehouse question using your MCP server only.

---

## Day 4 — Capstone + job package

| Block | Hours | Goal |
|-------|-------|------|
| 1 | 0:00–2:00 | Combine day02 agent + day03 MCP (or call MCP from agent) |
| 2 | 2:00–4:00 | `evals/golden.yaml` + runner (≥15 cases) |
| 3 | 4:00–6:00 | Root README, architecture diagram, 5-min demo script |
| 4 | 6:00–8:00 | CV bullets + LinkedIn post draft |

**Deliverable:** Public-ready repo + demo checklist in `DEMO.md`.

---

## Daily rhythm (8h)

- **50 min** focus · **10 min** break (×4 blocks)
- Lunch: 45 min between block 2 and 3 (optional)
- End of day: 15 min commit + update checkboxes in this file

## Environment (Windows)

See **`PLAN.md` Step 1** for full instructions.

Quick version (no `Activate.ps1` required):

```powershell
cd C:\Users\Avishay\projects\agents-mcp-intensive
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pytest
copy .env.example .env
.\.venv\Scripts\python.exe scripts\seed_warehouse.py
```

If `Activate.ps1` is blocked: use `.\.venv\Scripts\python.exe` for every command, or run `.\.venv\Scripts\activate.bat`, or `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`.

## API keys

You need **one** provider for Days 1–2:

- `OPENAI_API_KEY` (default, model `gpt-4o-mini`) — or
- `ANTHROPIC_API_KEY` (set `LLM_PROVIDER=anthropic` in `.env`)

Days 1–2 include a **mock mode** (`LLM_PROVIDER=mock`) to run structure without billing.
