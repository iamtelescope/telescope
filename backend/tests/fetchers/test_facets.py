from unittest.mock import MagicMock, Mock, patch

import pytest

from telescope.fetchers import facets
from telescope.fetchers.facets import FacetRequest
from telescope.models import Source, SourceColumn

T0 = 1762423200000
HOUR = 3600 * 1000


def column(name, type):
    return SourceColumn(
        name=name,
        display_name="",
        type=type,
        jsonstring=False,
        autocomplete=True,
        suggest=True,
        group_by=True,
        values=[],
    )


def make_source(kind="clickhouse", **data):
    source = Mock(spec=Source)
    source.kind = kind
    source.data = {"catalog": "cat", "database": "db", "table": "logs", "settings": ""}
    source.data.update(data)
    source.time_column = "ts"
    source.date_column = ""
    source._columns = {
        "ts": column("ts", "DateTime64(3)"),
        "service": column("service", "LowCardinality(String)"),
        "code": column("code", "UInt16"),
        "Body": column("Body", "String"),
        "attrs": column("attrs", "Map(LowCardinality(String), String)"),
    }
    source.conn = Mock(data={})
    return source


def make_request(source, **kwargs):
    values = dict(
        source=source,
        time_from=T0,
        time_to=T0 + HOUR,
        columns=["service", "attrs"],
        map_keys={"attrs": ["http.method"]},
        limit=3,
        sample=1000,
    )
    values.update(kwargs)
    return FacetRequest(**values)


@pytest.fixture
def ch_client():
    with patch("telescope.fetchers.clickhouse.ClickhouseConnect") as connect:
        client = MagicMock()
        connect.return_value.__enter__.return_value.client = client
        yield client


def test_plan_facets_ids_and_kinds():
    plan = facets.plan_facets(make_request(make_source()))
    assert [(f.id, f.kind, f.key) for f in plan] == [
        ("service", "value", None),
        ("attrs", "keys", None),
        ("attrs.http.method", "value", "http.method"),
    ]


def test_clickhouse_sql_is_one_sampled_scan():
    request = make_request(make_source(settings="max_threads=2"), text="refused")
    sql, params = facets.clickhouse_sql(
        request, "service = 'a'", facets.plan_facets(request)
    )
    assert params == {"facet_key_3": "http.method", "facet_text": "refused"}
    assert "[(0, CAST(NULL, 'Nullable(String)'))]" in sql
    assert "arrayMap(v -> (1, toNullable(toString(v))), [`service`])" in sql
    assert "arrayMap(v -> (2, toNullable(toString(v))), mapKeys(`attrs`))" in sql
    assert (
        "if(mapContains(`attrs`, {facet_key_3:String}), [`attrs`[{facet_key_3:String}]], [])"
        in sql
    )
    assert "(service = 'a')" in sql
    assert "positionCaseInsensitive(toString(`Body`), {facet_text:String}) > 0" in sql
    assert "ORDER BY `ts` DESC LIMIT 1000)" in sql
    assert sql.endswith(
        "GROUP BY idx, value ORDER BY idx, cnt DESC, value LIMIT 4 BY idx SETTINGS max_threads=2"
    )
    # Map keys never reach the SQL text, only bound parameters.
    assert "http.method" not in sql


def test_fetch_clickhouse_response(ch_client):
    ch_client.query.return_value = Mock(
        result_rows=[
            (0, None, 1000),
            (1, "api", 600),
            (1, "web", 300),
            (1, "db", 90),
            (1, "", 10),
            (2, "http.method", 700),
            (3, "GET", 650),
            (3, None, 50),
        ],
        summary={"read_rows": "1200"},
    )
    result = facets.fetch_clickhouse(make_request(make_source(), query="code=200"))
    sql = ch_client.query.call_args.args[0]
    assert "`code` = 200" in sql or "code = 200" in sql
    settings = ch_client.query.call_args.kwargs["settings"]
    assert settings["max_rows_to_read"] == facets.DEFAULT_MAX_ROWS_TO_READ
    assert settings["read_overflow_mode"] == "break"
    assert result == {
        "facets": {
            "service": [
                {"value": "api", "count": 600},
                {"value": "web", "count": 300},
                {"value": "db", "count": 90},
            ],
            "attrs.http.method": [
                {"value": "GET", "count": 650},
                {"value": None, "count": 50},
            ],
        },
        "map_keys": {"attrs": [{"value": "http.method", "count": 700}]},
        "more": ["service"],
        "total_sampled": 1000,
        "sampled": True,
    }


