"""Metric series: quantile maths and validation, without ClickHouse."""

from types import SimpleNamespace

import pytest

from telescope.fetchers.chart import series_label
from telescope.serializers.dashboard import ChartSeriesSerializer, chart_series_errors
from telescope_otel.metrics_sql import exponential_quantile, histogram_quantile

BOUNDS = [0.1, 0.5, 1, 2.5]


def test_histogram_quantile_interpolates_inside_the_bucket():
    # 10 in (0,0.1], 10 in (0.1,0.5], 0 in (0.5,1], 20 in (1,2.5], 0 in (2.5,+Inf).
    counts = [10, 10, 0, 20, 0]
    assert histogram_quantile(0.25, BOUNDS, counts) == pytest.approx(0.1)
    assert histogram_quantile(0.5, BOUNDS, counts) == pytest.approx(0.5)
    assert histogram_quantile(0.75, BOUNDS, counts) == pytest.approx(1.75)
    assert histogram_quantile(0.1, BOUNDS, counts) == pytest.approx(0.04)


def test_histogram_quantile_edges():
    assert histogram_quantile(0.5, BOUNDS, [0] * 5) is None
    assert histogram_quantile(0.5, BOUNDS, [1, 2]) is None
    # Everything above the last bound reports that bound.
    assert histogram_quantile(0.99, BOUNDS, [0, 0, 0, 0, 7]) == 2.5


def test_exponential_quantile():
    # Scale 0: bucket i is (2^i, 2^(i+1)].
    assert exponential_quantile(0.5, 0, {0: 10, 2: 10}, 0) == pytest.approx(2.0)
    assert exponential_quantile(0.25, 0, {1: 4}, 4) == 0.0
    assert exponential_quantile(0.75, 1, {2: 2}, 0) == pytest.approx(
        2 + (2**1.5 - 2) * 0.75
    )
    assert exponential_quantile(0.5, 0, {}, 0) is None


def metrics_source(tables=None):
    otel = {"signal": "metrics", "metric_tables": tables or {"gauge": "g", "sum": "s"}}
    return SimpleNamespace(kind="clickhouse", _columns={}, data={"otel": otel})


def series(**metric):
    return {
        "agg": "metric",
        "metric": {"name": "m", "type": "sum", "agg": "rate", **metric},
    }


def validate(item):
    serializer = ChartSeriesSerializer(data=item)
    return serializer.is_valid(), serializer.errors


def test_series_serializer_checks_the_metric():
    assert validate(series())[0]
    ok, errors = validate(series(type="gauge"))
    assert not ok and errors["metric"]["agg"] == [
        "a gauge metric takes avg, min, max, last"
    ]
    ok, errors = validate({"agg": "metric"})
    assert errors["metric"] == ["This field is required."]
    ok, errors = validate({**series(), "where": "a = 1"})
    assert errors["where"] == ["filter a metric series with metric.attrs_filter"]
    ok, errors = validate({"agg": "count", "metric": series()["metric"]})
    assert errors["metric"] == ["metric is only allowed for agg metric"]
    ok, errors = validate({**series(), "column": "Value"})
    assert errors["column"] == ["metric does not take a column"]


def test_metric_series_need_a_metrics_source_and_a_table():
    plain = SimpleNamespace(kind="clickhouse", _columns={}, data={})
    assert chart_series_errors(plain, [series()]) == {
        0: {"metric": ["source is not an OTel metrics source"]}
    }
    errors = chart_series_errors(
        metrics_source(), [series(type="histogram", agg="p95")]
    )
    assert errors == {0: {"metric": {"type": ["source has no histogram metric table"]}}}
    mixed = [series(), {"agg": "count"}, {"agg": "formula", "formula": "a"}]
    errors = chart_series_errors(metrics_source(), mixed)
    assert errors[1] == {
        "agg": ["a metric chart takes only metric series and formulas"]
    }
    assert (
        chart_series_errors(metrics_source(), [series(), series(agg="increase")]) == {}
    )


def test_series_label():
    assert series_label(series()) == "rate(m)"
    assert series_label({**series(), "alias": "rps"}) == "rps"
