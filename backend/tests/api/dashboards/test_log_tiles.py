"""P5.2: search (log rows) and patterns dashboard tiles: saving, and their data endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from telescope.fetchers.response import DataResponse
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole

from tests.data import get_dashboard_data

rbac_manager = RBACManager()
T0 = 1762423200000
PATTERNS = {"patterns": [], "buckets": [], "step": 1, "total": 0, "sample_size": 0}
FETCH_PATTERNS = "telescope.views.source.tiles.fetch_patterns"
GET_FETCHERS = "telescope.views.source.tiles.get_fetchers"


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def grant(user, source, role=SourceRole.USER):
    rbac_manager.grant_source_role(source, role.value, user=user)
    return client_for(user)


def tile(chart, id="log1"):
    return {"id": id, "x": 0, "y": 8, "w": 24, "h": 10, "title": "", "chart": chart}


def save(client, *charts, variables=None):
    data = get_dashboard_data()
    data["tiles"] += [tile(c, f"log{i}") for i, c in enumerate(charts)]
    if variables is not None:
        data["variables"] = variables
    body = {"name": "Logs", "description": "", "shared": False, "data": data}
    return client.post("/ui/v1/dashboards", body, format="json").json()


def body(**changes):
    data = {
        "from": str(T0),
        "to": str(T0 + 3600000),
        "query": "",
        "columns": "hostname",
    }
    data.update(changes)
    return data


def post(client, source, kind, data, qs=""):
    url = f"/ui/v1/sources/{source.slug}/{kind}Tile{qs}"
    return client.post(url, data, format="json").json()


def fake_fetcher(rows=(), cursor=None):
    fetcher = MagicMock()
    fetcher.fetch_data.return_value = DataResponse(rows=list(rows), cursor=cursor)
    return fetcher


@pytest.mark.django_db
def test_dashboard_saves_search_and_patterns_tiles(test_user, clickhouse_source):
    client = grant(test_user, clickhouse_source)
    search = {
        "source": "clickhouse",
        "display": "search",
        "query": "hostname = $host",
        "columns": "hostname, message",
        "limit": 100,
    }
    patterns = {"source": "clickhouse", "display": "patterns", "sample": 5000}
    created = save(client, search, patterns)
    assert created["result"] is True, created
    charts = [t["chart"] for t in created["data"]["data"]["tiles"][2:]]
    assert charts[0] == {**search, "raw_query": "", "context_columns": {}}
    assert charts[1] == {
        **patterns,
        "query": "",
        "raw_query": "",
        "context_columns": {},
        "column": "",
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "chart, field",
    [
        ({"display": "search", "columns": "nope"}, "columns"),
        ({"display": "search", "limit": 501}, "limit"),
        ({"display": "search", "series": [{"agg": "count"}]}, "series"),
        ({"display": "patterns", "column": "nope"}, "column"),
        ({"display": "patterns", "sample": 0}, "sample"),
        ({"display": "patterns", "group_by": "hostname"}, "group_by"),
    ],
)
def test_dashboard_rejects_bad_log_tiles(root_user, clickhouse_source, chart, field):
    result = save(client_for(root_user), {"source": "clickhouse", **chart})
    assert result["validation"]["result"] is False
    errors = result["validation"]["fields"]["data"]["tiles"]["2"]["chart"]
    assert field in errors, errors


@pytest.mark.django_db
def test_dashboard_log_tile_needs_source_access(test_user, clickhouse_source):
    result = save(client_for(test_user), {"source": "clickhouse", "display": "search"})
    errors = result["validation"]["fields"]["data"]["tiles"]
    assert errors["2"]["chart"]["source"] == ["source clickhouse not found"]


@pytest.mark.django_db
def test_patterns_tile_on_starrocks_is_rejected(root_user, clickhouse_source):
    clickhouse_source.kind = "starrocks"
    clickhouse_source.save()
    result = save(
        client_for(root_user), {"source": "clickhouse", "display": "patterns"}
    )
    errors = result["validation"]["fields"]["data"]["tiles"]
    assert errors["2"]["chart"]["display"] == [
        "patterns are not supported for starrocks sources"
    ]


@pytest.mark.django_db
def test_search_tile_binds_variables_and_dashboard_filter(test_user, clickhouse_source):
    client = grant(test_user, clickhouse_source)
    fetcher = fake_fetcher(cursor={"time": "5", "skip": 1})
    with patch(GET_FETCHERS, return_value={"clickhouse": fetcher}):
        result = post(
            client,
            clickhouse_source,
            "search",
            body(
                query="hostname = $host",
                dashboard_query="level in [$levels]",
                params={"host": "h'1", "levels": ["Error", "Fatal"]},
                columns="hostname",
                limit=20,
                before={"time": "9", "skip": 0},
            ),
        )
    assert result["result"] is True, result
    request = fetcher.fetch_data.call_args.args[0]
    assert request.query == "(hostname = 'h\\'1') and (level in ['Error', 'Fatal'])"
    assert (request.time_from, request.time_to) == (T0, T0 + 3600000)
    assert (request.limit, request.before) == (20, {"time": "9", "skip": 0})
    assert result["data"]["kind"] == "rows"
    assert result["data"]["cursor"] == {"time": "5", "skip": 1}
    assert [c["name"] for c in result["data"]["columns"]] == ["hostname"]


@pytest.mark.django_db
def test_search_tile_defaults_to_the_source_columns(root_user, clickhouse_source):
    clickhouse_source.default_chosen_columns = ["hostname", "message"]
    clickhouse_source.save()
    with patch(GET_FETCHERS, return_value={"clickhouse": fake_fetcher()}):
        result = post(
            client_for(root_user), clickhouse_source, "search", body(columns="")
        )
    names = [c["name"] for c in result["data"]["columns"]]
    assert names == ["hostname", "message"]


@pytest.mark.django_db
def test_search_tile_without_access_is_no_access(test_user, clickhouse_source):
    result = post(client_for(test_user), clickhouse_source, "search", body())
    assert result["result"] is False
    assert result["data"] == {"code": "no_access"}
    result = post(client_for(test_user), clickhouse_source, "patterns", body())
    assert result["data"] == {"code": "no_access"}


@pytest.mark.django_db
def test_search_tile_raw_query_needs_permission(test_user, clickhouse_source):
    client = grant(test_user, clickhouse_source)
    result = post(client, clickhouse_source, "search", body(raw_query="1 = 1"))
    assert result["validation"]["non_field"] == [
        "Insufficient permissions to use source raw queries"
    ]
    grant(test_user, clickhouse_source, SourceRole.RAW_QUERY_USER)
    fetcher = fake_fetcher()
    with patch(GET_FETCHERS, return_value={"clickhouse": fetcher}):
        result = post(client, clickhouse_source, "search", body(raw_query="1 = 1"))
    assert result["result"] is True, result
    assert fetcher.fetch_data.call_args.args[0].raw_query == "1 = 1"


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["search", "patterns"])
@pytest.mark.parametrize(
    "changes, field",
    [
        ({"to": str(T0)}, "to"),
        ({"query": "nope = 1"}, "query"),
        ({"dashboard_query": "nope = 1"}, "dashboard_query"),
        ({"query": "hostname = $host", "params": {"host": [{"a": 1}]}}, "params"),
    ],
)
def test_log_tile_validation(root_user, clickhouse_source, kind, changes, field):
    result = post(client_for(root_user), clickhouse_source, kind, body(**changes))
    assert result["validation"]["result"] is False
    assert field in result["validation"]["fields"], result["validation"]


@pytest.mark.django_db
def test_search_tile_limit_is_bounded(root_user, clickhouse_source):
    result = post(client_for(root_user), clickhouse_source, "search", body(limit=501))
    assert "limit" in result["validation"]["fields"]


@pytest.mark.django_db
def test_search_tile_query_error_is_query_failed(root_user, clickhouse_source):
    fetcher = MagicMock()
    fetcher.fetch_data.side_effect = RuntimeError("boom")
    with patch(GET_FETCHERS, return_value={"clickhouse": fetcher}):
        result = post(client_for(root_user), clickhouse_source, "search", body())
    assert (result["result"], result["errors"]) == (False, ["boom"])
    assert result["data"] == {"code": "query_failed"}


@pytest.mark.django_db
def test_patterns_tile_binds_variables(test_user, clickhouse_source):
    client = grant(test_user, clickhouse_source)
    with patch(FETCH_PATTERNS, return_value=PATTERNS) as fetch:
        result = post(
            client,
            clickhouse_source,
            "patterns",
            body(
                query="hostname = $host",
                dashboard_query="level = 'Error'",
                params={"host": "h1"},
                column="hostname",
                sample=500,
            ),
            qs="?dashboard=d1&tile=t1",
        )
    assert result["result"] is True, result
    assert result["data"] == {"kind": "patterns", **PATTERNS}
    request = fetch.call_args.args[0]
    assert request.query == "(hostname = 'h1') and (level = 'Error')"
    assert (request.column, request.sample) == ("hostname", 500)


@pytest.mark.django_db
def test_patterns_tile_defaults_to_the_body_column(root_user, clickhouse_source):
    with patch(FETCH_PATTERNS, return_value=PATTERNS) as fetch:
        post(client_for(root_user), clickhouse_source, "patterns", body())
    assert fetch.call_args.args[0].column == "message"


@pytest.mark.django_db
def test_patterns_tile_unsupported_kind(root_user, clickhouse_source):
    clickhouse_source.kind = "starrocks"
    clickhouse_source.save()
    result = post(client_for(root_user), clickhouse_source, "patterns", body())
    assert result["validation"]["fields"]["display"] == [
        "patterns are not supported for starrocks sources"
    ]
