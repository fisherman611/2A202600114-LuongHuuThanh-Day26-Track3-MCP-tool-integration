from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from db import SQLiteAdapter, ValidationError
from init_db import create_database


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "lab.db"
DB_PATH = Path(os.getenv("SQLITE_LAB_DB_PATH", str(DEFAULT_DB_PATH))).resolve()

# Ensure there is always a working database for local MCP clients.
create_database(DB_PATH, reset=False)

adapter = SQLiteAdapter(DB_PATH)
mcp = FastMCP("SQLite Lab MCP Server")


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | list[str] | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows from a table with optional filters, ordering, and pagination."""
    return adapter.search(
        table=table,
        filters=filters,
        columns=columns,
        limit=limit,
        offset=offset,
        order_by=order_by,
        descending=descending,
    )


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one row into a table and return inserted payload metadata."""
    return adapter.insert(table=table, values=values)


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    group_by: str | list[str] | None = None,
) -> dict[str, Any]:
    """Run aggregate metrics (count, avg, sum, min, max) with optional filters and group_by."""
    return adapter.aggregate(
        table=table,
        metric=metric,
        column=column,
        filters=filters,
        group_by=group_by,
    )


@mcp.resource("schema://database")
def database_schema() -> dict[str, Any]:
    """Return full database schema metadata for all tables."""
    return {
        "database": str(DB_PATH),
        "tables": adapter.get_database_schema(),
    }


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> dict[str, Any]:
    """Return schema metadata for one table."""
    return {
        "database": str(DB_PATH),
        "table": table_name,
        "schema": adapter.get_table_schema(table_name),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SQLite Lab MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport to run. Default is stdio.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP/SSE transport")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transport")
    parser.add_argument("--path", default="/mcp", help="Path for HTTP/SSE transport")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Reset and reseed database before server starts",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.init_db:
        create_database(DB_PATH, reset=True)

    try:
        if args.transport == "stdio":
            mcp.run()
        else:
            mcp.run(
                transport=args.transport,
                host=args.host,
                port=args.port,
                path=args.path,
            )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


if __name__ == "__main__":
    main()
