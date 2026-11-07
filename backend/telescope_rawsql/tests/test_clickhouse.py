"""P5.1 acceptance against a real ClickHouse: read-only, bounded, and no way to inject through variables."""

import pytest
from clickhouse_connect.driver.exceptions import DatabaseError

from telescope.fetchers.clickhouse import ClickhouseConnect, _client_query
from telescope_rawsql.query import QUERY_SETTINGS
from telescope_rawsql.tests.conftest import T0, client_for, grant, query

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]

HOSTILE = "x' OR 1=1 --"


@pytest.fixture
def client(ch_connection, sql_user):
    return client_for(grant(ch_connection, sql_user))


def run(client, ch_connection, sql, **body):
    response = query(client, ch_connection.pk, sql, **body)
    assert response.status_code == 200, response.content
    return response.json()


def rows(client, ch_connection, sql, **body):
    result = run(client, ch_connection, sql, **body)
    assert result["result"] and result["validation"]["result"], result
    return result["data"]["rows"]


def refused(client, ch_connection, sql, **body):
    result = run(client, ch_connection, sql, **body)
    assert not result["validation"]["result"], result
    return result["validation"]["fields"]["sql"][0]


def test_select_with_macros(client, ch_connection):
    sql = """
        SELECT $__timeInterval(ts) AS t, count() AS c, any($__interval_s) AS step,
            any(toUnixTimestamp($__fromTime)) AS f, any(toUnixTimestamp($__toTime)) AS e
        FROM (SELECT toDateTime(intDiv({start:Int64}, 1000) + number * 60) AS ts FROM numbers(120))
        WHERE $__timeFilter(ts)
        GROUP BY t ORDER BY t LIMIT 2
    """
    result = run(client, ch_connection, sql, params={"start": T0 - 1800000})
    assert result["data"]["columns"] == [
        {"name": "t", "type": "DateTime"},
        {"name": "c", "type": "UInt64"},
        {"name": "step", "type": "Int64"},
        {"name": "f", "type": "UInt32"},
        {"name": "e", "type": "UInt32"},
    ]
    first = result["data"]["rows"][0]
    # Only the 61 minutes inside [from, to] remain, bucketed by the 1m auto step.
    assert first[1:] == [1, 60, T0 // 1000, T0 // 1000 + 3600]
    total = rows(
        client,
        ch_connection,
        "SELECT count() FROM (SELECT toDateTime(intDiv({start:Int64}, 1000) + number * 60) AS ts"
        " FROM numbers(120)) WHERE $__timeFilter(ts)",
        params={"start": T0 - 1800000},
    )
    assert total == [[61]]


def test_runs_read_only_with_limits(client, ch_connection):
    sql = (
        "SELECT getSetting('readonly'), getSetting('max_execution_time'),"
        " getSetting('max_result_rows')"
    )
    assert rows(client, ch_connection, sql) == [[2, 30.0, 1001]]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1 SETTINGS readonly = 0",
        "SELECT 1 SETTINGS max_execution_time = 100000",
        "SELECT * FROM (SELECT 1 SETTINGS max_result_rows = 0)",
        "SELECT 1 FROM numbers(2) WHERE 1 IN (SELECT 1 SETTINGS readonly = 0)",
    ],
)
def test_settings_overrides_are_refused(client, ch_connection, sql):
    assert refused(client, ch_connection, sql) == "SETTINGS clauses are not allowed"


def test_breaking_out_of_the_wrapper_is_refused(client, ch_connection):
    # Closing the wrapper's parenthesis to put a clause outside it.
    for sql in [
        "SELECT 1) SETTINGS readonly = 0 UNION ALL (SELECT 1",
        "SELECT 1) UNION ALL (SELECT 1 SETTINGS readonly = 0",
        "SELECT 1) LIMIT 1000000 --",
        "SELECT 1) LIMIT 5000 UNION ALL SELECT 1 FROM (SELECT 1",
    ]:
        assert refused(client, ch_connection, sql)


def test_readonly_holds_even_past_the_guard(ch_connection):
    # Defence in depth: the server itself refuses to lift readonly=2.
    with ClickhouseConnect(ch_connection.data) as c:
        with pytest.raises(DatabaseError, match="readonly"):
            _client_query(
                c.client, "SELECT 1 SETTINGS readonly = 0", settings=QUERY_SETTINGS
            )
        with pytest.raises(DatabaseError, match="READONLY|readonly"):
            _client_query(
                c.client,
                "CREATE TABLE default.p51_rawsql_probe (a Int8) ENGINE = Memory",
                settings=QUERY_SETTINGS,
            )


