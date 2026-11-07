"""Chart engine v2: formulas, series filters, new aggs, several group-by columns, compare, sparkline."""

import re
from unittest.mock import MagicMock

import pytest

from telescope.fetchers import clickhouse, docker, starrocks
from telescope.fetchers.chart import (
    ChartPlan,
    FormulaError,
    eval_formula,
    fetch_chart,
    parse_formula,
    with_formulas,
)
from tests.fetchers.test_chart_sql import (
    HOUR,
    T0,
    ch_calls,
    ch_client,  # noqa: F401
    make_request,
    make_source,
    sr_cursor,  # noqa: F401
    sr_sqls,
)
from telescope.columns import ParsedColumn

TIME = (
    f"`ts` BETWEEN fromUnixTimestamp64Milli({T0 + 1500})"
    f" and fromUnixTimestamp64Milli({T0 + HOUR})"
)


def parsed(source, name):
    root = name.split(".")[0]
    return ParsedColumn(name, root, source._columns[root].type, False, "")


@pytest.mark.parametrize(
    "text, env, expected",
    [
        ("errors/total*100", {"errors": 1, "total": 4}, 25.0),
        ("errors / total * 100", {"errors": 1, "total": 0}, None),
        ("errors/total", {"errors": None, "total": None}, None),
        ("errors + total", {"errors": None, "total": 2}, 2.0),
        ("-(errors - 1.5) * 2", {"errors": 1}, 1.0),
        ("errors - total - 1", {"errors": 5, "total": 1}, 3.0),
        ("errors / total / 2", {"errors": 8, "total": 2}, 2.0),
        (".5 * errors", {"errors": 3}, 1.5),
    ],
)
def test_formula_semantics(text, env, expected):
    assert eval_formula(parse_formula(text, {"errors", "total"}), env) == expected


@pytest.mark.parametrize(
    "text, message",
    [
        ("", "empty"),
        ("errors +", "unexpected end"),
        ("nope / 2", "unknown series nope"),
        ("1 + 2", "at least one series"),
        ("errors errors", "unexpected errors"),
        ("errors % 2", "unexpected character '%'"),
        ("abs(errors)", "unknown series abs"),
        ("(errors", "missing )"),
        ("(" * 70 + "errors" + ")" * 70, "nested too deeply"),
        ("errors" + "+1" * 600, "longer than 1024"),
        ("__import__", "unknown series"),
    ],
)
def test_formula_errors(text, message):
    with pytest.raises(FormulaError, match=re.escape(message)):
        parse_formula(text, {"errors"})


def test_clickhouse_series_where_and_new_aggs(ch_client):
    ch_client.query.return_value.result_rows = [(1, 2, 3, 4)]
    source = make_source("clickhouse", "DateTime64(3)")
    series = [
        {"agg": "count", "where": "service = 'a'"},
        {"agg": "last_value", "column": "duration"},
        {"agg": "any", "column": "duration", "where": "service = 'a'"},
        {
            "agg": "quantile",
            "column": "duration",
            "level": 0.5,
            "where": "duration > 1",
        },
    ]
    clickhouse.Fetcher.fetch_chart_data(
        make_request(source, display="table", series=series)
    )
    [(sql, _, _)] = ch_calls(ch_client)
    assert sql == (
        "SELECT countIf((service = 'a')) AS `__telescope_v0`,"
        " argMaxOrNull(`duration`, `ts`) AS `__telescope_v1`,"
        " anyOrNullIf(`duration`, (service = 'a')) AS `__telescope_v2`,"
        " quantileOrNullIf(0.5)(`duration`, (duration > 1)) AS `__telescope_v3`"
        f" FROM db.logs WHERE {TIME} AND (true) AND (true)"
    )


def test_clickhouse_three_group_by_columns(ch_client):
    ch_client.query.side_effect = [
        MagicMock(result_rows=[("a", "x", ""), ("b", "y", "1")]),
        MagicMock(result_rows=[(T0 + 60000, "a", "x", "", 5)]),
    ]
    source = make_source("clickhouse", "DateTime64(3)")
    request = make_request(source, limit=1)
    request.group_by = [parsed(source, n) for n in ["service", "attrs.k", "duration"]]
    result = clickhouse.Fetcher.fetch_chart_data(request).as_dict()
    (rank, _, _), (sql, parameters, _) = ch_calls(ch_client)
    groups = (
        "ifNull(toString(toString(service)), '') AS `__telescope_g0`,"
        " ifNull(toString(attrs['k']), '') AS `__telescope_g1`,"
        " ifNull(toString(toString(duration)), '') AS `__telescope_g2`"
    )
    aliases = "`__telescope_g0`, `__telescope_g1`, `__telescope_g2`"
    assert rank == (
        f"SELECT {groups} FROM db.logs WHERE {TIME.replace(str(T0 + 1500), str(T0)).replace(str(T0 + HOUR), str(T0 + HOUR - 1))}"
        f" AND (true) AND (true) GROUP BY {aliases} ORDER BY count() DESC, {aliases} LIMIT 2"
    )
    assert (
        "AND tuple(ifNull(toString(toString(service)), ''), ifNull(toString(attrs['k']), ''),"
        " ifNull(toString(toString(duration)), '')) IN {groups:Array(Tuple(String, String, String))}"
    ) in sql
    assert parameters == {"groups": [("a", "x", "")]}
    assert result["truncated"] is True
    [series] = result["series"]
    assert series["name"] == series["group"] == "a · x · __none__"
    assert series["groups"] == ["a", "x", "__none__"]
    assert series["values"][1] == 5


