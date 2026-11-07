from unittest.mock import MagicMock, Mock, patch

import pytest

from telescope.columns import ParsedColumn
from telescope.fetchers import clickhouse, starrocks
from telescope.fetchers.request import ChartDataRequest
from telescope.models import Source, SourceColumn

T0 = 1762423200000
HOUR = 3600 * 1000


def column(name, type, jsonstring=False):
    return SourceColumn(
        name=name,
        display_name="",
        type=type,
        jsonstring=jsonstring,
        autocomplete=False,
        suggest=False,
        group_by=True,
        values=[],
    )


def make_source(kind, time_type, **data):
    source = Mock(spec=Source)
    source.kind = kind
    source.slug = "logs"
    source.data = {"catalog": "default_catalog", "database": "db", "table": "logs"}
    source.data.update(data)
    source.time_column = "ts"
    source.date_column = ""
    source._columns = {
        "ts": column("ts", time_type),
        "service": column("service", "String"),
        "duration": column("duration", "Float64"),
        "we`ird": column("we`ird", "UInt64"),
        "attrs": column("attrs", "Map(String, String)"),
    }
    source.conn = Mock(data={})
    return source


def make_request(source, display="line", series=None, group_by=None, **kwargs):
    values = dict(
        source=source,
        query="",
        raw_query="",
        time_from=T0 + 1500,
        time_to=T0 + HOUR,
        context_columns={},
        display=display,
        series=series or [{"agg": "count"}],
        group_by=[],
        granularity="1m",
        limit=10,
    )
    if group_by:
        values["group_by"] = [
            ParsedColumn(
                name=group_by,
                root_name=group_by.split(".")[0],
                type=source._columns[group_by.split(".")[0]].type,
                jsonstring=False,
                display_name="",
            )
        ]
    values.update(kwargs)
    return ChartDataRequest(**values)


@pytest.fixture
def ch_client():
    with patch("telescope.fetchers.clickhouse.ClickhouseConnect") as connect:
        client = MagicMock()
        connect.return_value.__enter__.return_value.client = client
        yield client


def ch_calls(client):
    return [
        (c.args[0], c.kwargs.get("parameters"), c.kwargs.get("settings"))
        for c in client.query.call_args_list
    ]


ALL_SERIES = [
    {"agg": "count"},
    {"agg": "sum", "column": "duration"},
    {"agg": "avg", "column": "duration"},
    {"agg": "min", "column": "duration"},
    {"agg": "max", "column": "duration"},
    {"agg": "quantile", "column": "duration", "level": 0.95},
    {"agg": "uniq", "column": "we`ird"},
]


def test_clickhouse_aggs_and_quoting(ch_client):
    ch_client.query.return_value.result_rows = [(1, 2, 3, 4, 5, 6, 7)]
    source = make_source("clickhouse", "DateTime64(3)", settings="max_threads = 1")
    request = make_request(source, display="table", series=ALL_SERIES)
    result = clickhouse.Fetcher.fetch_chart_data(request).as_dict()
    [(sql, parameters, settings)] = ch_calls(ch_client)
    assert sql == (
        "SELECT count() AS `__telescope_v0`, sum(`duration`) AS `__telescope_v1`,"
        " avgOrNull(`duration`) AS `__telescope_v2`, minOrNull(`duration`) AS `__telescope_v3`,"
        " maxOrNull(`duration`) AS `__telescope_v4`,"
        " quantileOrNull(0.95)(`duration`) AS `__telescope_v5`,"
        " uniq(`we``ird`) AS `__telescope_v6` FROM db.logs WHERE"
        f" `ts` BETWEEN fromUnixTimestamp64Milli({T0 + 1500}) and fromUnixTimestamp64Milli({T0 + HOUR})"
        " AND (true) AND (true) SETTINGS max_threads = 1"
    )
    assert parameters is None
    assert settings == {"max_execution_time": 30}
    assert result["rows"] == [{"group": "", "values": [1, 2, 3, 4, 5, 6, 7]}]


