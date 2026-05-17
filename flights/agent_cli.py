"""Step 10: CLI agent over flight DB tools (OpenAI, sparse use)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from flights.agent_tools import OPENAI_TOOLS, dispatch_tool

SYSTEM = """You are a TLV-Vienna flight price assistant.
Rules:
- Answer using tools only; never invent prices or flights.
- Prices are USD totals for 2 economy passengers unless stated.
- For 'did prices change between runs' use compare_runs, then departure_date_price_over_runs for examples.
- compare_runs 'same flight' counts need stable flight numbers across runs (mock ingest does this).
- For booking window (days until departure) use price_vs_days_to_departure.
- Be concise; cite run_id or dates when relevant."""


def ask(question: str) -> str:
    from openai import OpenAI

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY in .env (use MCP tools without LLM if you prefer).")

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for _ in range(10):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            messages.append(msg.model_dump())
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                result = dispatch_tool(tc.function.name, args)
                print(f"  -> tool {tc.function.name}({args})", file=sys.stderr)
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )
            continue
        return msg.content or ""
    return "Stopped: max tool iterations."


def main() -> None:
    parser = argparse.ArgumentParser(description="Flight tracker CLI agent")
    parser.add_argument("question", nargs="+", help="Your question")
    args = parser.parse_args()
    print(ask(" ".join(args.question)))


if __name__ == "__main__":
    main()
