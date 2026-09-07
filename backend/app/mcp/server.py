"""Minimal MCP stdio server exposing bounded financial analytics."""

import asyncio
import json
import sys
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.analytics.service import AnalyticsService
from app.core.config import settings
from app.db.session import async_session

PROTOCOL_VERSION = "2025-03-26"
TOOLS = [
    {
        "name": "financial_overview",
        "description": (
            "Return exact SQL-calculated spending, income, cash flow, "
            "monthly totals, and top categories for the configured user."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start": {"type": "string", "format": "date"},
                "end_exclusive": {"type": "string", "format": "date"},
                "currency": {
                    "type": "string",
                    "minLength": 3,
                    "maxLength": 3,
                    "default": "USD",
                },
            },
            "required": ["start", "end_exclusive"],
            "additionalProperties": False,
        },
    },
]


async def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "finsight-ai", "version": "0.0.1"},
            },
        )
    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})
    if method == "tools/call":
        return await _call_tool(request_id, request.get("params"))
    return _error(request_id, -32601, "Method not found")


async def _call_tool(
    request_id: object,
    params: object,
) -> dict[str, Any]:
    if not isinstance(params, dict) or params.get("name") != "financial_overview":
        return _error(request_id, -32602, "Unknown tool")
    arguments = params.get("arguments")
    if not isinstance(arguments, dict):
        return _error(request_id, -32602, "Tool arguments are required")
    if not settings.mcp_user_id:
        return _tool_error(request_id, "MCP_USER_ID is not configured")
    try:
        start = date.fromisoformat(arguments["start"])
        end_exclusive = date.fromisoformat(arguments["end_exclusive"])
        currency = arguments.get("currency", "USD")
        if (
            not isinstance(currency, str)
            or len(currency) != 3
            or start >= end_exclusive
            or (end_exclusive - start).days > 366
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return _tool_error(request_id, "Invalid analytics period or currency")
    try:
        async with async_session() as session:
            overview = await AnalyticsService(session).get_overview(
                user_id=settings.mcp_user_id,
                start=start,
                end_exclusive=end_exclusive,
                currency=currency.upper(),
                category_limit=5,
            )
    except SQLAlchemyError:
        return _tool_error(request_id, "Financial data is temporarily unavailable")
    payload = json.dumps(
        overview.model_dump(mode="json"),
        default=_json_default,
        separators=(",", ":"),
    )
    return _result(
        request_id,
        {"content": [{"type": "text", "text": payload}], "isError": False},
    )


def _json_default(value: object) -> str:
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError


def _result(request_id: object, result: object) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: object, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _tool_error(request_id: object, message: str) -> dict[str, Any]:
    return _result(
        request_id,
        {
            "content": [{"type": "text", "text": message}],
            "isError": True,
        },
    )


async def run() -> None:
    while line := await asyncio.to_thread(sys.stdin.readline):
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError
            response = await handle(request)
        except (json.JSONDecodeError, ValueError):
            response = _error(None, -32700, "Parse error")
        if response is not None:
            print(json.dumps(response, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    asyncio.run(run())