def test_clickhouse_number_with_filter_and_raw_query(ch_client):
    ch_client.query.return_value.result_rows = [(42,)]
    source = make_source("clickhouse", "DateTime")
    request = make_request(
        source,
        display="number",
        query="service = 'api'",
        raw_query="duration > 1 OR duration < 0",
    )
    assert clickhouse.Fetcher.fetch_chart_data(request).as_dict()["value"] == 42
    [(sql, _, _)] = ch_calls(ch_client)
    assert "AND (service = 'api') AND (duration > 1 OR duration < 0)" in sql


def test_clickhouse_timeseries_top_n(ch_client):
    first = MagicMock(result_rows=[("api",), ("web",), ("db",)])
    second = MagicMock(result_rows=[(T0 + 60000, "api", 7), (T0, "web", 3)])
    ch_client.query.side_effect = [first, second]
    source = make_source("clickhouse", "DateTime64(3)")
    request = make_request(source, group_by="service", limit=2)
    result = clickhouse.Fetcher.fetch_chart_data(request).as_dict()

    (rank_sql, rank_params, _), (sql, params, settings) = ch_calls(ch_client)
    time_clause = (
        f"`ts` BETWEEN fromUnixTimestamp64Milli({T0})"
        f" and fromUnixTimestamp64Milli({T0 + HOUR - 1})"
    )
    group = "ifNull(toString(toString(service)), '')"
    assert rank_sql == (
        f"SELECT {group} AS `__telescope_g` FROM db.logs WHERE {time_clause}"
        " AND (true) AND (true) GROUP BY `__telescope_g`"
        " ORDER BY count() DESC, `__telescope_g` LIMIT 3"
    )
    assert rank_params is None
    assert sql == (
        "SELECT intDiv(toUnixTimestamp(`ts`), 60) * 60000 AS `__telescope_t`,"
        f" {group} AS `__telescope_g`, count() AS `__telescope_v0` FROM db.logs"
        f" WHERE {time_clause} AND (true) AND (true) AND {group} IN {{groups:Array(String)}}"
        " GROUP BY `__telescope_t`, `__telescope_g` ORDER BY `__telescope_t`"
    )
    assert params == {"groups": ["api", "web"]}
    assert settings == {"max_execution_time": 30}
    assert result["truncated"] is True
    assert [s["group"] for s in result["series"]] == ["api", "web"]
    assert result["series"][0]["values"][:2] == [0, 7]


def test_clickhouse_timeseries_no_groups_skips_second_query(ch_client):
    ch_client.query.return_value.result_rows = []
    source = make_source("clickhouse", "DateTime64(3)")
    result = clickhouse.Fetcher.fetch_chart_data(
        make_request(source, group_by="service")
    ).as_dict()
    assert ch_client.query.call_count == 1
    assert result["series"] == []


def test_clickhouse_int_time_column(ch_client):
    ch_client.query.return_value.result_rows = []
    source = make_source("clickhouse", "UInt64")
    clickhouse.Fetcher.fetch_chart_data(make_request(source))
    [(sql, _, _)] = ch_calls(ch_client)
    assert sql.startswith(
        "SELECT intDiv(toUnixTimestamp(toDateTime(`ts`)), 60) * 60000 AS `__telescope_t`"
    )


def test_clickhouse_bar_order(ch_client):
    ch_client.query.return_value.result_rows = [("a", 2)]
    source = make_source("clickhouse", "DateTime")
    request = make_request(
        source,
        display="bar",
        series=[{"agg": "sum", "column": "duration"}],
        group_by="service",
        limit=5,
    )
    clickhouse.Fetcher.fetch_chart_data(request)
    [(sql, _, _)] = ch_calls(ch_client)
    assert sql.endswith(
        "GROUP BY `__telescope_g` ORDER BY `__telescope_v0` DESC, `__telescope_g` LIMIT 6"
    )


