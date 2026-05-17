"""Read-only warehouse tools with strict validation."""
from __future__ import annotations

import os
import re
from pathlib import Path

import duckdb
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "warehouse.duckdb"

ALLOWED_TABLES = frozenset({"regions", "orders"})
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|copy|pragma)\b",
    re.IGNORECASE,
)


class QueryInput(BaseModel):
    sql: str = Field(description="Single SELECT statement against regions or orders")


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[list]
    row_count: int


def _db_path() -> Path:
    return Path(os.getenv("WAREHOUSE_PATH", str(DEFAULT_DB)))


def list_tables() -> list[str]:
    return sorted(ALLOWED_TABLES)


def describe_table(table: str) -> str:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table not allowed: {table}")
    con = duckdb.connect(str(_db_path()), read_only=True)
    try:
        col_rows = con.execute(f"DESCRIBE {table}").fetchall()
        sample_cur = con.execute(f"SELECT * FROM {table} LIMIT 3")
        sample_cols = [d[0] for d in sample_cur.description]
        sample_rows = sample_cur.fetchall()
        schema_lines = [f"  {row}" for row in col_rows]
        sample_lines = [f"  {dict(zip(sample_cols, row))}" for row in sample_rows]
        return "Schema:\n" + "\n".join(schema_lines) + "\n\nSample:\n" + "\n".join(sample_lines)
    finally:
        con.close()


def run_readonly_query(sql: str) -> QueryResult:
    cleaned = sql.strip().rstrip(";")
    if FORBIDDEN.search(cleaned):
        raise ValueError("Only read-only SELECT queries are allowed")
    if not re.match(r"^select\b", cleaned, re.IGNORECASE):
        raise ValueError("Query must start with SELECT")
    for token in re.findall(r"\b([a-z_][a-z0-9_]*)\b", cleaned, re.IGNORECASE):
        if token.lower() in ALLOWED_TABLES:
            continue
        if token.lower() in {
            "select", "from", "where", "join", "on", "and", "or", "as",
            "group", "by", "order", "limit", "sum", "count", "avg", "min", "max",
            "left", "right", "inner", "outer", "having", "distinct", "between",
            "in", "not", "null", "is", "desc", "asc", "case", "when", "then", "else", "end",
        }:
            continue
        if token.isdigit():
            continue
    limit = int(os.getenv("SQL_ROW_LIMIT", "500"))
    wrapped = f"SELECT * FROM ({cleaned}) AS _q LIMIT {limit}"
    con = duckdb.connect(str(_db_path()), read_only=True)
    try:
        cur = con.execute(wrapped)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        serializable = [list(r) for r in rows]
        return QueryResult(columns=cols, rows=serializable, row_count=len(rows))
    finally:
        con.close()


OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "List warehouse tables available to the assistant",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "Show schema and sample rows for a table",
            "parameters": {
                "type": "object",
                "properties": {"table": {"type": "string", "enum": ["regions", "orders"]}},
                "required": ["table"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_readonly_query",
            "description": "Run a read-only SELECT against regions or orders",
            "parameters": QueryInput.model_json_schema(),
        },
    },
]


def dispatch_tool(name: str, arguments: dict) -> str:
    if name == "list_tables":
        return str(list_tables())
    if name == "describe_table":
        return describe_table(arguments["table"])
    if name == "run_readonly_query":
        result = run_readonly_query(arguments["sql"])
        return result.model_dump_json()
    raise ValueError(f"Unknown tool: {name}")