def test_clickhouse_multi_group_table(ch_client):
    ch_client.query.return_value.result_rows = [("a", "x", 3), ("b", "", 1)]
    source = make_source("clickhouse", "DateTime64(3)")
    request = make_request(source, display="pie")
    request.group_by = [parsed(source, n) for n in ["service", "attrs.k"]]
    result = clickhouse.Fetcher.fetch_chart_data(request).as_dict()
    assert result["columns"][0] == {
        "name": "service · attrs.k",
        "kind": "group",
        "names": ["service", "attrs.k"],
    }
    assert result["rows"] == [
        {"group": "a · x", "groups": ["a", "x"], "values": [3]},
        {"group": "b · __none__", "groups": ["b", "__none__"], "values": [1]},
    ]


def test_starrocks_series_where_new_aggs_and_groups(sr_cursor):
    source = make_source("starrocks", "datetime")
    sr_cursor.fetchall.return_value = [(1, 2, 3, 4)]
    series = [
        {"agg": "count", "where": "service = 'a'"},
        {"agg": "last_value", "column": "duration"},
        {"agg": "any", "column": "duration"},
        {"agg": "avg", "column": "duration", "where": "service = 'a'"},
        {"agg": "last_value", "column": "duration", "where": "service = 'a'"},
    ]
    starrocks.Fetcher.fetch_chart_data(
        make_request(source, display="table", series=series)
    )
    sr_cursor.fetchall.side_effect = [
        [("a", "x"), ("it's", "y")],
        [(T0, "a", "x", 1)],
    ]
    request = make_request(source)
    request.group_by = [parsed(source, n) for n in ["service", "attrs.k"]]
    result = starrocks.Fetcher.fetch_chart_data(request).as_dict()
    table, rank, sql = sr_sqls(sr_cursor)
    cond = "(`service` = 'a')"
    for part in [
        f"count(CASE WHEN {cond} THEN 1 END) AS `__telescope_v0`",
        "max_by(`duration`, `ts`) AS `__telescope_v1`",
        "any_value(`duration`) AS `__telescope_v2`",
        f"avg(CASE WHEN {cond} THEN `duration` END) AS `__telescope_v3`",
        f"max_by(`duration`, CASE WHEN {cond} THEN `ts` END) AS `__telescope_v4`",
    ]:
        assert part in table
    g0, g1 = (
        "ifnull(cast(`service` as string), '')",
        "ifnull(cast(attrs['k'] as string), '')",
    )
    assert f"{g0} AS `__telescope_g0`, {g1} AS `__telescope_g1` FROM" in rank
    assert (
        f"AND (({g0} = 'a' AND {g1} = 'x') OR ({g0} = 'it\\'s' AND {g1} = 'y')) GROUP BY"
        in sql
    )
    assert [s["group"] for s in result["series"]] == ["a · x", "it's · y"]


def plan_run(rows_by_display):
    """A fetcher stand-in: ChartPlan shaping over canned rows per display kind."""

    def run(request):
        plan = ChartPlan(request)
        rows = rows_by_display[plan.kind](request)
        if plan.kind == "number":
            return plan.number(rows)
        if plan.kind == "table":
            return plan.table(rows)
        return plan.timeseries(rows)

    return run


RATIO = [
    {"agg": "count", "alias": "errors", "where": "status = 'Error'", "hidden": True},
    {"agg": "count", "alias": "total", "hidden": True},
    {"agg": "formula", "formula": "errors/total*100", "alias": "ratio"},
]


def test_formula_over_number_table_and_timeseries():
    source = make_source("clickhouse", "DateTime64(3)")
    seen = []

    def rows(kind):
        def make(request):
            seen.append([s["agg"] for s in request.series])
            if kind == "timeseries":
                return [(T0, 1, 4), (T0 + 60000, 0, 0)]
            return [(1, 4)]

        return make

    run = plan_run({k: rows(k) for k in ["number", "table", "timeseries"]})
    number = with_formulas(make_request(source, "number", series=RATIO), run)
    assert number.as_dict()["value"] == 25.0
    assert number.as_dict()["values"] == [1, 4, 25.0]
    table = with_formulas(make_request(source, "table", series=RATIO), run).as_dict()
    assert table["rows"] == [{"group": "", "values": [1, 4, 25.0]}]
    assert [c["name"] for c in table["columns"]] == ["", "errors", "total", "ratio"]
    line = with_formulas(make_request(source, "line", series=RATIO), run).as_dict()
    assert [s["series_index"] for s in line["series"]] == [0, 1, 2]
    assert line["series"][2]["name"] == "ratio"
    assert line["series"][2]["values"][:3] == [25.0, None, None]
    assert seen == [["count", "count"]] * 3


