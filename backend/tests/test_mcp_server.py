"""MCP protocol boundary tests."""

import asyncio

from app.mcp.server import PROTOCOL_VERSION, handle


def test_mcp_initialize_and_tool_discovery():
    initialized = asyncio.run(handle({"id": 1, "method": "initialize"}))
    listed = asyncio.run(handle({"id": 2, "method": "tools/list"}))

    assert initialized["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert [tool["name"] for tool in listed["result"]["tools"]] == [
        "financial_overview",
    ]
    assert (
        listed["result"]["tools"][0]["inputSchema"]["additionalProperties"]
        is False
    )


def test_mcp_rejects_unknown_tools():
    response = asyncio.run(
        handle(
            {
                "id": 3,
                "method": "tools/call",
                "params": {"name": "execute_sql", "arguments": {}},
            },
        ),
    )

    assert response["error"]["code"] == -32602
