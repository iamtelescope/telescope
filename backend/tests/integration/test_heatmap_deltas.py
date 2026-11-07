"""P4.1 heatmap and event deltas against the planted slow POST /api/checkout band of the P0.2 otel_traces data."""

import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from telescope.fetchers.chart import pick_granularity
from telescope.fetchers.deltas import Selection, fetch_deltas, fetch_heatmap
from telescope.models import Source, SourceColumn

pytestmark = pytest.mark.clickhouse

SLOW_NS = 1_500_000_000


def ms(iso):
    return int(datetime.fromisoformat(iso[:26] + "+00:00").timestamp() * 1000)


@pytest.fixture
def traces(ch_settings_dict, ch_client, otel_db):
    rows = ch_client.query(
        "SELECT name, type FROM system.columns WHERE database = {db:String} AND table = 'otel_traces'",
        parameters={"db": otel_db},
    ).result_rows
    source = Mock(spec=Source)
    source.kind = "clickhouse"
    source.slug = "traces"
    source.data = {
        "database": otel_db,
        "table": "otel_traces",
        "settings": "",
        "otel": {"signal": "traces", "roles": {"span_id": "SpanId"}},
    }
    source.time_column, source.date_column = "Timestamp", ""
    source._columns = {
        name: SourceColumn(name, "", t, False, True, True, True, []) for name, t in rows
    }
    source.columns = dict(source._columns)
    source.conn = Mock(
        data={
            "host": ch_settings_dict["host"],
            "port": ch_settings_dict["port"],
            "user": ch_settings_dict["username"],
            "password": ch_settings_dict["password"],
            "ssl": False,
            "verify": False,
        }
    )
    return source


@pytest.fixture
def window(otel_facts):
    return ms(otel_facts["start"]), ms(otel_facts["end"])


def test_heatmap_counts_equal_sql_ground_truth(traces, window, ch_client, otel_db):
    query = "ServiceName='frontend'"
    result = fetch_heatmap(
        Selection(traces, window[0], window[1], "Duration", query=query)
    ).as_dict()
    edges, step = result["y_edges"], result["step_ms"]
    assert result["kind"] == "heatmap"
    assert (result["granularity"], step) == pick_granularity(*window)
    # Ground truth from plain range predicates over the returned edges.
    cases = ", ".join(
        f"({'1' if i == 0 else f'Duration >= {edges[i]!r}'}"
        f" AND {'1' if i == len(edges) - 2 else f'Duration < {edges[i + 1]!r}'}, {i})"
        for i in range(len(edges) - 1)
    )
    truth = ch_client.query(
        f"SELECT intDiv(toUnixTimestamp64Milli(toDateTime64(Timestamp, 3)), {step}) * {step} AS t,"
        f" arrayFirst(x -> x.1, [{cases}]).2 AS b, count()"
        f" FROM {otel_db}.otel_traces WHERE ServiceName = 'frontend'"
        f" AND Timestamp BETWEEN fromUnixTimestamp64Milli({window[0]}) AND fromUnixTimestamp64Milli({window[1]})"
        " GROUP BY t, b",
    ).result_rows
    ts = result["timestamps"]
    got = {(ts[t], b): n for t, b, n in result["cells"]}
    assert got == {(int(t), int(b)): int(n) for t, b, n in truth}
    assert sum(got.values()) == result["total"] > 40_000
    low, high = ch_client.query(
        f"SELECT min(Duration), max(Duration) FROM {otel_db}.otel_traces WHERE ServiceName = 'frontend'"
    ).result_rows[0]
    assert (
        len(edges) - 1 <= 40
        and edges[0] <= low < edges[1]
        and edges[-2] <= high <= edges[-1]
    )


