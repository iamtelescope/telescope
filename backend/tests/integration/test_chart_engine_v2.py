"""Roadmap P2.2 acceptance against the P0.2 OTel data in a native ClickHouse."""

import math
from datetime import datetime

import pytest
from rest_framework.test import APIClient

from telescope.models import Dashboard
from telescope_alerts.definition import alert_data, resolve
from telescope_alerts.evaluator import query_window
from telescope_alerts.models import Alert
from telescope_alerts.tests.conftest import otel_source

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]

HOUR = 3600 * 1000
ERRORS = [
    {
        "agg": "count",
        "alias": "errors",
        "where": "StatusCode = 'Error'",
        "hidden": True,
    },
    {"agg": "count", "alias": "total", "hidden": True},
    {"agg": "formula", "formula": "errors/total*100", "alias": "error_rate"},
]


@pytest.fixture
def traces(ch_client, ch_settings_dict, otel_db):
    return otel_source(
        ch_client, ch_settings_dict, otel_db, "otel_traces", "otel-traces"
    )


@pytest.fixture
def window(otel_facts):
    start = datetime.fromisoformat(otel_facts["start"][:26] + "+00:00")
    t0 = int(start.timestamp() * 1000)
    return t0, t0 + 24 * HOUR


def chart(user, source, window, **changes):
    body = {
        "from": str(window[0]),
        "to": str(window[1]),
        "query": "",
        "dashboard_query": "",
        "raw_query": "",
        "context_columns": {},
        "display": "table",
        "series": [{"agg": "count"}],
        "group_by": "",
        "granularity": "auto",
        "limit": 10,
    }
    body.update(changes)
    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/ui/v1/sources/{source.slug}/chartData", body, format="json"
    )
    result = response.json()
    assert result["result"] is True, result
    return result["data"]


def rows(ch_client, sql, window, **params):
    return ch_client.query(
        sql, parameters={"f": window[0], "t": window[1], **params}
    ).result_rows


def in_window(otel_db, window_end_inclusive=True):
    op = "<=" if window_end_inclusive else "<"
    return (
        f"FROM `{otel_db}`.otel_traces WHERE Timestamp >= fromUnixTimestamp64Milli(%(f)s)"
        f" AND Timestamp {op} fromUnixTimestamp64Milli(%(t)s)"
    )


def test_group_by_service_and_kind_matches_sql(
    root_user, traces, window, ch_client, otel_db
):
    data = chart(
        root_user,
        traces,
        window,
        group_by="ServiceName, SpanKind",
        series=[{"agg": "count"}, {"agg": "avg", "column": "Duration"}],
    )
    truth = rows(
        ch_client,
        f"SELECT ServiceName, SpanKind, count(), avg(Duration) {in_window(otel_db)}"
        " GROUP BY ServiceName, SpanKind ORDER BY count() DESC, ServiceName, SpanKind LIMIT 11",
        window,
    )
    assert data["truncated"] == (len(truth) == 11)
    assert data["columns"][0]["names"] == ["ServiceName", "SpanKind"]
    assert len(data["rows"]) == 10
    for row, (service, kind, count, avg) in zip(data["rows"], truth):
        assert row["groups"] == [service, kind]
        assert row["group"] == f"{service} · {kind}"
        assert row["values"][0] == count
        assert math.isclose(row["values"][1], avg, rel_tol=1e-9)

    series = chart(
        root_user, traces, window, display="line", group_by="ServiceName, SpanKind"
    )
    top = [f"{s} · {k}" for s, k, *_ in truth[:10]]
    assert [s["group"] for s in series["series"]] == top
    step = series["step_ms"]
    buckets = rows(
        ch_client,
        f"SELECT intDiv(toUnixTimestamp(Timestamp), {step // 1000}) * {step}, ServiceName, SpanKind,"
        f" count() {in_window(otel_db, False)} GROUP BY 1, 2, 3",
        (series["from"], series["to"]),
    )
    expected = {(t, f"{s} · {k}"): n for t, s, k, n in buckets}
    for s in series["series"]:
        for ts, value in zip(series["timestamps"], s["values"]):
            assert value == expected.get((ts, s["group"]), 0)


def test_error_rate_formula_matches_count_if(
    root_user, traces, window, ch_client, otel_db
):
    data = chart(
        root_user, traces, window, display="line", granularity="15m", series=ERRORS
    )
    truth = dict(
        rows(
            ch_client,
            "SELECT intDiv(toUnixTimestamp(Timestamp), 900) * 900000,"
            f" countIf(StatusCode = 'Error') / count() * 100 {in_window(otel_db, False)} GROUP BY 1",
            (data["from"], data["to"]),
        )
    )
    [rate] = [s for s in data["series"] if s["series_index"] == 2]
    assert rate["name"] == "error_rate"
    assert any(v for v in rate["values"])
    for ts, value in zip(data["timestamps"], rate["values"]):
        if ts not in truth:
            assert value is None
        else:
            assert abs(value - truth[ts]) <= 1e-9

    number = chart(root_user, traces, window, display="number", series=ERRORS)
    [(total_rate,)] = rows(
        ch_client,
        f"SELECT countIf(StatusCode = 'Error') / count() * 100 {in_window(otel_db)}",
        window,
    )
    assert abs(number["value"] - total_rate) <= 1e-9


def test_pie_totals_equal_table_totals(root_user, traces, window):
    common = dict(group_by="ServiceName", series=[{"agg": "count"}], limit=100)
    pie = chart(root_user, traces, window, display="pie", **common)
    table = chart(root_user, traces, window, display="table", **common)
    assert pie["rows"] == table["rows"]
    total = sum(r["values"][0] for r in pie["rows"])
    assert total == sum(r["values"][0] for r in table["rows"]) > 0


