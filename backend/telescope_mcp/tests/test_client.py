"""The official mcp Python client against /api/mcp on a live server."""

import asyncio
import json

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from telescope.models import APIToken, Dashboard
from tests.data import get_dashboard_data

pytestmark = pytest.mark.django_db(transaction=True)


async def session_run(url, token, steps):
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            return info, await steps(session)


def run(live_server, token, steps):
    return asyncio.run(session_run(f"{live_server.url}/api/mcp", token, steps))


def test_client_lists_and_calls_tools(live_server, root_user, test_user, ch_source):
    Dashboard.objects.create(
        slug="ops",
        name="Ops",
        owner=root_user,
        updated_by=root_user,
        data=get_dashboard_data(),
    )

    async def steps(session):
        tools = (await session.list_tools()).tools
        sources = await session.call_tool("list_sources", {})
        tile = {"id": "fromclient", "chart": {"display": "text", "text": "hello"}}
        upsert = await session.call_tool(
            "upsert_tile", {"dashboard": "ops", "tile": tile}
        )
        missing = await session.call_tool("get_dashboard", {"dashboard": "nope"})
        await session.send_ping()
        return tools, sources, upsert, missing

    info, (tools, sources, upsert, missing) = run(
        live_server, APIToken.create(root_user, "c").token, steps
    )
    assert info.serverInfo.name == "telescope" and info.capabilities.tools is not None
    assert len(tools) == 9
    hints = {t.name: t.annotations for t in tools}
    assert (
        hints["upsert_tile"].readOnlyHint is False
        and hints["search"].readOnlyHint is True
    )
    assert [s["slug"] for s in json.loads(sources.content[0].text)] == ["clickhouse"]
    assert not upsert.isError and json.loads(upsert.content[0].text)["created"]
    assert "fromclient" in [
        t["id"] for t in Dashboard.objects.get(slug="ops").data["tiles"]
    ]
    assert missing.isError and missing.content[0].text == "Dashboard not found"

    # A user without any role sees no sources and cannot edit root's dashboard.
    async def denied(session):
        tile = {"id": "x", "chart": {"display": "text", "text": "no"}}
        return (
            await session.call_tool("list_sources", {}),
            await session.call_tool("search", {"source": "clickhouse"}),
            await session.call_tool("upsert_tile", {"dashboard": "ops", "tile": tile}),
        )

    _, (sources, search, upsert) = run(
        live_server, APIToken.create(test_user, "c").token, denied
    )
    assert json.loads(sources.content[0].text) == []
    assert search.isError and upsert.isError


def test_client_rejects_bad_token(live_server):
    async def steps(session):
        return None

    with pytest.raises(BaseException) as raised:
        run(live_server, "nope", steps)
    assert "401" in repr(
        raised.value.exceptions if hasattr(raised.value, "exceptions") else raised.value
    ), raised.value