def test_unknown_column_rejected(ch_client):
    source = make_source("clickhouse", "DateTime")
    request = make_request(
        source, display="number", series=[{"agg": "sum", "column": "x; DROP"}]
    )
    with pytest.raises(ValueError, match="unknown column"):
        clickhouse.Fetcher.fetch_chart_data(request)
    assert ch_client.query.call_count == 0


def test_clickhouse_group_by_value():
    def parsed(name, type, jsonstring=False):
        return ParsedColumn(name, name.split(".")[0], type, jsonstring, "")

    build = clickhouse.build_group_by_value
    assert build(parsed("service", "String")) == "toString(service)"
    assert build(parsed("attrs.k", "Map(String, String)")) == "attrs['k']"
    assert build(parsed("attrs.a'b", "Map(String, String)")) == "attrs['a\\'b']"
    assert build(parsed("arr.1", "Array(String)")) == "arr[1]"
    assert (
        build(parsed("body.a.b", "String", jsonstring=True))
        == "JSONExtractString(body, 'a', 'b')"
    )


@pytest.fixture
def sr_cursor():
    with patch("telescope.fetchers.starrocks.StarrocksConnect") as connect:
        cursor = MagicMock()
        connect.return_value.__enter__.return_value.client.cursor.return_value = cursor
        yield cursor


def sr_sqls(cursor):
    for c in cursor.execute.call_args_list:
        assert len(c.args) == 1
    return [c.args[0] for c in cursor.execute.call_args_list]


def test_starrocks_aggs_and_hints(sr_cursor):
    sr_cursor.fetchall.return_value = [(1, 2, 3, 4, 5, 6, 7)]
    source = make_source("starrocks", "datetime", settings="pipeline_dop=1")
    request = make_request(source, display="number", series=ALL_SERIES[:1])
    starrocks.Fetcher.fetch_chart_data(request)
    request = make_request(source, display="table", series=ALL_SERIES)
    starrocks.Fetcher.fetch_chart_data(request)
    number_sql, table_sql = sr_sqls(sr_cursor)
    assert number_sql.startswith(
        "SELECT /*+ SET_VAR(query_timeout=30, pipeline_dop=1) */ count(*) AS `__telescope_v0`"
        " FROM default_catalog.db.logs WHERE"
    )
    for part in [
        "sum(`duration`)",
        "avg(`duration`)",
        "min(`duration`)",
        "max(`duration`)",
        "percentile_approx(`duration`, 0.95)",
        "approx_count_distinct(`we``ird`)",
    ]:
        assert part in table_sql


def test_starrocks_timeseries_top_n(sr_cursor):
    sr_cursor.fetchall.side_effect = [
        [("it's",), ("web",)],
        [(T0, "it's", 1)],
    ]
    source = make_source("starrocks", "datetime")
    request = make_request(source, group_by="service", limit=5)
    result = starrocks.Fetcher.fetch_chart_data(request).as_dict()
    rank_sql, sql = sr_sqls(sr_cursor)
    group = "ifnull(cast(`service` as string), '')"
    assert rank_sql.startswith(
        f"SELECT /*+ SET_VAR(query_timeout=30) */ {group} AS `__telescope_g`"
    )
    assert rank_sql.endswith("ORDER BY count(*) DESC, `__telescope_g` LIMIT 6")
    assert sql.startswith(
        "SELECT /*+ SET_VAR(query_timeout=30) */"
        " floor(seconds_diff(`ts`, '1970-01-01 00:00:00') / 60) * 60000 AS `__telescope_t`"
    )
    assert f"AND {group} IN ('it\\'s', 'web') GROUP BY" in sql
    assert result["truncated"] is False
    assert result["series"][0]["name"] == "it's"


def test_starrocks_group_by_value():
    def parsed(name, type):
        return ParsedColumn(name, name.split(".")[0], type, False, "")

    build = starrocks.build_group_by_value
    assert build(parsed("service", "varchar")) == "`service`"
    assert build(parsed("attrs.a.b", "map<varchar,varchar>")) == "attrs['a']['b']"
    assert build(parsed("doc.a", "json")) == "cast(`doc`->'\"a\"' as string)"