def test_fetch_clickhouse_unsampled_unless_read_limit_hit(ch_client):
    request = make_request(make_source(), columns=["service"], map_keys={})
    ch_client.query.return_value = Mock(
        result_rows=[(0, None, 10), (1, "api", 10)], summary={"read_rows": "10"}
    )
    assert facets.fetch_clickhouse(request)["sampled"] is False
    ch_client.query.return_value = Mock(
        result_rows=[(0, None, 10), (1, "api", 10)],
        summary={"read_rows": str(facets.DEFAULT_MAX_ROWS_TO_READ)},
    )
    assert facets.fetch_clickhouse(request)["sampled"] is True


def test_max_rows_to_read_grows_with_sample():
    request = make_request(make_source(), sample=5_000_000)
    assert facets.max_rows_to_read(request) == 5_000_000


def test_starrocks_statements():
    request = make_request(make_source("starrocks"), raw_query="code > 1")
    statements = facets.starrocks_sql(request, "true", facets.plan_facets(request))
    cte = (
        "WITH s AS (SELECT `attrs`, `service` FROM cat.db.logs WHERE `ts` BETWEEN "
        f"to_datetime_ntz({T0}, 3) and to_datetime_ntz({T0 + HOUR}, 3) AND (true) AND (code > 1)"
        " ORDER BY `ts` DESC LIMIT 1000) "
    )
    hint = "SELECT /*+ SET_VAR(query_timeout=30) */"
    assert statements[0] == f"{cte}{hint} count(*) FROM s"
    assert statements[1] == (
        f"{cte}{hint} * FROM (SELECT 1, cast(s.`service` as string) AS v, count(*) AS cnt FROM s"
        " GROUP BY v ORDER BY cnt DESC, v LIMIT 4) f"
    )
    assert "unnest(map_keys(s.`attrs`)) AS t(k)" in statements[2]
    assert (
        "element_at(s.`attrs`, 'http.method') AS v, count(*) AS cnt FROM s"
        " WHERE element_at(s.`attrs`, 'http.method') IS NOT NULL" in statements[3]
    )


def test_starrocks_text_is_escaped():
    request = make_request(make_source("starrocks"), text="it's")
    statements = facets.starrocks_sql(request, "true", [])
    assert "instr(lower(cast(`Body` as string)), lower('it\\'s')) > 0" in statements[0]


def row(t, **data):
    return Mock(time={"unixtime": t}, data=data)


def test_count_rows_python():
    source = make_source("docker")
    rows = [
        row(1, service="a", attrs={"k": "x"}, Body="Connection refused"),
        row(2, service="b", attrs={}, Body="ok"),
        row(3, service="a", attrs={"k": "y", "j": 1}, Body="refused again"),
        row(4, service=None, attrs={"k": "x"}, Body="REFUSED"),
    ]
    request = make_request(
        source, map_keys={"attrs": ["k"]}, limit=1, sample=10, text="refused"
    )
    result = facets.count_rows(request, rows)
    assert result == {
        "facets": {
            "service": [{"value": "a", "count": 2}],
            "attrs.k": [{"value": "x", "count": 2}],
        },
        "map_keys": {"attrs": [{"value": "k", "count": 3}]},
        "more": ["service", "attrs", "attrs.k"],
        "total_sampled": 3,
        "sampled": False,
    }


def test_count_rows_keeps_newest_sample():
    rows = [row(t, service=str(t % 2)) for t in range(10)]
    request = make_request(
        make_source("docker"), columns=["service"], map_keys={}, sample=3
    )
    result = facets.count_rows(request, rows)
    assert result["total_sampled"] == 3 and result["sampled"] is True
    assert result["facets"]["service"] == [
        {"value": "1", "count": 2},
        {"value": "0", "count": 1},
    ]


def test_kubernetes_error_is_raised():
    fetcher = Mock()
    fetcher._collect_rows.return_value = ([], "boom")
    with pytest.raises(ValueError, match="boom"):
        facets.fetch_rows_counted(make_request(make_source("kubernetes")), fetcher)


def test_body_column_prefers_otel_role():
    source = make_source(otel={"roles": {"body": "service"}})
    assert facets.body_column(source) == "service"
    assert facets.body_column(make_source()) == "Body"
