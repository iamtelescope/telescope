from decimal import Decimal
from types import SimpleNamespace

import pytest

from telescope.fetchers.chart import (
    ChartPlan,
    align_range,
    pick_granularity,
    series_label,
)

HOUR = 3600 * 1000
DAY = 24 * HOUR
T0 = 1762423200000  # 2025-11-06 10:00:00 UTC, a whole day boundary is T0 - 10h


def make_request(display="line", series=None, group_by=None, **kwargs):
    values = dict(
        source=SimpleNamespace(kind="clickhouse"),
        display=display,
        series=series or [{"agg": "count"}],
        group_by=[SimpleNamespace(name=group_by)] if group_by else [],
        granularity="1m",
        limit=10,
        time_from=T0,
        time_to=T0 + HOUR,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "range_ms, expected",
    [
        (15 * 60 * 1000, "15s"),
        (HOUR, "1m"),
        (6 * HOUR, "5m"),
        (DAY, "30m"),
        (7 * DAY, "6h"),
        (30 * DAY, "12h"),
        (90 * DAY, "1d"),
        (1000, "15s"),
    ],
)
def test_auto_granularity(range_ms, expected):
    assert pick_granularity(T0, T0 + range_ms)[0] == expected


def test_explicit_granularity_kept():
    assert pick_granularity(T0, T0 + HOUR, "1m") == ("1m", 60000)
    assert pick_granularity(T0, T0 + HOUR, "10m") == ("10m", 600000)


@pytest.mark.parametrize(
    "granularity, range_ms, expected",
    [
        ("15s", DAY, "5m"),
        ("1m", 3 * DAY, "15m"),
        ("10m", 3 * DAY, "15m"),
        ("1h", 30 * DAY, "6h"),
        ("1d", 400 * DAY, "1d"),
    ],
)
def test_explicit_granularity_coarsened(granularity, range_ms, expected):
    name, step_ms = pick_granularity(T0, T0 + range_ms, granularity)
    assert name == expected
    if name != "1d":
        aligned_from, aligned_to = align_range(T0, T0 + range_ms, step_ms)
        assert (aligned_to - aligned_from) // step_ms <= 300


def test_align_range():
    assert align_range(1000, 61000, 60000) == (0, 120000)
    assert align_range(60000, 120000, 60000) == (60000, 120000)
    day_from, day_to = align_range(T0, T0 + HOUR, DAY)
    assert day_from % DAY == 0 and day_to == day_from + DAY


@pytest.mark.parametrize(
    "series, label",
    [
        ({"agg": "count"}, "count()"),
        ({"agg": "sum", "column": "bytes"}, "sum(bytes)"),
        ({"agg": "avg", "column": "d"}, "avg(d)"),
        ({"agg": "quantile", "column": "d", "level": 0.95}, "p95(d)"),
        ({"agg": "quantile", "column": "d", "level": 0.5}, "p50(d)"),
        ({"agg": "uniq", "column": "u"}, "uniq(u)"),
        ({"agg": "count", "alias": "Rows"}, "Rows"),
    ],
)
def test_series_label(series, label):
    assert series_label(series) == label


def test_timeseries_plan_is_aligned():
    plan = ChartPlan(make_request(time_from=T0 + 1500, time_to=T0 + HOUR - 1500))
    assert (plan.granularity, plan.step_ms) == ("1m", 60000)
    assert (plan.time_from, plan.time_to, plan.query_to) == (
        T0,
        T0 + HOUR,
        T0 + HOUR - 1,
    )


def test_number_and_table_plans_use_raw_range():
    for display in ["number", "table", "bar"]:
        plan = ChartPlan(make_request(display, time_from=T0 + 1, time_to=T0 + 2))
        assert (plan.time_from, plan.time_to, plan.query_to) == (T0 + 1, T0 + 2, T0 + 2)
        assert plan.granularity is None


def test_timeseries_zero_vs_null_fill():
    series = [{"agg": "count"}, {"agg": "avg", "column": "d"}]
    plan = ChartPlan(make_request(series=series, time_to=T0 + 3 * 60000))
    result = plan.timeseries([(T0 + 60000 + 5000, 4, Decimal("2.5"))]).as_dict()
    assert result["kind"] == "timeseries"
    assert result["timestamps"] == [T0, T0 + 60000, T0 + 120000]
    assert result["step_ms"] == 60000
    assert result["series"] == [
        {"name": "count()", "group": None, "series_index": 0, "values": [0, 4, 0]},
        {
            "name": "avg(d)",
            "group": None,
            "series_index": 1,
            "values": [None, 2.5, None],
        },
    ]
    assert result["truncated"] is False


def test_timeseries_nan_and_null_values():
    series = [{"agg": "max", "column": "d"}, {"agg": "sum", "column": "d"}]
    plan = ChartPlan(make_request(series=series, time_to=T0 + 2 * 60000))
    result = plan.timeseries(
        [(T0, float("nan"), None), (T0 + 60000, float("inf"), 3)]
    ).as_dict()
    assert [s["values"] for s in result["series"]] == [[None, None], [0, 3]]


def test_timeseries_empty_without_group_by():
    plan = ChartPlan(make_request(time_to=T0 + 2 * 60000))
    result = plan.timeseries([]).as_dict()
    assert result["series"] == [
        {"name": "count()", "group": None, "series_index": 0, "values": [0, 0]}
    ]


