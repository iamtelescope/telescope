"""Roadmap P3.1 acceptance: OTel metric series against the P0.2 data in a native ClickHouse."""

from collections import defaultdict
from datetime import datetime
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from telescope.models import Dashboard
from telescope_alerts.definition import alert_data, resolve
from telescope_alerts.evaluator import query_window
from telescope_alerts.models import Alert
from telescope_alerts.tests.conftest import otel_source

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]

HOUR = 3600 * 1000
REQUESTS = {"name": "http.server.requests", "type": "sum"}
DURATION = {"name": "http.server.request.duration", "type": "histogram"}
CPU = {"name": "k8s.pod.cpu.utilization", "type": "gauge"}
TABLES = {
    k: f"otel_metrics_{k}"
    for k in ["gauge", "sum", "histogram", "exponential_histogram", "summary"]
}


def metrics_source(ch_client, ch_settings_dict, db, slug="otel-metrics"):
    source = otel_source(ch_client, ch_settings_dict, db, "otel_metrics_gauge", slug)
    source.time_column = "TimeUnix"
    source.data = {
        **source.data,
        "otel": {"signal": "metrics", "roles": {}, "metric_tables": TABLES},
    }
    source.save()
    return source


@pytest.fixture
def metrics(ch_client, ch_settings_dict, otel_db):
    return metrics_source(ch_client, ch_settings_dict, otel_db)


@pytest.fixture
def start(otel_facts):
    return int(
        datetime.fromisoformat(otel_facts["start"][:26] + "+00:00").timestamp() * 1000
    )


def post(user, source, body, path="chartData"):
    client = APIClient()
    client.force_login(user)
    return client.post(
        (
            f"/ui/v1/otel/{source.slug}/{path}"
            if path.startswith("metrics")
            else f"/ui/v1/sources/{source.slug}/{path}"
        ),
        body,
        format="json",
    ).json()


def chart(user, source, window, series, **changes):
    body = {
        "from": str(window[0]),
        "to": str(window[1]),
        "query": "",
        "raw_query": "",
        "context_columns": {},
        "display": "line",
        "series": series,
        "group_by": "",
        "granularity": "5m",
        "limit": 10,
        **changes,
    }
    result = post(user, source, body)
    assert result["result"] is True, result
    return result["data"]


def metric(base, agg, **extra):
    return {"agg": "metric", "metric": {**base, "agg": agg, **extra}}


