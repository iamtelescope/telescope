"""Tool behaviour on SQLite with a mocked ClickHouse client."""

import json

import pytest

from telescope.models import Dashboard
from telescope_alerts.models import Alert
from telescope_api2.tests.conftest import chart_body, search_body
from telescope_mcp import tools
from telescope_mcp.tests.conftest import call_tool, token_client
from tests.data import get_dashboard_data

pytestmark = pytest.mark.django_db


@pytest.fixture
def dashboard(root_user):
    return Dashboard.objects.create(
        slug="ops",
        name="Ops",
        owner=root_user,
        updated_by=root_user,
        data=get_dashboard_data(),
    )


@pytest.fixture
def ch_source(ch_source):
    # The shared fixture's defaults name a column it does not have.
    ch_source.default_chosen_columns = "hostname"
    ch_source.save()
    return ch_source


def same_query(a, b):
    # Only the log_comment differs: surface mcp vs api.
    strip = lambda c: {k: v for k, v in c.kwargs.items() if k != "settings"}
    return a.args == b.args and strip(a) == strip(b)


def test_list_and_describe_sources(root_user, ch_source):
    client = token_client(root_user)
    error, sources = call_tool(client, "list_sources")
    assert not error and [s["slug"] for s in sources] == ["clickhouse"]
    assert "use" in sources[0]["permissions"]
    error, info = call_tool(client, "describe_source", {"source": "clickhouse"})
    assert not error
    assert info["columns"]["hostname"]["type"] == ch_source.columns["hostname"]["type"]
    assert info["table"] == "logs" and info["time_column"] == ch_source.time_column
    error, text = call_tool(client, "describe_source", {"source": "nope"})
    assert error and "does not exist" in text


def test_search_and_chart_run_the_api_v2_sql(root_user, ch_source, fake_ch):
    client = token_client(root_user)
    body = search_body(query="hostname = 'a'")
    client.post("/api/v1/sources/clickhouse/search", body, format="json")
    api_sql = fake_ch.query.call_args
    error, data = call_tool(client, "search", {"source": "clickhouse", **body})
    assert not error and data["rows"] == [] and data["cursor"] is None
    assert same_query(fake_ch.query.call_args, api_sql)
    client.post("/api/v1/sources/clickhouse/chart", chart_body(), format="json")
    api_sql = fake_ch.query.call_args
    error, data = call_tool(client, "chart", {"source": "clickhouse", **chart_body()})
    assert not error and "series" in data
    assert same_query(fake_ch.query.call_args, api_sql)


@pytest.mark.parametrize("defaults", ["hostname, message", ["hostname", "message"]])
def test_search_defaults(root_user, ch_source, fake_ch, defaults):
    ch_source.default_chosen_columns = defaults
    ch_source.save()
    error, data = call_tool(token_client(root_user), "search", {"source": "clickhouse"})
    assert not error, data
    sql = fake_ch.query.call_args.args[0]
    assert "LIMIT 50" in sql
    assert [c["name"] for c in data["columns"]] == ["hostname", "message"]
    assert data["to"] - data["from"] == pytest.approx(3600_000, abs=1000)


def test_query_errors_are_tool_errors(root_user, ch_source, fake_ch):
    client = token_client(root_user)
    fake_ch.query.side_effect = RuntimeError("Code: 62. Syntax error")
    assert call_tool(client, "chart", {"source": "clickhouse"}) == (
        True,
        "Code: 62. Syntax error",
    )
    error, text = call_tool(
        client, "search", {"source": "clickhouse", "query": "nope = 1"}
    )
    assert error and text.startswith("validation failed") and "query" in text


def test_upsert_tile_adds_then_replaces(root_user, ch_source, dashboard):
    client = token_client(root_user)
    chart = {"source": "clickhouse", "display": "number", "series": [{"agg": "count"}]}
    error, added = call_tool(
        client,
        "upsert_tile",
        {"dashboard": "ops", "tile": {"title": "Rows", "chart": chart}},
    )
    assert not error, added
    assert added["created"] and added["version"] == 2
    bottom = max(t["y"] + t["h"] for t in get_dashboard_data()["tiles"])
    assert {k: added["tile"][k] for k in "xywh"} == {
        "x": 0,
        "y": bottom,
        "w": 12,
        "h": 6,
    }
    tile_id = added["tile"]["id"]
    error, replaced = call_tool(
        client,
        "upsert_tile",
        {"dashboard": "ops", "tile": {"id": tile_id, "title": "All"}},
    )
    assert not error and not replaced["created"] and replaced["version"] == 3
    assert replaced["tile"] == {**added["tile"], "title": "All"}
    tiles = Dashboard.objects.get(slug="ops").data["tiles"]
    assert [t["id"] for t in tiles].count(tile_id) == 1 and len(tiles) == 3
    # The dashboard serializer still validates what the tool writes.
    error, text = call_tool(
        client,
        "upsert_tile",
        {"dashboard": "ops", "tile": {"id": tile_id, "chart": {"display": "pie"}}},
    )
    assert error and text.startswith("validation failed")
    error, text = call_tool(
        client, "upsert_tile", {"dashboard": "ops", "tile": {"id": "new"}}
    )
    assert (error, text) == (True, "a new tile needs a chart")
    assert Dashboard.objects.get(slug="ops").version == 3


