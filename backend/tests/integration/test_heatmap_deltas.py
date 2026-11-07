"""P4.1 heatmap and event deltas against the planted slow POST /api/checkout band of the P0.2 otel_traces data."""

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
