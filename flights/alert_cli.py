"""CLI: price alerts (deterministic) or optional LLM summary."""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from flights.alerts import offers_below_price, offers_below_price_latest_across_runs


def main() -> None:
    p = argparse.ArgumentParser(description="Price alerts TLV/VIE")
    p.add_argument(
        "--threshold", type=float, default=250.0, help="USD per one-way leg (2 pax)"
    )
    p.add_argument("--run-id", type=int, default=None)
    p.add_argument(
        "--recent-runs",
        type=int,
        default=0,
        help="If >0, scan last N runs for sub-threshold offers",
    )
    p.add_argument(
        "--agent",
        action="store_true",
        help="Use OpenAI to summarize (needs OPENAI_API_KEY)",
    )
    p.add_argument(
        "--watch",
        action="store_true",
        help="Run forever: check, then sleep --interval-seconds (default 900 = 15 min)",
    )
    p.add_argument(
        "--interval-seconds",
        type=int,
        default=900,
        help="Sleep between checks when using --watch (default 900 = 15 minutes)",
    )
    args = p.parse_args()

    def run_once() -> str:
        if args.recent_runs > 0:
            return offers_below_price_latest_across_runs(
                args.threshold, args.recent_runs
            )
        return offers_below_price(args.threshold, args.run_id)

    if args.watch:
        print(
            f"Watching every {args.interval_seconds}s "
            f"(threshold ${args.threshold:.0f}, recent_runs={args.recent_runs or 'latest only'})",
            flush=True,
        )
        while True:
            text = run_once()
            print(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---", flush=True)
            print(text, flush=True)
            if "[ALERT]" in text:
                print(">>> ALERT <<<", flush=True)
            time.sleep(args.interval_seconds)

    text = run_once()

    if not args.agent:
        print(text)
        if "[ALERT]" in text:
            sys.exit(2)
        sys.exit(0)

    if not os.getenv("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY for --agent", file=sys.stderr)
        sys.exit(1)

    from openai import OpenAI

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    sys_msg = (
        "You help with TLV–Vienna flight data. You receive raw text from a local database. "
        "Explain clearly in English: is there a price alert, which offers, and what to do next. "
        "Do not invent numbers that are not in the text."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": text},
        ],
    )
    print(resp.choices[0].message.content or "")


if __name__ == "__main__":
    main()