def test_last_value_and_any(root_user, traces, window, ch_client, otel_db):
    data = chart(
        root_user,
        traces,
        window,
        group_by="ServiceName",
        series=[
            {"agg": "last_value", "column": "Duration"},
            {"agg": "any", "column": "Duration", "where": "SpanKind = 'Server'"},
        ],
    )
    truth = dict(
        rows(
            ch_client,
            f"SELECT ServiceName, argMax(Duration, Timestamp) {in_window(otel_db)} GROUP BY 1",
            window,
        )
    )
    assert data["rows"]
    for row in data["rows"]:
        assert row["values"][0] == truth[row["group"]]


def test_compare_and_sparkline(root_user, traces, window):
    day = (window[0] + 12 * HOUR, window[1])
    line = chart(root_user, traces, day, display="line", granularity="1h", compare=True)
    previous = chart(
        root_user,
        traces,
        (day[0] - 12 * HOUR, day[0]),
        display="line",
        granularity="1h",
    )
    assert [s.get("previous", False) for s in line["series"]] == [False, True]
    assert line["series"][1]["values"] == previous["series"][0]["values"]
    assert line["previous_offset_ms"] == 12 * HOUR

    number = chart(
        root_user, traces, day, display="number", compare=True, sparkline=True
    )
    before = chart(root_user, traces, (day[0] - 12 * HOUR, day[0]), display="number")
    assert number["previous_value"] == before["value"]
    assert sum(number["sparkline"]["values"]) == number["value"]


V1_TILES = [
    {"display": "line", "series": [{"agg": "count"}], "group_by": "ServiceName"},
    {
        "display": "stacked_bar",
        "series": [
            {"agg": "count"},
            {"agg": "quantile", "column": "Duration", "level": 0.95},
        ],
        "group_by": "",
    },
    {"display": "number", "series": [{"agg": "sum", "column": "Duration"}]},
    {
        "display": "table",
        "series": [{"agg": "uniq", "column": "TraceId"}],
        "group_by": "SpanKind",
    },
    {
        "display": "bar",
        "series": [{"agg": "max", "column": "Duration"}],
        "group_by": "ServiceName",
    },
]


@pytest.mark.parametrize("version", [1, 2])
def test_v1_and_v2_dashboards_serve_the_same_chart_data(
    root_user, traces, window, version
):
    tiles = [
        {
            "id": f"t{i}",
            "x": 0,
            "y": i * 8,
            "w": 12,
            "h": 8,
            "title": "",
            "chart": {"source": traces.slug, "query": "", "raw_query": "", **c},
        }
        for i, c in enumerate(V1_TILES)
    ]
    data = {
        "time": {"from": "now-1h", "to": "now"},
        "query": "",
        "refresh": "off",
        "tiles": tiles,
    }
    if version == 2:
        data.update(version=2, variables=[])
    dashboard = Dashboard.objects.create(
        slug="old", name="old", owner=root_user, updated_by=root_user, data=data
    )
    client = APIClient()
    client.force_login(root_user)
    served = client.get(f"/ui/v1/dashboards/{dashboard.slug}").json()["data"]["data"]
    assert served["version"] == 3 and served["sections"] == []
    keys = {
        "timeseries": {"kind", "from", "to", "granularity", "step_ms"}
        | {"timestamps", "series", "truncated"},
        "number": {"kind", "from", "to", "value"},
        "table": {"kind", "from", "to", "columns", "rows", "truncated"},
    }
    for old, new in zip(tiles, served["tiles"]):
        assert old == new
        body = {k: v for k, v in new["chart"].items() if k != "source"}
        result = chart(root_user, traces, window, **body)
        # The v1 wire shape: no v2 keys appear for a v1 tile; `debug` is the RAW_QUERY user's SQL.
        assert set(result) - {"debug"} == keys[result["kind"]]
        for item in result.get("series", []) + result.get("rows", []):
            assert set(item) <= {"name", "group", "series_index", "values"}


def test_tile_alert_with_series_filter(root_user, traces, window, ch_client, otel_db):
    dashboard = Dashboard.objects.create(
        slug="errors",
        name="errors",
        owner=root_user,
        updated_by=root_user,
        data={
            "version": 3,
            "time": {"from": "now-1h", "to": "now"},
            "query": "",
            "refresh": "off",
            "variables": [],
            "sections": [],
            "tiles": [
                {
                    "id": "e",
                    "x": 0,
                    "y": 0,
                    "w": 12,
                    "h": 8,
                    "chart": {
                        "source": traces.slug,
                        "display": "line",
                        "series": ERRORS,
                        "query": "",
                        "raw_query": "",
                        "group_by": "ServiceName",
                    },
                }
            ],
        },
    )
    alert = Alert.objects.create(
        name="errors",
        owner=root_user,
        kind="tile",
        dashboard=dashboard,
        tile_id="e",
        series_index=0,
        interval="1h",
        threshold_type="above",
        threshold=1,
    )
    aq = resolve(root_user, alert_data(alert))
    start, end = window[0], window[0] + 24 * HOUR
    truth = dict(
        rows(
            ch_client,
            f"SELECT ServiceName, countIf(StatusCode = 'Error') {in_window(otel_db, False)} GROUP BY 1",
            (start, end),
        )
    )
    got = query_window(aq, start, end)
    assert got == {k: float(v) for k, v in truth.items()}
    assert got["payment"] > 0