def test_formula_per_group():
    source = make_source("clickhouse", "DateTime64(3)")
    request = make_request(source, "line", series=RATIO, group_by="service")
    plan = ChartPlan(request)

    def run(sub):
        plan = ChartPlan(sub)
        return plan.timeseries(
            [(T0, "a", 1, 2), (T0, "b", 3, 3)], groups=["a", "b"], truncated=False
        )

    result = with_formulas(request, run).as_dict()
    assert [(s["name"], s["values"][0]) for s in result["series"]] == [
        ("errors · a", 1),
        ("total · a", 2),
        ("ratio · a", 50.0),
        ("errors · b", 3),
        ("total · b", 3),
        ("ratio · b", 100.0),
    ]
    assert plan.kind == "timeseries"


def test_number_shows_the_visible_series():
    source = make_source("clickhouse", "DateTime64(3)")
    series = [{"agg": "count", "hidden": True}, {"agg": "sum", "column": "duration"}]
    plan = ChartPlan(make_request(source, "number", series=series))
    assert plan.number([(3, 7)]).as_dict() == {
        "kind": "number",
        "from": T0 + 1500,
        "to": T0 + HOUR,
        "value": 7,
        "values": [3, 7],
    }


class FakeFetcher:
    def __init__(self, source):
        self.requests = []
        self.run = plan_run(
            {
                "number": lambda r: [(r.time_from // 1000,)],
                "timeseries": lambda r: (
                    [(r.time_from, "a", 1), (r.time_from, "b", 2)]
                    if r.group_by
                    else [(r.time_from, r.time_from // 1000)]
                ),
            }
        )

    def fetch_chart_data(self, request):
        self.requests.append(request)
        if request.group_by:
            plan = ChartPlan(request)
            groups = ["a"] if request.time_from < T0 else ["a", "b"]
            rows = [(plan.time_from, g, 1 if g == "a" else 2) for g in groups]
            return plan.timeseries(rows, groups, False)
        return self.run(request)


def test_compare_previous_period_timeseries():
    source = make_source("clickhouse", "DateTime64(3)")
    fetcher = FakeFetcher(source)
    request = make_request(source, "line", granularity="auto", group_by="service")
    result = fetch_chart(fetcher, request, compare=True).as_dict()
    current, previous = fetcher.requests
    span = result["to"] - result["from"]
    assert (previous.time_from, previous.time_to) == (
        request.time_from - span,
        request.time_to - span,
    )
    assert previous.granularity == result["granularity"]
    assert [(s["name"], s.get("previous", False)) for s in result["series"]] == [
        ("a", False),
        ("b", False),
        ("a (previous)", True),
        ("b (previous)", True),
    ]
    assert result["series"][2]["values"][0] == 1
    assert set(result["series"][3]["values"]) == {None}
    assert result["previous_offset_ms"] == span


def test_compare_and_sparkline_for_number():
    source = make_source("clickhouse", "DateTime64(3)")
    fetcher = FakeFetcher(source)
    request = make_request(source, "number")
    result = fetch_chart(fetcher, request, compare=True, sparkline=True).as_dict()
    span = HOUR - 1500
    assert result["value"] == (T0 + 1500) // 1000
    assert result["previous_value"] == (T0 + 1500 - span) // 1000
    assert result["previous_offset_ms"] == span
    line = fetcher.requests[2]
    assert (line.display, line.granularity, line.group_by) == ("line", "auto", [])
    assert len(result["sparkline"]["timestamps"]) == len(result["sparkline"]["values"])
    assert result["sparkline"]["values"][0] == (T0 + 1500) // 1000


def test_plain_request_is_one_query():
    source = make_source("clickhouse", "DateTime64(3)")
    fetcher = FakeFetcher(source)
    result = fetch_chart(fetcher, make_request(source, "number")).as_dict()
    assert len(fetcher.requests) == 1
    assert set(result) == {"kind", "from", "to", "value"}


def test_docker_counts_several_series_and_formulas():
    source = make_source("docker", "DateTime64(3)")
    series = [
        {"agg": "count", "alias": "a"},
        {"agg": "formula", "formula": "a * 2"},
    ]
    request = make_request(source, "number", series=[{"agg": "count"}] * 2)
    plan = ChartPlan(request)
    assert plan.count_rows([object()] * 3, None).as_dict()["values"] == [3, 3]
    request = make_request(source, "number", series=series)
    result = with_formulas(
        request, lambda sub: ChartPlan(sub).count_rows([object()] * 3, None)
    ).as_dict()
    assert result["values"] == [3, 6.0]
    assert docker.Fetcher is not None
