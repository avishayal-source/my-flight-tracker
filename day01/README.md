# Day 1 — Tool-calling data assistant

## Block 1 checklist (do now)

1. Read `docs/01-mental-model.md` (15 min)
2. Create venv + install deps (see **`PLAN.md` Step 1–3** — no `Activate.ps1` needed)
3. `.\.venv\Scripts\python.exe scripts\seed_warehouse.py`
4. `.\.venv\Scripts\python.exe -m day01.src.assistant --provider mock "How many orders are there?"`
5. Switch to real API in `.env` and ask: *"What was revenue by region last month?"*

## What you're learning

- The model does **not** run SQL safely by itself — you expose **tools** with strict validation.
- Same pattern as Airflow operators: contract in, contract out.

## Files

| File | Role |
|------|------|
| `day01/src/tools.py` | Allowlisted read-only SQL |
| `day01/src/assistant.py` | Tool-calling loop (OpenAI / Anthropic / mock) |
| `data/warehouse.duckdb` | Generated sample warehouse |

## Block 4 stretch

Add 3 questions to `day01/notes/queries.md` that **failed** first, then passed after you tightened prompts or tools.
