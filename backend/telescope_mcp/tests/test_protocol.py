"""The streamable HTTP transport: JSON-RPC framing, versions, auth and the tool listing."""

import pytest
from rest_framework.test import APIClient

from telescope.models import APIToken
from telescope_mcp.tests.conftest import call_tool, rpc, token_client

pytestmark = pytest.mark.django_db

TOOL_NAMES = [
    "list_sources",
    "describe_source",
    "search",
    "chart",
    "get_trace",
    "list_dashboards",
    "get_dashboard",
    "upsert_tile",
    "list_alerts",
]


def test_initialize_negotiates_version(root_user):
    client = token_client(root_user)
    result = rpc(client, "initialize", {"protocolVersion": "2025-03-26"}).json()[
        "result"
    ]
    assert result["protocolVersion"] == "2025-03-26"
    assert result["capabilities"] == {"tools": {"listChanged": False}}
    assert result["serverInfo"]["name"] == "telescope"
    assert "list_sources" in result["instructions"]
    unknown = rpc(client, "initialize", {"protocolVersion": "1999-01-01"}).json()
    assert unknown["result"]["protocolVersion"] == "2025-06-18"


def test_tools_listed_with_hints(root_user):
    tools = rpc(token_client(root_user), "tools/list").json()["result"]["tools"]
    assert [t["name"] for t in tools] == TOOL_NAMES
    for t in tools:
        hints = t["annotations"]
        assert set(hints) == {
            "readOnlyHint",
            "destructiveHint",
            "idempotentHint",
            "openWorldHint",
        }
        assert hints["readOnlyHint"] is (t["name"] != "upsert_tile")
        assert hints["destructiveHint"] is (t["name"] == "upsert_tile")
        assert t["inputSchema"]["type"] == "object" and t["description"] and t["title"]


def test_auth(root_user):
    anonymous = rpc(APIClient(), "tools/list")
    assert anonymous.status_code == 401
    assert anonymous["WWW-Authenticate"].startswith("Bearer")
    bad = APIClient()
    bad.credentials(HTTP_AUTHORIZATION="Bearer nope")
    assert rpc(bad, "tools/list").status_code == 401
    token = APIToken.create(root_user, "mcp").token
    for scheme in ["Bearer", "Token"]:
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"{scheme} {token}")
        assert rpc(client, "ping").json() == {"jsonrpc": "2.0", "id": 1, "result": {}}
    root_user.is_active = False
    root_user.save()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert rpc(client, "ping").status_code == 401


def test_framing(root_user):
    client = token_client(root_user)
    note = client.post(
        "/api/mcp",
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        format="json",
    )
    assert note.status_code == 202 and note.content == b""
    assert client.get("/api/mcp").status_code == 405
    assert client.delete("/api/mcp").status_code == 405
    garbage = client.post("/api/mcp", "{", content_type="application/json")
    assert garbage.status_code == 400 and garbage.json()["error"]["code"] == -32700
    assert (
        client.post("/api/mcp", {"x": 1}, format="json").json()["error"]["code"]
        == -32600
    )
    assert rpc(client, "resources/list").json()["error"]["code"] == -32601
    unknown = rpc(client, "tools/call", {"name": "drop_table", "arguments": {}}).json()
    assert unknown["error"]["code"] == -32602
    listed = rpc(client, "tools/call", {"name": ["search"]}).json()
    assert listed["error"]["code"] == -32602
    old = client.post(
        "/api/mcp",
        {"jsonrpc": "2.0", "id": 1, "method": "ping"},
        format="json",
        HTTP_MCP_PROTOCOL_VERSION="2020-01-01",
    )
    assert old.status_code == 400
    batch = [{"jsonrpc": "2.0", "id": i, "method": "ping"} for i in (1, 2)]
    assert [r["id"] for r in client.post("/api/mcp", batch, format="json").json()] == [
        1,
        2,
    ]


def test_arguments_are_validated(root_user):
    client = token_client(root_user)
    assert call_tool(client, "describe_source") == (
        True,
        "invalid arguments: 'source' is a required property",
    )
    error, text = call_tool(client, "search", {"source": "x", "limit": 1000})
    assert error and text.startswith("invalid arguments at limit")
    error, text = call_tool(client, "list_sources", {"extra": 1})
    assert error and "additional" in text.lower()
