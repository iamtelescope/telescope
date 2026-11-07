import pytest

from tests.api.dashboards.test_views import client_for
from tests.data import get_dashboard_data

# A tile as the chart explorer's TileEditor emits it, with every optional key set.
FULL_CHART = {
    "source": "clickhouse",
    "display": "line",
    "series": [
        {
            "agg": "quantile",
            "column": "thread_id",
            "level": 0.99,
            "alias": "p99",
            "where": "thread_name = 'x'",
            "color": "#ff0000",
        },
        {"agg": "count", "alias": "total", "hidden": True},
        {"agg": "formula", "formula": "p99 / total", "alias": "ratio"},
    ],
    "query": "hostname = 'a'",
    "raw_query": "1 = 1",
    "context_columns": {},
    "group_by": "hostname, thread_name",
    "granularity": "5m",
    "limit": 7,
    "number_format": {
        "unit": "duration_ms",
        "decimals": 1,
        "prefix": "~",
        "suffix": " ms",
        "compact": True,
    },
    "compare": True,
}
TILE = {
    "id": "c1",
    "x": 0,
    "y": 0,
    "w": 12,
    "h": 8,
    "title": "p99 by host",
    "description": "From /charts",
    "chart": FULL_CHART,
}


def dashboard_body(tiles):
    data = get_dashboard_data()
    data["tiles"] = tiles
    return {"name": "Charts", "description": "", "shared": False, "data": data}


@pytest.mark.django_db
def test_chart_explorer_tile_round_trips(root_user, clickhouse_source):
    client = client_for(root_user)
    created = client.post("/ui/v1/dashboards", dashboard_body([TILE]), format="json")
    created = created.json()
    assert created["result"] is True, created
    slug = created["data"]["slug"]
    got = client.get(f"/ui/v1/dashboards/{slug}").json()["data"]
    assert got["data"]["tiles"] == [TILE]

    # Appending to an existing dashboard, as AddToDashboard does, keeps the tile as well.
    appended = {**TILE, "id": "c2", "y": 8}
    body = dashboard_body([TILE, appended])
    body["version"] = got["version"]
    updated = client.patch(f"/ui/v1/dashboards/{slug}", body, format="json").json()
    assert updated["result"] is True, updated
    got = client.get(f"/ui/v1/dashboards/{slug}").json()["data"]
    assert got["data"]["tiles"] == [TILE, appended]


@pytest.mark.django_db
def test_alert_prefilled_from_a_chart(root_user, clickhouse_source):
    # What "Create alert" passes for FULL_CHART: the first series, its filter joined to the query.
    series = FULL_CHART["series"][0]
    body = {
        "name": "p99 by host",
        "kind": "search",
        "source": "clickhouse",
        "query": f"({FULL_CHART['query']}) and ({series['where']})",
        "raw_query": FULL_CHART["raw_query"],
        "group_by": FULL_CHART["group_by"],
        "series": {"agg": "quantile", "column": "thread_id", "level": 0.99},
        "interval": "5m",
        "threshold_type": "above",
        "threshold": 1,
    }
    client = client_for(root_user)
    created = client.post("/ui/v1/alerts", body, format="json").json()
    assert created["result"] is True, created
    alert = created["data"]
    assert alert["query"] == "(hostname = 'a') and (thread_name = 'x')"
    assert alert["group_by"] == "hostname, thread_name"
    assert alert["series"] == {"agg": "quantile", "column": "thread_id", "level": 0.99}