def test_get_and_list_dashboards(root_user, dashboard):
    client = token_client(root_user)
    error, items = call_tool(client, "list_dashboards")
    assert not error and [(d["slug"], d["tiles_count"]) for d in items] == [("ops", 2)]
    error, got = call_tool(client, "get_dashboard", {"dashboard": "ops"})
    assert not error and got == client.get("/api/v1/dashboards/ops").json()
    assert call_tool(client, "get_dashboard", {"dashboard": "nope"}) == (
        True,
        "Dashboard not found",
    )


def test_list_alerts(root_user, ch_source, dashboard):
    common = dict(
        owner=root_user,
        series={"agg": "count"},
        interval="5m",
        threshold_type="above",
        threshold=1,
    )
    Alert.objects.create(
        name="search", kind="search", source_slug="clickhouse", **common
    )
    Alert.objects.create(
        name="tile", kind="tile", dashboard=dashboard, tile_id="t1", **common
    )
    client = token_client(root_user)
    error, alerts = call_tool(client, "list_alerts")
    assert not error and [a["name"] for a in alerts] == ["search", "tile"]
    assert alerts == client.get("/api/v1/alerts?page_size=500").json()["data"]
    error, alerts = call_tool(client, "list_alerts", {"dashboard": "ops"})
    assert [a["name"] for a in alerts] == ["tile"]


def test_queries_are_attributed_to_mcp(root_user, ch_source, fake_ch):
    call_tool(token_client(root_user), "search", {"source": "clickhouse"})
    comment = json.loads(fake_ch.query.call_args.kwargs["settings"]["log_comment"])
    assert comment == {"surface": "mcp", "source": "clickhouse", "user": root_user.pk}


def test_limit_size(monkeypatch):
    monkeypatch.setattr(tools, "MAX_RESPONSE_CHARS", 1000)
    rows = [{"n": i, "body": "x" * 40} for i in range(100)]
    out = json.loads(
        tools.limit_size({"columns": ["n"], "rows": rows, "cursor": {"time": 1}})
    )
    assert len(tools.dumps(out)) <= 1000
    n = out["trimmed"]["returned"]
    assert 0 < n < 100 and out["rows"] == rows[:n] and out["trimmed"]["total"] == 100
    assert "cursor" not in out and out["columns"] == ["n"]
    assert tools.limit_size({"rows": rows[:2]}) == tools.dumps({"rows": rows[:2]})
    listed = json.loads(tools.limit_size(rows))
    assert listed["trimmed"]["field"] == "items"
    huge = json.loads(tools.limit_size({"rows": [{"body": "y" * 2000}]}))
    assert huge["trimmed"] is True and "limit" in huge["error"]


def test_big_responses_are_trimmed(root_user, ch_source, monkeypatch):
    monkeypatch.setattr(tools, "MAX_RESPONSE_CHARS", 3000)
    spans = [{"id": str(i), "name": "n" * 100} for i in range(60)]
    trace = {"trace_id": "abc", "found": True, "spans": spans}
    monkeypatch.setattr(tools, "fetch_trace", lambda *a: trace)
    client = token_client(root_user)
    response = client.post(
        "/api/mcp",
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_trace",
                "arguments": {"source": "clickhouse", "trace_id": "abc"},
            },
        },
        format="json",
    )
    text = response.json()["result"]["content"][0]["text"]
    out = json.loads(text)
    assert (
        len(text) <= 3000
        and out["found"]
        and out["spans"] == spans[: len(out["spans"])]
    )
    assert out["trimmed"] == {
        "field": "spans",
        "returned": len(out["spans"]),
        "total": 60,
        "hint": "narrow the query, pick fewer columns or lower limit",
    }
