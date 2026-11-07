from datetime import datetime

import pytest

from telescope.fetchers.chart import agg_expression
from telescope.fetchers.deltas import (
    bucket_sql,
    distribution_score,
    flatten,
    is_denylisted,
    is_high_cardinality,
    log_edges,
    property_statistics,
    rank_properties,
    semantic_boost,
    shares,
)
from telescope.serializers.dashboard import (
    ChartSeriesSerializer,
    QueryChartSerializer,
    TileSeriesSerializer,
    chart_shape_errors,
)

COLUMNS = {
    "TraceId": "String",
    "SpanName": "LowCardinality(String)",
    "Duration": "UInt64",
    "SpanAttributes": "Map(LowCardinality(String), String)",
    "Events.Timestamp": "Array(DateTime64(9))",
    "Links.SpanId": "Array(String)",
}


def test_log_edges_cover_the_range_with_at_most_40_rows():
    edges = log_edges(1_755_337, 3_790_655_827)
    assert edges[0] <= 1_755_337 < edges[1] and edges[-2] < 3_790_655_827 <= edges[-1]
    assert len(edges) - 1 <= 40
    ratios = {round(b / a, 6) for a, b in zip(edges, edges[1:])}
    assert len(ratios) == 1
    # A range too wide for 10 per decade falls back to coarser buckets.
    wide = log_edges(1, 1e12)
    assert len(wide) - 1 <= 40 and wide[0] == 1 and wide[-1] >= 1e12


def test_log_edges_without_positive_values_and_for_one_value():
    assert log_edges(None, None) == [1.0, 10.0]
    one = log_edges(1000, 1000)
    assert len(one) == 2 and one[0] <= 1000 <= one[1]


def test_bucket_sql_clamps_the_ends():
    sql = bucket_sql("`Duration`", [1.0, 10.0, 100.0, 1000.0])
    assert "[10.0, 100.0]" in sql and ", 2, __i - 1)" in sql
    assert "CAST([], 'Array(Float64)')" in bucket_sql("`v`", [1.0, 10.0])


def test_flatten_maps_arrays_and_empties():
    row = {
        "SpanName": "GET /",
        "SpanAttributes": {"http.route": "/", "x": {}},
        "Events.Name": ["a", "b"],
        "Links.SpanId": [],
    }
    assert flatten(row) == {
        "SpanName": "GET /",
        "SpanAttributes.http.route": "/",
        "SpanAttributes.x": {},
        "Events.Name[0]": "a",
        "Events.Name[1]": "b",
        "Links.SpanId": [],
    }


def test_shares_count_missing_keys_and_score_is_total_variation():
    assert shares({"a": 3}, 4) == {"a": 75.0, None: 25.0}
    assert shares({}, 0) == {}
    assert distribution_score({"a": 100.0}, {"a": 50.0, "b": 50.0}) == 50.0
    assert distribution_score({"a": 60.0, "b": 40.0}, {"a": 60.0, "b": 40.0}) == 0
    assert distribution_score({}, {"a": 100.0}) == 0.0


def test_denylist_and_semantic_boost():
    assert is_denylisted("TraceId", COLUMNS)
    assert is_denylisted("Links.SpanId[0]", COLUMNS)
    assert is_denylisted("Events.Timestamp[2]", COLUMNS)
    assert not is_denylisted("SpanName", COLUMNS)
    assert not is_denylisted("SpanAttributes.TraceId", COLUMNS)
    assert semantic_boost("ResourceAttributes.service.name") == 1
    assert semantic_boost("SpanAttributes.http.request.method") == 1
    assert semantic_boost("SpanName") == 0


def test_high_cardinality_needs_more_than_20_rows():
    present, values = property_statistics([{"id": str(i)} for i in range(15)])
    assert not is_high_cardinality("id", present, {}, values, {})
    present, values = property_statistics([{"id": str(i)} for i in range(30)])
    assert is_high_cardinality("id", present, {}, values, {})


def test_rank_properties_puts_the_differing_column_first():
    slow = [
        {
            "SpanName": "POST /api/checkout",
            "Duration": 2000 + i,
            "TraceId": f"t{i}",
            "SpanAttributes": {"http.route": "/x"} if i % 2 else {},
        }
        for i in range(30)
    ]
    rest = [
        {
            "SpanName": ["GET /cart", "GET /ads", "POST /api/checkout"][i % 3],
            "Duration": i,
            "TraceId": f"u{i}",
            "SpanAttributes": {"http.route": "/x"},
        }
        for i in range(60)
    ]
    ranked = rank_properties(slow, rest, COLUMNS)
    assert [p["key"] for p in ranked if not p["hidden"]][0] == "SpanName"
    top = ranked[0]
    assert top["values"][0] == {
        "value": "POST /api/checkout",
        "outlier": 100.0,
        "inlier": pytest.approx(100 / 3),
    }
    assert top["score"] == pytest.approx(100 - 100 / 3)
    hidden = {p["key"]: p["hidden_reason"] for p in ranked if p["hidden"]}
    assert hidden == {"TraceId": "denylist", "Duration": "high_cardinality"}
    route = next(p for p in ranked if p["key"] == "SpanAttributes.http.route")
    assert {v["value"]: v["outlier"] for v in route["values"]} == {
        None: 50.0,
        "/x": 50.0,
    }
    assert route["score"] == 50.0
    assert ranked[-2:] == sorted(ranked[-2:], key=lambda p: -p["score"])


def test_rank_properties_skips_rare_keys_and_stringifies_values():
    rows = [{"a": 1, "t": datetime(2026, 1, 1)} for _ in range(5)] + [{"rare": 1}]
    ranked = rank_properties(rows, [], {})
    assert {p["key"] for p in ranked} == {"a", "t"}
    t = next(p for p in ranked if p["key"] == "t")
    assert t["values"][0]["value"] == "2026-01-01T00:00:00"


def heatmap(**changes):
    chart = {
        "source": "s",
        "display": "heatmap",
        "series": [{"agg": "heatmap", "column": "Duration"}],
    }
    chart.update(changes)
    return chart


def test_heatmap_tile_shape():
    assert QueryChartSerializer(data=heatmap()).is_valid()
    for changes, field in [
        ({"series": [{"agg": "count"}]}, "series"),
        (
            {"series": [{"agg": "heatmap", "column": "Duration"}, {"agg": "count"}]},
            "series",
        ),
        ({"group_by": "SpanName"}, "group_by"),
        ({"compare": True}, "compare"),
    ]:
        serializer = QueryChartSerializer(data=heatmap(**changes))
        assert not serializer.is_valid()
        assert field in serializer.errors
    line = heatmap(display="line")
    assert chart_shape_errors(
        {**line, "series": [{"agg": "heatmap", "column": "Duration"}]}
    ) == {"series": ["a heatmap series only draws a heatmap tile"]}


def test_heatmap_series_needs_a_column_and_is_not_an_alert_series():
    assert not TileSeriesSerializer(data={"agg": "heatmap"}).is_valid()
    assert TileSeriesSerializer(data={"agg": "heatmap", "column": "x"}).is_valid()
    assert not ChartSeriesSerializer(data={"agg": "heatmap", "column": "x"}).is_valid()
    with pytest.raises(ValueError, match="heatmap tile"):
        agg_expression({}, None, {"agg": "heatmap", "column": "x"})
