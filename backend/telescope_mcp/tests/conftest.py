import json

import pytest

from telescope_api2.tests.conftest import (  # noqa: F401
    ch_client,
    ch_settings,
    ch_settings_dict,
    ch_source,
    fake_ch,
    fresh_rate_limit,
    otel_db,
    otel_facts,
    pytest_collection_modifyitems as api2_collection,
    session_client,
    token_client,
)
from tests.fixtures import *  # noqa: F401,F403


def pytest_collection_modifyitems(config, items):
    api2_collection(config, items)
    if ch_settings():
        return
    skip = pytest.mark.skip(
        reason="TELESCOPE_TEST_CH_HOST / TELESCOPE_TEST_CH_PORT not set"
    )
    for item in items:
        if "clickhouse" in item.keywords and "telescope_mcp" in str(item.fspath):
            item.add_marker(skip)


def rpc(client, method, params=None, id=1):
    body = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        body["params"] = params
    return client.post("/api/mcp", body, format="json")


def call_tool(client, name, arguments=None):
    """(is_error, parsed JSON or error text) of a tools/call."""
    response = rpc(client, "tools/call", {"name": name, "arguments": arguments or {}})
    assert response.status_code == 200, response.content
    result = response.json()["result"]
    text = result["content"][0]["text"]
    if result.get("isError"):
        return True, text
    return False, json.loads(text)