@pytest.mark.parametrize(
    "sql,error",
    [
        ("SHOW TABLES", "only SELECT queries are allowed"),
        (
            "INSERT INTO logs.app SELECT * FROM logs.app",
            "only SELECT queries are allowed",
        ),
        ("DROP TABLE logs.app", "only SELECT queries are allowed"),
        ("SELECT 1; DROP TABLE logs.app", "multi-statement queries are not allowed"),
        ("SELECT 1 FORMAT JSON", "Syntax error"),
        ("SELECT 1 INTO OUTFILE '/tmp/x'", "Syntax error"),
        ("WITH 1 AS x SHOW TABLES", "Syntax error"),
        ("SELECT * FROM url('http://127.0.0.1:18123/', CSV)", "table function url"),
        ("SELECT * FROM file('x.csv')", "table function file"),
        ("SELECT * FROM remote('127.0.0.1', system.one)", "table function remote"),
        (
            "SELECT 1 WHERE 1 IN (SELECT 1 FROM url('http://x/', CSV))",
            "table function url",
        ),
    ],
)
def test_non_select_and_external_reads_are_refused(client, ch_connection, sql, error):
    assert error in refused(client, ch_connection, sql)


def test_allowed_shapes(client, ch_connection):
    assert rows(client, ch_connection, "SELECT ';' AS s;") == [[";"]]
    assert rows(client, ch_connection, "WITH 2 AS x SELECT x -- trailing comment") == [
        [2]
    ]
    assert rows(client, ch_connection, "SELECT count() FROM numbers(3)") == [[3]]
    assert rows(client, ch_connection, "SELECT 1 UNION ALL SELECT 2") in (
        [[1], [2]],
        [[2], [1]],
    )


def test_variables_cannot_inject(client, ch_connection):
    params = {"v": HOSTILE, "many": ["a", HOSTILE]}
    sql = (
        "SELECT {v:String}, count() FROM numbers(10)"
        " WHERE toString(number) = {v:String} OR 'a' IN {many:Array(String)} AND 0"
    )
    assert rows(client, ch_connection, sql, params=params) == [[HOSTILE, 0]]
    assert rows(
        client, ch_connection, "SELECT {many:Array(String)}", params=params
    ) == [[["a", HOSTILE]]]
    # Values are never parsed as SQL, macros or other placeholders.
    for value in ["$__fromTime", "{v:String}", "1); DROP TABLE logs.app; --"]:
        assert rows(
            client, ch_connection, "SELECT {v:String}", params={"v": value}
        ) == [[value]]
    # Without placeholders, clickhouse_connect's client-side %-formatting must not run.
    assert rows(
        client, ch_connection, "SELECT '%(v)s', '{v}'", params={"v": HOSTILE}
    ) == [["%(v)s", "{v}"]]


def test_a_variable_cannot_override_the_time_range(client, ch_connection):
    params = {"startDateMilliseconds": "0", "rawSqlLimit": "1000000"}
    assert rows(
        client,
        ch_connection,
        "SELECT {startDateMilliseconds:Int64}, getSetting('max_result_rows')",
        params=params,
    ) == [[T0, 1001]]


def test_a_type_mismatch_fails_instead_of_injecting(client, ch_connection):
    result = run(client, ch_connection, "SELECT {n:UInt32}", params={"n": "1 OR 1=1"})
    assert not result["validation"]["result"] or not result["result"]
    assert "rows" not in result["data"]


def test_row_and_byte_limits(client, ch_connection):
    result = run(client, ch_connection, "SELECT number FROM numbers(5000)")
    assert len(result["data"]["rows"]) == 1000 and result["data"]["truncated"]
    # ClickHouse checks max_result_bytes after each block, so only the setting is asserted.
    sql = "SELECT getSetting('max_result_bytes'), getSetting('result_overflow_mode')"
    assert rows(client, ch_connection, sql) == [[10 * 1024 * 1024, "throw"]]


def test_query_errors_are_query_failed(client, ch_connection):
    result = run(client, ch_connection, "SELECT * FROM p51_no_such.table")
    assert not result["result"] and result["data"] == {"code": "query_failed"}


def test_values_are_json(client, ch_connection):
    sql = (
        "SELECT toDateTime64('2026-11-06 10:00:00.123', 3, 'UTC'), toDecimal64(1.5, 2),"
        " nan, map('k', [1, 2]), toUUID('00000000-0000-0000-0000-000000000001'),"
        " toIPv4('10.0.0.1'), NULL"
    )
    (row,) = rows(client, ch_connection, sql)
    assert row == [
        "2026-11-06T10:00:00.123000",
        1.5,
        None,
        {"k": [1, 2]},
        "00000000-0000-0000-0000-000000000001",
        "10.0.0.1",
        None,
    ]