def test_timeseries_drops_rows_outside_grid():
    plan = ChartPlan(make_request(time_to=T0 + 60000))
    result = plan.timeseries([(T0 - 60000, 9), (T0 + 60000, 9), (T0, 1)]).as_dict()
    assert result["series"][0]["values"] == [1]


def test_timeseries_groups_single_series():
    plan = ChartPlan(make_request(group_by="service", time_to=T0 + 2 * 60000))
    rows = [(T0, "web", 1), (T0 + 60000, "api", 5), (T0, "", 2)]
    result = plan.timeseries(rows, ["api", "web", ""], True).as_dict()
    assert [(s["name"], s["group"], s["values"]) for s in result["series"]] == [
        ("api", "api", [0, 5]),
        ("web", "web", [1, 0]),
        ("__none__", "__none__", [2, 0]),
    ]
    assert result["truncated"] is True


def test_timeseries_groups_several_series():
    series = [{"agg": "count"}, {"agg": "quantile", "column": "d", "level": 0.95}]
    plan = ChartPlan(
        make_request(series=series, group_by="service", time_to=T0 + 60000)
    )
    result = plan.timeseries(
        [(T0, "web", 1, 10.0), (T0, "api", 2, 130.5)], ["api", "web"]
    ).as_dict()
    assert [(s["name"], s["series_index"], s["values"]) for s in result["series"]] == [
        ("count() · api", 0, [2]),
        ("p95(d) · api", 1, [130.5]),
        ("count() · web", 0, [1]),
        ("p95(d) · web", 1, [10.0]),
    ]


def test_number():
    plan = ChartPlan(make_request("number"))
    assert plan.number([(Decimal("1234.5"),)]).as_dict() == {
        "kind": "number",
        "from": T0,
        "to": T0 + HOUR,
        "value": 1234.5,
    }
    assert plan.number([]).as_dict()["value"] == 0
    avg = ChartPlan(make_request("number", series=[{"agg": "avg", "column": "d"}]))
    assert avg.number([(None,)]).as_dict()["value"] is None
    assert avg.number([(float("nan"),)]).as_dict()["value"] is None


def test_table_truncated():
    plan = ChartPlan(make_request("table", group_by="service", limit=2))
    result = plan.table([("api", 3), ("web", 2), ("", 1)]).as_dict()
    assert result == {
        "kind": "table",
        "from": T0,
        "to": T0 + HOUR,
        "columns": [
            {"name": "service", "kind": "group"},
            {"name": "count()", "kind": "value"},
        ],
        "rows": [{"group": "api", "values": [3]}, {"group": "web", "values": [2]}],
        "truncated": True,
    }
    assert plan.table([("api", 3), ("web", 2)]).as_dict()["truncated"] is False


def test_table_without_group_by():
    series = [{"agg": "count"}, {"agg": "min", "column": "d"}]
    plan = ChartPlan(make_request("table", series=series))
    result = plan.table([(0, None)]).as_dict()
    assert result["rows"] == [{"group": "", "values": [0, None]}]
    assert result["columns"][0] == {"name": "", "kind": "group"}


def fake_row(ts, **data):
    return SimpleNamespace(time={"unixtime": ts}, data=data)


ROWS = [
    fake_row(T0 + 1000, stream="stdout"),
    fake_row(T0 + 2000, stream="stdout"),
    fake_row(T0 + 61000, stream="stderr"),
    fake_row(T0 + 62000, stream="stdout"),
    fake_row(T0 + 63000, stream=""),
]


def stream_of(row):
    return row.data["stream"]


def test_count_rows_number():
    plan = ChartPlan(make_request("number"))
    assert plan.count_rows(ROWS, stream_of).as_dict()["value"] == 5


def test_count_rows_timeseries():
    plan = ChartPlan(make_request(time_to=T0 + 2 * 60000))
    result = plan.count_rows(ROWS, stream_of).as_dict()
    assert result["series"][0]["values"] == [2, 3]

    plan = ChartPlan(make_request(group_by="stream", limit=2, time_to=T0 + 2 * 60000))
    result = plan.count_rows(ROWS, stream_of).as_dict()
    assert [(s["group"], s["values"]) for s in result["series"]] == [
        ("stdout", [2, 1]),
        ("__none__", [0, 1]),
    ]
    assert result["truncated"] is True


def test_count_rows_table_and_bar():
    for display in ["table", "bar"]:
        plan = ChartPlan(make_request(display, group_by="stream"))
        result = plan.count_rows(ROWS, stream_of).as_dict()
        assert result["rows"] == [
            {"group": "stdout", "values": [3]},
            {"group": "__none__", "values": [1]},
            {"group": "stderr", "values": [1]},
        ]
        assert result["truncated"] is False
    plan = ChartPlan(make_request("table"))
    assert plan.count_rows(ROWS, stream_of).as_dict()["rows"] == [
        {"group": "", "values": [5]}
    ]


def test_count_rows_rejects_other_aggs():
    plan = ChartPlan(
        make_request(
            source=SimpleNamespace(kind="docker"),
            series=[{"agg": "sum", "column": "x"}],
        )
    )
    with pytest.raises(ValueError, match="aggregation sum is not supported for docker"):
        plan.count_rows(ROWS, stream_of)
