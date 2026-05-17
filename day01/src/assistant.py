"""Day 1: tool-calling assistant (OpenAI, Anthropic, or mock)."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from day01.src.tools import OPENAI_TOOLS, dispatch_tool

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SYSTEM = """You are a data warehouse assistant. Answer questions using tools only.
Rules:
- Call list_tables or describe_table before writing SQL if schema is unclear.
- Use run_readonly_query for data; never invent numbers.
- Prefer small, correct SELECTs.
- Summarize results clearly for a data engineer audience."""


def _mock_tool_loop(question: str) -> str:
    """Deterministic demo without API keys."""
    q = question.lower()
    if "how many" in q and "order" in q:
        raw = dispatch_tool("run_readonly_query", {"sql": "SELECT COUNT(*) AS n FROM orders"})
        return f"[mock] Tool trace: run_readonly_query -> {raw}\n\nThere are 7 orders in the sample warehouse."
    if "revenue" in q or "amount" in q:
        raw = dispatch_tool(
            "run_readonly_query",
            {
                "sql": """
                SELECT r.region_name, SUM(o.amount_usd) AS revenue
                FROM orders o
                JOIN regions r ON o.region_id = r.region_id
                WHERE o.status = 'completed'
                GROUP BY 1
                ORDER BY 2 DESC
                """
            },
        )
        return f"[mock] Tool trace: run_readonly_query -> {raw}\n\nSee grouped revenue by region above."
    tables = dispatch_tool("list_tables", {})
    return f"[mock] Listed tables: {tables}\n\nAsk about order counts, revenue by region, or refunds."


def _openai_loop(question: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for _ in range(8):
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
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
            continue
        return msg.content or ""
    return "Stopped: max tool iterations reached."


def _anthropic_loop(question: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    tools = [
        {
            "name": "list_tables",
            "description": "List warehouse tables",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "describe_table",
            "description": "Schema + sample for a table",
            "input_schema": {
                "type": "object",
                "properties": {"table": {"type": "string", "enum": ["regions", "orders"]}},
                "required": ["table"],
            },
        },
        {
            "name": "run_readonly_query",
            "description": "Run read-only SELECT",
            "input_schema": {
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"],
            },
        },
    ]
    messages: list[dict] = [{"role": "user", "content": question}]
    for _ in range(8):
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM,
            tools=tools,
            messages=messages,
        )
        tool_blocks = [b for b in resp.content if b.type == "tool_use"]
        if tool_blocks:
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in tool_blocks:
                print(f"  -> tool {block.name}({block.input})", file=sys.stderr)
                out = dispatch_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": out,
                    }
                )
            messages.append({"role": "user", "content": tool_results})
            continue
        texts = [b.text for b in resp.content if hasattr(b, "text")]
        return "\n".join(texts)
    return "Stopped: max tool iterations reached."


def main() -> None:
    parser = argparse.ArgumentParser(description="Day 1 warehouse assistant")
    parser.add_argument("question", nargs="+", help="Natural language question")
    parser.add_argument(
        "--provider",
        choices=("openai", "anthropic", "mock"),
        default=os.getenv("LLM_PROVIDER", "openai"),
    )
    args = parser.parse_args()
    question = " ".join(args.question)

    if args.provider == "mock":
        print(_mock_tool_loop(question))
        return
    if args.provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            sys.exit("Set ANTHROPIC_API_KEY in .env")
        print(_anthropic_loop(question))
        return
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY in .env or use --provider mock")
    print(_openai_loop(question))


if __name__ == "__main__":
    main()
