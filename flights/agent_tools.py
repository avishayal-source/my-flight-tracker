"""Tool definitions + dispatch for the flight tracker CLI agent (same logic as MCP)."""
from __future__ import annotations

import json
from typing import Any

from flights import compare_runs as compare_mod
from flights.analyze import cheapest_roundtrips
from flights.db import connect, print_stats
from flights.mcp_server import list_offers, price_trend

import io
from contextlib import redirect_stdout


def _stats() -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        print_stats()
    return buf.getvalue()


def dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "db_stats":
        return _stats()
    if name == "cheapest_roundtrip":
        days = int(arguments.get("trip_days", 4))
        run_id = arguments.get("run_id")
        opts = cheapest_roundtrips([days], run_id=run_id)
        if not opts:
            return f"No {days}-day round trip found."
        o = opts[0]
        return (
            f"Cheapest {o.trip_days}-day round trip (run {o.run_id}):\n"
            f"  Out: {o.outbound_date}  {o.outbound_carrier} {o.outbound_flight}  ${o.outbound_price:.2f}\n"
            f"  Ret: {o.return_date}  {o.return_carrier} {o.return_flight}  ${o.return_price:.2f}\n"
            f"  Total: ${o.total_price:.2f} USD"
        )
    if name == "price_trend":
        return price_trend(
            arguments.get("direction", "TLV_VIE"),
            int(arguments.get("limit", 15)),
        )
    if name == "compare_runs":
        d = arguments.get("direction")
        return compare_mod.compare_runs_summary(d)
    if name == "departure_date_price_over_runs":
        return compare_mod.departure_date_price_over_runs(
            arguments["direction"],
            arguments["departure_date"],
        )
    if name == "same_flight_price_over_runs":
        return compare_mod.same_flight_price_over_runs(
            arguments["direction"],
            arguments["departure_date"],
            arguments["carrier_code"],
            arguments["flight_number"],
        )
    if name == "price_vs_days_to_departure":
        return compare_mod.price_vs_days_to_departure(
            arguments.get("direction", "TLV_VIE"),
            bool(arguments.get("use_latest_run_only", False)),
        )
    if name == "list_offers":
        return list_offers(
            arguments.get("direction", "TLV_VIE"),
            arguments.get("departure_date"),
            arguments.get("run_id"),
            int(arguments.get("limit", 10)),
        )
    raise ValueError(f"Unknown tool: {name}")


OPENAI_TOOLS = [
    {"type": "function", "function": {"name": "db_stats", "description": "Scrape run and offer counts", "parameters": {"type": "object", "properties": {}}}},
    {
        "type": "function",
        "function": {
            "name": "cheapest_roundtrip",
            "description": "Cheapest N-day TLV-VIE round trip from latest or given run",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_days": {"type": "integer", "description": "3, 4, or 5"},
                    "run_id": {"type": "integer", "description": "Optional scrape run id"},
                },
                "required": ["trip_days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "price_trend",
            "description": "Min price per departure date across all scrapes",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["TLV_VIE", "VIE_TLV"]},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_runs",
            "description": "How prices changed between scrape runs",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["TLV_VIE", "VIE_TLV"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "departure_date_price_over_runs",
            "description": "Cheapest price for a departure date on each scrape run",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["TLV_VIE", "VIE_TLV"]},
                    "departure_date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["direction", "departure_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "same_flight_price_over_runs",
            "description": "Price of one flight across scrape runs",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["TLV_VIE", "VIE_TLV"]},
                    "departure_date": {"type": "string"},
                    "carrier_code": {"type": "string"},
                    "flight_number": {"type": "string"},
                },
                "required": ["direction", "departure_date", "carrier_code", "flight_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "price_vs_days_to_departure",
            "description": "Price vs booking window (days until departure)",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["TLV_VIE", "VIE_TLV"]},
                    "use_latest_run_only": {"type": "boolean"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_offers",
            "description": "List offers for a direction and optional date",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["TLV_VIE", "VIE_TLV"]},
                    "departure_date": {"type": "string"},
                    "run_id": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
]