def reference_increase(ch_client, db, window, step_ms, where, clamp=False):
    """Per-bucket sum of per-series deltas from raw points; a drop restarts the counter, as in
    Prometheus increase(), or counts 0 with `clamp`."""
    rows = ch_client.query(
        f"SELECT ResourceAttributes, Attributes, toUnixTimestamp(TimeUnix) * 1000, Value"
        f" FROM `{db}`.otel_metrics_sum WHERE MetricName = 'http.server.requests' AND {where}"
        " ORDER BY TimeUnix"
    ).result_rows
    last = {}
    out = defaultdict(float)
    for res, attrs, ts, value in rows:
        key = (tuple(sorted(res.items())), tuple(sorted(attrs.items())))
        prev = last.get(key)
        last[key] = value
        if prev is None or not window[0] <= ts < window[1]:
            continue
        delta = (0 if clamp else value) if value < prev else value - prev
        out[ts // step_ms * step_ms, attrs["http.route"]] += delta
    return out


def test_increase_per_5m_matches_python_reference_across_the_reset(
    root_user, metrics, ch_client, otel_db, otel_facts, start
):
    reset = start + 6 * HOUR
    assert otel_facts["counter_reset"]["at"].startswith("2026-01-01T06:00")
    window = (reset - HOUR, reset + HOUR)
    data = chart(
        root_user,
        metrics,
        window,
        [metric(REQUESTS, "increase")],
        query="ServiceName = 'frontend'",
        group_by="Attributes.http.route",
    )
    truth = reference_increase(
        ch_client, otel_db, window, 300000, "ServiceName = 'frontend'"
    )
    assert data["step_ms"] == 300000 and len(data["series"]) == 4
    reset_bucket = data["timestamps"].index(reset)
    for s in data["series"]:
        values = [truth.get((ts, s["group"]), 0) for ts in data["timestamps"]]
        assert s["values"] == pytest.approx(values)
        assert all(v >= 0 for v in s["values"])
    # The point after the reset counts in full, so the bucket holds more than clamped deltas.
    clamped = reference_increase(
        ch_client, otel_db, window, 300000, "ServiceName = 'frontend'", clamp=True
    )
    checkout = next(s for s in data["series"] if s["group"] == "/api/checkout")
    assert checkout["values"][reset_bucket] > clamped[reset, "/api/checkout"] > 0

    rate = chart(
        root_user,
        metrics,
        window,
        [metric(REQUESTS, "rate")],
        query="ServiceName = 'frontend'",
    )
    totals = defaultdict(float)
    for (ts, _), v in truth.items():
        totals[ts] += v
    assert rate["series"][0]["values"] == pytest.approx(
        [totals.get(ts, 0) / 300 for ts in rate["timestamps"]]
    )


def test_histogram_p95_of_checkout_is_near_the_planted_value(
    root_user, metrics, otel_facts, start
):
    planted = otel_facts["slow_endpoint"]["p95_ms"] / 1000
    window = (start, start + 24 * HOUR)
    data = chart(
        root_user,
        metrics,
        window,
        [metric(DURATION, "p95")],
        display="table",
        group_by="Attributes.http.route",
        query="ServiceName = 'frontend'",
    )
    by_route = {r["group"]: r["values"][0] for r in data["rows"]}
    # The planted value sits in the (1, 2.5] bucket, so one bucket width is 1.5 s.
    assert abs(by_route["/api/checkout"] - planted) <= 1.5
    assert data["rows"][0]["group"] == "/api/checkout"
    assert all(v < 0.5 for g, v in by_route.items() if g != "/api/checkout")

    line = chart(
        root_user,
        metrics,
        window,
        [
            metric(
                DURATION,
                "p95",
                attrs_filter="Attributes.'http.route' = '/api/checkout'",
            )
        ],
        granularity="1h",
    )
    values = [v for v in line["series"][0]["values"] if v is not None]
    assert len(values) == 24 and all(abs(v - planted) <= 1.5 for v in values)


def test_gauge_max_per_pod_finds_the_restarting_pod(
    root_user, metrics, otel_facts, start
):
    planted = otel_facts["restarting_pod"]
    window = (start, start + 24 * HOUR)
    data = chart(
        root_user,
        metrics,
        window,
        [metric(CPU, "max")],
        display="bar",
        group_by="ResourceAttributes.k8s.pod.name",
        limit=20,
    )
    assert len(data["rows"]) == 20
    top = data["rows"][0]
    assert top["group"] == planted["pod"]
    assert abs(top["values"][0] - planted["cpu_utilization"]) < 0.02
    assert data["rows"][1]["values"][0] < 0.7

    series = chart(
        root_user,
        metrics,
        window,
        [metric(CPU, "avg"), metric(CPU, "last")],
        group_by="ResourceAttributes.'k8s.pod.name'",
        granularity="1h",
        limit=3,
    )
    assert series["truncated"] is True
    assert series["series"][0]["group"] == planted["pod"]
    assert all(abs(v - 0.95) < 0.02 for v in series["series"][0]["values"])


def test_metric_formula_and_number(root_user, metrics, start):
    window = (start + 12 * HOUR, start + 13 * HOUR)
    errors = metric(
        REQUESTS, "increase", attrs_filter="Attributes.'http.route' = '/api/checkout'"
    )
    data = chart(
        root_user,
        metrics,
        window,
        [
            {**errors, "alias": "a", "hidden": True},
            {**metric(REQUESTS, "increase"), "alias": "b", "hidden": True},
            {"agg": "formula", "formula": "a / b * 100", "alias": "share"},
        ],
        display="number",
        query="ServiceName = 'frontend'",
    )
    a, b, share = data["values"]
    assert 0 < a < b and share == pytest.approx(a / b * 100)


def test_metric_names_and_attributes(
    root_user, metrics, otel_facts, start, ch_client, otel_db
):
    window = {"from": start, "to": start + 24 * HOUR}
    result = post(root_user, metrics, window, "metrics/names")
    assert result["result"], result
    names = {(m["name"], m["type"]) for m in result["data"]["metrics"]}
    truth = set()
    for kind, table in TABLES.items():
        for (name,) in ch_client.query(
            f"SELECT DISTINCT MetricName FROM `{otel_db}`.`{table}`"
        ).result_rows:
            truth.add((name, kind))
    assert names == truth and len(truth) == 9

    keys = post(root_user, metrics, {**window, **DURATION}, "metrics/attributes")
    assert keys["result"], keys
    paths = {k["path"] for k in keys["data"]["keys"]}
    assert {"Attributes.http.route", "ResourceAttributes.k8s.namespace.name"} <= paths
    values = post(
        root_user,
        metrics,
        {**window, **DURATION, "key": "Attributes.http.route"},
        "metrics/attributes",
    )
    assert "/api/checkout" in values["data"]["values"]


def test_metric_series_validation(
    root_user, metrics, ch_client, ch_settings_dict, otel_db, start
):
    window = (start, start + HOUR)
    body = {
        "from": str(window[0]),
        "to": str(window[1]),
        "display": "line",
        "series": [metric(CPU, "rate")],
    }
    result = post(root_user, metrics, body)
    assert result["validation"]["fields"]["series"]["0"]["metric"]["agg"]
    body["series"] = [metric(CPU, "max"), {"agg": "count"}]
    assert post(root_user, metrics, body)["validation"]["fields"]["series"]["1"]["agg"]
    logs = otel_source(ch_client, ch_settings_dict, otel_db, "otel_logs", "plain-logs")
    body["series"] = [metric(CPU, "max")]
    errors = post(root_user, logs, body)["validation"]["fields"]["series"]["0"]
    assert errors["metric"] == ["source is not an OTel metrics source"]
    # Non-metric charts on the metrics source still read its gauge table.
    plain = chart(root_user, metrics, window, [{"agg": "count"}], display="number")
    [(count,)] = ch_client.query(
        f"SELECT count() FROM `{otel_db}`.otel_metrics_gauge WHERE TimeUnix BETWEEN"
        f" fromUnixTimestamp64Milli({window[0]}) AND fromUnixTimestamp64Milli({window[1]})"
    ).result_rows
    assert plain["value"] == count


def test_tile_alert_on_a_metric_tile(root_user, metrics, otel_facts, start):
    dashboard = Dashboard.objects.create(
        name="metrics",
        owner=root_user,
        data={
            "version": 3,
            "time": {"from": "now-1h", "to": "now"},
            "query": "",
            "refresh": "off",
            "variables": [],
            "sections": [],
            "tiles": [
                {
                    "id": "cpu",
                    "x": 0,
                    "y": 0,
                    "w": 6,
                    "h": 4,
                    "chart": {
                        "source": metrics.slug,
                        "display": "line",
                        "series": [metric(CPU, "max")],
                        "query": "",
                        "raw_query": "",
                        "context_columns": {},
                        "group_by": "ResourceAttributes.k8s.pod.name",
                        "granularity": "auto",
                        "limit": 10,
                    },
                }
            ],
        },
    )
    alert = Alert.objects.create(
        name="hot pod",
        owner=root_user,
        kind="tile",
        dashboard=dashboard,
        tile_id="cpu",
        interval="5m",
        threshold_type="above",
        threshold=0.9,
    )
    aq = resolve(root_user, alert_data(alert))
    window = start + 3 * HOUR
    values = query_window(aq, window, window + 300000)
    hot = {g: v for g, v in values.items() if v is not None and v > 0.9}
    assert list(hot) == [otel_facts["restarting_pod"]["pod"]]


SYNTH_DB = "telescope_test_p31"
T0 = 1767225600  # 2026-01-01 00:00:00 UTC


@pytest.fixture
def synthetic(ch_client, ch_settings_dict, otel_db):
    """Empty copies of the metric tables plus hand-made exponential histogram and summary points."""
    ch_client.command(f"CREATE DATABASE IF NOT EXISTS {SYNTH_DB}")
    for table in TABLES.values():
        ch_client.command(f"DROP TABLE IF EXISTS {SYNTH_DB}.{table}")
        ch_client.command(f"CREATE TABLE {SYNTH_DB}.{table} AS `{otel_db}`.{table}")
    columns = [
        "MetricName",
        "Attributes",
        "StartTimeUnix",
        "TimeUnix",
        "AggregationTemporality",
        "Scale",
        "ZeroCount",
        "PositiveOffset",
        "PositiveBucketCounts",
    ]
    start, later = T0 - 600, T0 + 30
    exp = [
        # Cumulative at scale 0, buckets (1,2], (2,4], (4,8].
        ("exp", {"s": "a"}, start, T0, 2, 0, 0, 0, [0, 0, 0]),
        ("exp", {"s": "a"}, start, T0 + 60, 2, 0, 0, 0, [10, 0, 0]),
        ("exp", {"s": "a"}, start, T0 + 120, 2, 0, 0, 0, [10, 0, 10]),
        # Delta at scale 1: index 2 is (2, 2.83], index 1 of (2,4] at scale 0.
        ("exp", {"s": "b"}, start, T0 + 120, 1, 1, 0, 2, [5]),
        # A restart (new StartTimeUnix) counts its points from zero.
        ("exp.reset", {}, start, T0, 2, 0, 0, 0, [0, 4]),
        ("exp.reset", {}, start, T0 + 60, 2, 0, 0, 0, [0, 6]),
        ("exp.reset", {}, later, T0 + 120, 2, 0, 0, 0, [3]),
    ]
    ch_client.insert(
        f"{SYNTH_DB}.otel_metrics_exponential_histogram",
        [
            [n, a, datetime.utcfromtimestamp(s), datetime.utcfromtimestamp(t), *rest]
            for n, a, s, t, *rest in exp
        ],
        column_names=columns,
    )
    summary = [
        ("rpc", {"s": "a"}, T0 + 60, [0.5, 0.95], [1.0, 3.0]),
        ("rpc", {"s": "b"}, T0 + 60, [0.5, 0.95], [2.0, 5.0]),
        ("rpc", {"s": "c"}, T0 + 60, [0.5], [9.0]),
    ]
    ch_client.insert(
        f"{SYNTH_DB}.otel_metrics_summary",
        [[n, a, datetime.utcfromtimestamp(t), q, v] for n, a, t, q, v in summary],
        column_names=[
            "MetricName",
            "Attributes",
            "TimeUnix",
            "ValueAtQuantiles.Quantile",
            "ValueAtQuantiles.Value",
        ],
    )
    yield metrics_source(ch_client, ch_settings_dict, SYNTH_DB, "synthetic-metrics")
    ch_client.command(f"DROP DATABASE IF EXISTS {SYNTH_DB}")


def number(user, source, base, agg):
    window = ((T0 + 30) * 1000, (T0 + 150) * 1000)
    return chart(user, source, window, [metric(base, agg)], display="number")["value"]


def test_exponential_histogram_quantiles(root_user, synthetic):
    exp = {"name": "exp", "type": "exponential_histogram"}
    # 10 in (1,2], 5 in (2,4], 10 in (4,8]; Prometheus interpolates on a log2 scale.
    assert number(root_user, synthetic, exp, "p50") == pytest.approx(2**1.5)
    assert number(root_user, synthetic, exp, "p95") == pytest.approx(
        2 ** (2 + 8.75 / 10)
    )
    reset = {"name": "exp.reset", "type": "exponential_histogram"}
    # 2 in (2,4] before the restart, 3 in (1,2] after it.
    assert number(root_user, synthetic, reset, "p50") == pytest.approx(2 ** (2.5 / 3))


def test_summary_quantile_passthrough(root_user, synthetic):
    rpc = {"name": "rpc", "type": "summary"}
    assert number(root_user, synthetic, rpc, "p50") == pytest.approx(4.0)
    assert number(root_user, synthetic, rpc, "p95") == pytest.approx(4.0)
    assert number(root_user, synthetic, rpc, "p99") is None


def test_exponential_histogram_negative_buckets_rank_first(
    root_user, synthetic, ch_client
):
    # Delta at scale 0: 10 in [-4,-2), 5 zeros, 5 in (1,2].
    ch_client.insert(
        f"{SYNTH_DB}.otel_metrics_exponential_histogram",
        [["exp.neg", datetime.utcfromtimestamp(T0 + 60), 1, 0, 5, 0, [5], 1, [10]]],
        column_names=[
            "MetricName",
            "TimeUnix",
            "AggregationTemporality",
            "Scale",
            "ZeroCount",
            "PositiveOffset",
            "PositiveBucketCounts",
            "NegativeOffset",
            "NegativeBucketCounts",
        ],
    )
    neg = {"name": "exp.neg", "type": "exponential_histogram"}
    assert number(root_user, synthetic, neg, "p50") == pytest.approx(-2.0)
    assert number(root_user, synthetic, neg, "p95") == pytest.approx(2**0.8)


SUM_COLUMNS = [
    "MetricName",
    "ScopeName",
    "Attributes",
    "TimeUnix",
    "Value",
    "AggregationTemporality",
    "IsMonotonic",
]


def insert_sums(ch_client, points):
    ch_client.insert(
        f"{SYNTH_DB}.otel_metrics_sum",
        [
            [n, sc, a, datetime.utcfromtimestamp(t), v, 2, m]
            for n, sc, a, t, v, m in points
        ],
        column_names=SUM_COLUMNS,
    )


def increase(user, source, name):
    window = (T0 * 1000, (T0 + 300) * 1000)
    series = [metric({"name": name, "type": "sum"}, "increase")]
    return chart(user, source, window, series, display="number")["value"]


def test_counter_reset_counts_the_restarted_value_per_scope(
    root_user, synthetic, ch_client
):
    # Same name and attributes in two scopes are two streams; s1 resets at its 4th point.
    s1 = [0, 100, 200, 10, 110]
    s2 = [5000, 5001, 5002, 5003]
    insert_sums(
        ch_client,
        [("req", "s1", {"k": "a"}, T0 + 60 * i, v, True) for i, v in enumerate(s1)]
        + [
            ("req", "s2", {"k": "a"}, T0 + 30 + 60 * i, v, True)
            for i, v in enumerate(s2)
        ],
    )
    # Prometheus increase(): 100 + 100 + 10 + 100 for s1, 3 for s2.
    assert increase(root_user, synthetic, "req") == 313


def test_up_down_sum_keeps_its_decreases(root_user, synthetic, ch_client):
    points = [10, 30, 20, 25]
    insert_sums(
        ch_client,
        [("queue", "s", {}, T0 + 60 * i, v, False) for i, v in enumerate(points)],
    )
    assert increase(root_user, synthetic, "queue") == 15


def test_grouped_metric_chart_reads_only_the_top_groups(
    root_user, synthetic, ch_client
):
    ch_client.insert(
        f"{SYNTH_DB}.otel_metrics_gauge",
        [
            ["temp", {"k": f"g{g:02}", "r": "x"}, datetime.utcfromtimestamp(T0 + t), g]
            for g in range(30)
            for t in (0, 300, 600)
        ],
        column_names=["MetricName", "Attributes", "TimeUnix", "Value"],
    )
    sizes = []

    def counting(client, sql, **kw):
        result = client.query(sql, **kw)
        sizes.append(len(result.result_rows))
        return result

    window = (T0 * 1000, (T0 + 900) * 1000)
    series = [metric({"name": "temp", "type": "gauge"}, "max")]
    with patch("telescope_otel.metrics_sql._client_query", counting):
        line = chart(
            root_user, synthetic, window, series, group_by="Attributes.k", limit=3
        )
        table = chart(
            root_user,
            synthetic,
            window,
            series,
            display="table",
            group_by="Attributes.k, Attributes.r",
            limit=3,
        )
    assert [s["group"] for s in line["series"]] == ["g29", "g28", "g27"]
    assert line["truncated"] is True
    assert [r["group"] for r in table["rows"]] == ["g29 · x", "g28 · x", "g27 · x"]
    assert table["truncated"] is True
    # Top query, then 4 groups x 3 buckets; then top query, then 4 groups; never all 30.
    assert sizes == [4, 12, 4, 4]
