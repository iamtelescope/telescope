"""Acceptance on the P0.2 OTel data: search returns the /api/v1 rows, charts match, the planted
trace comes back whole, RBAC holds and system.query_log tags MCP queries."""

import json
from datetime import datetime

import pytest

from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope_api2.tests.test_clickhouse import logged
from telescope_mcp.tests.conftest import call_tool, token_client
from tests.integration.test_trace_view import connection, make_source  # noqa: F401

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]
rbac_manager = RBACManager()


def ms(iso):
    return int(datetime.fromisoformat(iso[:26] + "+00:00").timestamp() * 1000)


@pytest.fixture
def window(otel_facts):
    return ms(otel_facts["start"]), ms(otel_facts["end"])


@pytest.fixture
def logs(connection, otel_db):  # noqa: F811
    source = make_source("mcp-logs", connection, otel_db, "otel_logs", {})
    source.default_chosen_columns = "Timestamp, ServiceName, SeverityText, Body"
    source.save()
    return source


@pytest.fixture
def traces(connection, otel_db):  # noqa: F811
    return make_source("mcp-traces", connection, otel_db, "otel_traces", {})


def test_search_returns_the_api_rows(root_user, logs, window):
    client = token_client(root_user)
    body = {
        "columns": "Timestamp, ServiceName, SeverityText, Body, TraceId",
        "query": "ServiceName = 'payment' and SeverityText = 'ERROR'",
        "from": str(window[0] + 12 * 3600_000),
        "to": str(window[0] + 12 * 3600_000 + 600_000),
        "limit": 20,
    }
    api = client.post(f"/api/v1/sources/{logs.slug}/search", body, format="json").json()
    error, data = call_tool(client, "search", {"source": logs.slug, **body})
    assert not error, data
    assert len(data["rows"]) == 20 and data["cursor"]
    assert data["rows"] == api["rows"] and data["cursor"] == api["cursor"]
    assert data["columns"] == api["columns"]
    # The cursor pages on to the next older rows, as with the API.
    error, older = call_tool(
        client, "search", {"source": logs.slug, **body, "before": data["cursor"]}
    )
    api_older = client.post(
        f"/api/v1/sources/{logs.slug}/search",
        {**body, "before": api["cursor"]},
        format="json",
    ).json()
    assert older["rows"] == api_older["rows"] and older["rows"] != data["rows"]


def test_chart_matches_the_api(root_user, logs, window):
    client = token_client(root_user)
    body = {
        "from": str(window[0]),
        "to": str(window[1]),
        "display": "table",
        "series": [{"agg": "count"}],
        "group_by": "ServiceName",
        "query": "SeverityText = 'ERROR'",
    }
    api = client.post(f"/api/v1/sources/{logs.slug}/chart", body, format="json").json()
    error, data = call_tool(client, "chart", {"source": logs.slug, **body})
    api.pop("debug", None)  # debug.sql is an API v2 extra for RAW_QUERY users.
    assert not error and data == api
    assert "payment" in json.dumps(data)


def test_get_trace_returns_the_planted_trace(root_user, traces, otel_facts):
    big = otel_facts["big_trace"]
    args = {
        "source": traces.slug,
        "trace_id": big["trace_id"],
        "around_ms": ms(big["start"]),
    }
    error, trace = call_tool(token_client(root_user), "get_trace", args)
    assert not error, trace
    assert trace["found"] and trace["span_count"] == big["spans"] == len(trace["spans"])
    assert trace["services"] == big["services"] and trace["truncated"] is False
    assert sum(s["error"] for s in trace["spans"]) == big["error_spans"]
    assert trace["spans"][0]["parent_id"] == ""
    assert len(trace["resources"]) >= 5 and all(
        isinstance(s["resource"], int) for s in trace["spans"]
    )
    assert (
        trace["resources"][trace["spans"][0]["resource"]]["service.name"]
        == trace["spans"][0]["service"]
    )
    error, text = call_tool(
        token_client(root_user), "get_trace", {**args, "source": "nope"}
    )
    assert error and "does not exist" in text


def test_rbac_on_real_data(test_user, logs, traces, window, otel_facts):
    client = token_client(test_user)
    args = {
        "source": logs.slug,
        "from": str(window[0]),
        "to": str(window[1]),
        "limit": 5,
    }
    assert call_tool(client, "search", args)[0]
    trace = {"source": traces.slug, "trace_id": otel_facts["trace_id"]}
    assert call_tool(client, "get_trace", trace)[0]
    rbac_manager.grant_source_role(logs, SourceRole.VIEWER.value, user=test_user)
    assert call_tool(client, "describe_source", {"source": logs.slug})[0] is False
    assert call_tool(client, "search", args)[0]
    rbac_manager.grant_source_role(logs, SourceRole.USER.value, user=test_user)
    error, data = call_tool(client, "search", args)
    assert not error and len(data["rows"]) == 5
    error, text = call_tool(client, "search", {**args, "raw_query": "1 = 1"})
    assert error and "raw" in text.lower()


def test_mcp_queries_are_attributed(root_user, logs, ch_client, window):
    since = ch_client.command("SELECT now64(6)")
    call_tool(
        token_client(root_user),
        "chart",
        {
            "source": logs.slug,
            "from": str(window[0]),
            "to": str(window[1]),
            "granularity": "1h",
        },
    )
    rows = logged(ch_client, since, '"surface":"mcp"')
    assert [r[0] for r in rows] == [
        {"surface": "mcp", "source": logs.slug, "user": root_user.pk}
    ]