def test_slow_band_ranks_span_name_first(traces, window, ch_client, otel_db):
    selection = Selection(traces, window[0], window[1], "Duration")
    outlier = {"y_min": SLOW_NS, "y_max": 1e12, "t_min": window[0], "t_max": window[1]}
    result = fetch_deltas(selection, outlier, 5000)
    expected = ch_client.command(
        f"SELECT count() FROM {otel_db}.otel_traces WHERE Duration >= {SLOW_NS}"
    )
    assert result["outlier"] == {"total": expected, "sample": expected}
    assert result["inlier"]["sample"] == 5000
    visible = [p for p in result["properties"] if not p["hidden"]]
    top = visible[0]
    assert top["key"] == "SpanName"
    best = top["values"][0]
    assert (
        best["value"] == "POST /api/checkout" and best["outlier"] > 50 > best["inlier"]
    )
    keys = [p["key"] for p in visible]
    assert keys.index("SpanAttributes.http.route") < keys.index("ServiceName")
    hidden = {p["key"]: p["hidden_reason"] for p in result["properties"] if p["hidden"]}
    assert hidden["TraceId"] == hidden["SpanId"] == "denylist"
    assert hidden["Duration"] == "high_cardinality"


def test_deltas_is_stable_for_a_span_id_source(traces, window):
    selection = Selection(traces, window[0], window[1], "Duration")
    outlier = {"y_min": SLOW_NS, "y_max": 1e12, "t_min": window[0], "t_max": window[1]}
    first = fetch_deltas(selection, outlier, 500)
    assert first == fetch_deltas(selection, outlier, 500)


@pytest.fixture
def scratch(traces, ch_client):
    db = f"telescope_test_deltas_{uuid.uuid4().hex[:8]}"
    ch_client.command(f"CREATE DATABASE {db}")
    ch_client.command(
        f"CREATE TABLE {db}.t (Timestamp DateTime64(3), v Nullable(Float64))"
        " ENGINE = MergeTree ORDER BY Timestamp"
    )
    values = (
        ["0"] * 50
        + [str(v) for v in (1, 2, 5, 10, 50, 100) for _ in range(100)]
        + ["-5"] * 20
        + ["NULL"] * 300
        + ["nan"] * 10
        + ["inf"]
    )
    rows = ", ".join(
        f"('2026-01-01 00:00:{i % 60:02d}', {v})" for i, v in enumerate(values)
    )
    ch_client.command(f"INSERT INTO {db}.t VALUES {rows}")
    traces.data = {"database": db, "table": "t", "settings": ""}
    traces._columns = {
        name: SourceColumn(name, "", t, False, True, True, True, [])
        for name, t in [("Timestamp", "DateTime64(3)"), ("v", "Nullable(Float64)")]
    }
    yield Selection(traces, ms("2026-01-01T00:00:00"), ms("2026-01-01T01:00:00"), "v")
    ch_client.command(f"DROP DATABASE {db}")


def test_heatmap_skips_null_nan_and_inf(scratch):
    result = fetch_heatmap(scratch).as_dict()
    rows = {}
    for _, b, n in result["cells"]:
        rows[b] = rows.get(b, 0) + n
    assert result["total"] == sum(rows.values()) == 670
    edges = result["y_edges"]
    assert edges[-2] < 100 <= edges[-1] and rows[len(edges) - 2] == 100


def test_deltas_selection_holds_exactly_the_selected_heatmap_rows(scratch):
    result = fetch_heatmap(scratch).as_dict()
    edges, top = result["y_edges"], len(result["y_edges"]) - 2
    rows = {}
    for _, b, n in result["cells"]:
        rows[b] = rows.get(b, 0) + n
    ts = result["timestamps"]
    for b in range(top + 1):
        # As heatmap.js snapSelection sends it: open bottom and top rows, exclusive y_max.
        outlier = {
            "y_min": None if b == 0 else edges[b],
            "y_max": None if b == top else edges[b + 1],
            "t_min": ts[0],
            "t_max": ts[-1] + result["step_ms"] - 1,
        }
        deltas = fetch_deltas(scratch, outlier, 10)
        assert deltas["outlier"]["total"] == rows.get(b, 0), (b, edges[b])
        assert deltas["inlier"]["total"] == 670 - rows.get(b, 0)
    assert rows[0] == 170  # the negatives, zeros and ones
