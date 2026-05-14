from __future__ import annotations

import asyncio
import json
from typing import Any

from fastmcp import Client

from mcp_server import mcp


async def _expect_tool_error(client: Client, tool_name: str, args: dict[str, Any]) -> None:
    try:
        result = await client.call_tool(tool_name, args)
    except Exception:
        return

    if getattr(result, "is_error", False):
        return

    raise AssertionError(f"Expected error from tool '{tool_name}' with args={args}")


def _read_text_payload(contents: Any) -> str:
    if isinstance(contents, list) and contents:
        first = contents[0]
        if hasattr(first, "text"):
            return first.text
        if hasattr(first, "blob"):
            return first.blob
    return str(contents)


async def run_verification() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = sorted(tool.name for tool in tools)

        required_tools = {"search", "insert", "aggregate"}
        missing_tools = required_tools.difference(tool_names)
        if missing_tools:
            raise AssertionError(f"Missing required tools: {sorted(missing_tools)}")

        resources = await client.list_resources()
        resource_uris = [str(res.uri) for res in resources]
        if "schema://database" not in resource_uris:
            raise AssertionError("Missing schema://database resource")

        templates = await client.list_resource_templates()
        template_uris = [str(tpl.uriTemplate) for tpl in templates]
        if "schema://table/{table_name}" not in template_uris:
            raise AssertionError("Missing schema://table/{table_name} template")

        search_result = await client.call_tool(
            "search",
            {
                "table": "students",
                "filters": [{"column": "cohort", "operator": "=", "value": "A1"}],
                "order_by": "score",
                "descending": True,
                "limit": 5,
                "offset": 0,
            },
        )
        search_data = search_result.data
        if not isinstance(search_data, dict) or not search_data.get("rows"):
            raise AssertionError("search tool did not return expected rows")

        insert_result = await client.call_tool(
            "insert",
            {
                "table": "students",
                "values": {
                    "full_name": "Verification User",
                    "cohort": "Z9",
                    "age": 23,
                    "score": 7.7,
                },
            },
        )
        insert_data = insert_result.data
        if not isinstance(insert_data, dict) or not insert_data.get("row_id"):
            raise AssertionError("insert tool did not return row_id")

        aggregate_result = await client.call_tool(
            "aggregate",
            {
                "table": "students",
                "metric": "avg",
                "column": "score",
                "group_by": "cohort",
            },
        )
        aggregate_data = aggregate_result.data
        if not isinstance(aggregate_data, dict) or "rows" not in aggregate_data:
            raise AssertionError("aggregate tool did not return rows")

        db_schema_contents = await client.read_resource("schema://database")
        db_schema_text = _read_text_payload(db_schema_contents)
        parsed_db_schema = json.loads(db_schema_text)
        if "tables" not in parsed_db_schema:
            raise AssertionError("schema://database missing tables payload")

        students_schema_contents = await client.read_resource("schema://table/students")
        students_schema_text = _read_text_payload(students_schema_contents)
        parsed_students_schema = json.loads(students_schema_text)
        if parsed_students_schema.get("table") != "students":
            raise AssertionError("schema://table/students returned unexpected table")

        await _expect_tool_error(client, "search", {"table": "missing_table"})
        await _expect_tool_error(
            client,
            "search",
            {
                "table": "students",
                "filters": [{"column": "cohort", "operator": "contains", "value": "A1"}],
            },
        )
        await _expect_tool_error(client, "insert", {"table": "students", "values": {}})

    print("[OK] Server starts and Client can connect")
    print("[OK] Required tools discovered: search, insert, aggregate")
    print("[OK] Schema resources discovered")
    print("[OK] Valid tool calls succeeded")
    print("[OK] Invalid requests produced errors")


if __name__ == "__main__":
    asyncio.run(run_verification())
