"""P1.2 against a real ClickHouse: keyset "load more", bound bare-text search and the live-tail window."""

import uuid
from datetime import datetime, timezone

import pytest

from telescope.fetchers.clickhouse import Fetcher
from telescope.fetchers.request import DataRequest, GraphDataRequest
from telescope.models import Connection, Source
from telescope.utils import get_telescope_column

pytestmark = pytest.mark.clickhouse


def iso_ms(iso):
    return int(
        datetime.fromisoformat(iso[:26] + "+00:00").timestamp() * 1000
    )  # facts.json ISO with ns -> ms


def make_source(ch_client, ch_settings_dict, database, table, uniq_column=""):
    rows = ch_client.query(
        "SELECT name, type FROM system.columns WHERE database = %(d)s AND table = %(t)s",
        parameters={"d": database, "t": table},
    ).result_rows
    columns = {}
    for name, type_ in rows:
        column = get_telescope_column(name, type_)
        column.pop("name")
        column["values"] = []
        columns[name] = column
    time_column = "Timestamp" if "Timestamp" in columns else "ts"
    source = Source(
        kind="clickhouse",
        slug=f"t-{table}",
        name=table,
        time_column=time_column,
        date_column="",
        uniq_column=uniq_column,
        severity_column="",
        columns=columns,
        default_chosen_columns=list(columns),
        support_raw_query=True,
        context_columns={},
        data={"database": database, "table": table, "settings": ""},
    )
    source.conn = Connection(
        kind="clickhouse",
        name="t",
        data={
            "host": ch_settings_dict["host"],
            "port": ch_settings_dict["port"],
            "user": ch_settings_dict["username"],
            "password": ch_settings_dict["password"],
            "ssl": False,
            "verify": False,
        },
    )
    return source


def page(source, time_from, time_to, limit, before=None, text="", query=""):
    return Fetcher.fetch_data(
        DataRequest(
            source=source,
            query=query,
            raw_query="",
            time_from=time_from,
            time_to=time_to,
            limit=limit,
            context_columns={},
            before=before,
            text=text,
        )
    )


def identity(row):
    d = row.data
    return (d["Timestamp"], d["TraceId"], d["SpanId"], d["ServiceName"], d["Body"])


@pytest.fixture(scope="module")
def otel_logs(ch_client, ch_settings_dict, otel_db):
    return make_source(ch_client, ch_settings_dict, otel_db, "otel_logs")


@pytest.fixture(scope="module")
def window(otel_facts):
    return iso_ms(otel_facts["start"]), iso_ms(otel_facts["end"])


def collect(source, time_from, time_to, limit, pages):
    rows, before = [], None
    for _ in range(pages):
        response = page(source, time_from, time_to, limit, before)
        rows += response.rows
        before = response.cursor
        assert before is not None
    return rows, before


def oracle(ch_client, db, time_from, time_to, n):
    return ch_client.query(
        f"SELECT Timestamp, TraceId, SpanId, ServiceName, Body FROM `{db}`.otel_logs"
        f" WHERE Timestamp BETWEEN fromUnixTimestamp64Milli({time_from}) AND fromUnixTimestamp64Milli({time_to})"
        f" ORDER BY Timestamp DESC LIMIT {n}"
    ).result_rows


def assert_same_rows(rows, expected):
    got = [identity(r) for r in rows]
    # Ties in the oracle may come in any order, so compare per timestamp.
    assert [g[0].replace(tzinfo=None) for g in got] == [e[0] for e in expected]
    assert sorted(map(repr_row, got)) == sorted(map(repr_row, expected))


def repr_row(r):
    return (r[0].replace(tzinfo=None).isoformat(),) + tuple(r[1:])


def test_load_more_five_pages_has_no_duplicates_or_gaps(
    ch_client, otel_db, otel_logs, window
):
    limit = 1000
    rows, _ = collect(otel_logs, *window, limit, 5)
    assert len(rows) == 5 * limit
    expected = oracle(ch_client, otel_db, *window, 5 * limit)
    assert_same_rows(rows, expected)
    assert len({repr_row(identity(r)) for r in rows}) == len(
        {repr_row(e) for e in expected}
    )


def test_load_more_cuts_inside_a_shared_timestamp(
    ch_client, otel_db, otel_logs, window
):
    # The densest millisecond: page boundaries of size 2 fall inside it.
    ts, n = ch_client.query(
        f"SELECT Timestamp, count() c FROM `{otel_db}`.otel_logs GROUP BY Timestamp ORDER BY c DESC, Timestamp LIMIT 1"
    ).result_rows[0]
    assert n >= 3
    to_ms = int(ts.replace(tzinfo=timezone.utc).timestamp() * 1000)
    time_from = to_ms - 2000
    rows, before = collect(otel_logs, time_from, to_ms, 2, n)
    assert before["time"] and before["skip"] >= 1
    expected = oracle(ch_client, otel_db, time_from, to_ms, 2 * n)
    assert_same_rows(rows, expected)


def test_last_page_has_no_cursor(otel_logs, window):
    response = page(otel_logs, window[0], window[0] + 60_000, 100_000)
    assert response.rows and response.cursor is None


@pytest.fixture
def sent(monkeypatch):
    """Every (sql, parameters) the fetcher hands to ClickHouse."""
    import telescope.fetchers.clickhouse as ch

    calls = []
    real = ch._client_query

    def spy(client, sql, **kw):
        calls.append((sql, kw.get("parameters")))
        return real(client, sql, **kw)

    monkeypatch.setattr(ch, "_client_query", spy)
    return calls


def test_text_search_finds_planted_rows_with_a_bound_parameter(
    otel_logs, window, otel_facts, sent
):
    fact = otel_facts["connection_refused"]
    response = page(otel_logs, *window, 1000, text=fact["text"].upper())
    assert len(response.rows) == fact["rows"] == 25
    assert {r.data["ServiceName"] for r in response.rows} == {fact["service"]}
    assert all("connection refused" in r.data["Body"].lower() for r in response.rows)
    # The SQL sent carries a placeholder only; the value travels as param_telescope_text.
    sql, params = sent[-1]
    assert "{telescope_text:String}" in sql
    assert "connection refused" not in sql.lower()
    assert params["telescope_text"] == fact["text"].upper()


def test_text_search_quotes_are_data(otel_logs, window, sent):
    for text in ["' OR 1=1 OR '", "\\' OR 1=1 --", "{x:String}"]:
        assert page(otel_logs, *window, 10, text=text).rows == []
        assert text not in sent[-1][0]


def test_text_filters_the_histogram_too(otel_logs, window, otel_facts):
    fact = otel_facts["connection_refused"]
    graph = Fetcher.fetch_graph_data(
        GraphDataRequest(
            source=otel_logs,
            query="",
            raw_query="",
            time_from=window[0],
            time_to=window[1],
            group_by=[],
            context_columns={},
            text=fact["text"],
        )
    )
    assert graph.total == fact["rows"]


@pytest.fixture
def live_table(ch_client, ch_settings_dict):
    db = f"telescope_p12_{uuid.uuid4().hex[:8]}"
    ch_client.command(f"CREATE DATABASE {db}")
    ch_client.command(
        f"CREATE TABLE {db}.logs (ts DateTime64(9, 'UTC'), id UInt64, body String)"
        " ENGINE = MergeTree PARTITION BY toDate(ts) ORDER BY ts"
    )
    yield db, make_source(ch_client, ch_settings_dict, db, "logs", uniq_column="id")
    ch_client.command(f"DROP DATABASE {db}")


def test_uniq_column_cursor_and_nanosecond_ties(ch_client, live_table):
    db, source = live_table
    # 30 rows on 3 timestamps 1 ns apart, so ms cursors would collide.
    base = 1_790_000_000_000_000_000
    ch_client.command(
        f"INSERT INTO {db}.logs SELECT fromUnixTimestamp64Nano(toInt64({base} + number % 3)), number, 'x'"
        " FROM numbers(30)"
    )
    time_from, time_to = base // 1_000_000 - 1, base // 1_000_000 + 1
    seen, before = [], None
    for _ in range(6):
        response = page(source, time_from, time_to, 7, before)
        seen += [r.data["id"] for r in response.rows]
        before = response.cursor
        if before is None:
            break
    assert before is None
    assert sorted(seen) == list(range(30))
    expected = [
        r[0]
        for r in ch_client.query(
            f"SELECT id FROM {db}.logs ORDER BY ts DESC, toString(id) DESC"
        ).result_rows
    ]
    assert seen == expected


def test_live_poll_reads_only_the_new_window(ch_client, live_table):
    db, source = live_table
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    old = now_ms - 3 * 86_400_000
    ch_client.command(
        f"INSERT INTO {db}.logs SELECT fromUnixTimestamp64Milli(toInt64({old} + number)), number, 'old'"
        " FROM numbers(100000)"
    )
    ch_client.command(
        f"INSERT INTO {db}.logs SELECT fromUnixTimestamp64Milli(toInt64({now_ms} + number)), 1000000 + number, 'new'"
        " FROM numbers(5)"
    )
    marker = f"live-{uuid.uuid4().hex}"
    response = page(source, now_ms, now_ms + 10_000, 50, query=f"body != '{marker}'")
    assert [r.data["body"] for r in response.rows] == ["new"] * 5
    if not ch_client.command("EXISTS TABLE system.query_log"):
        pytest.skip("system.query_log is not configured on this server")
    ch_client.command("SYSTEM FLUSH LOGS")
    read_rows, sql = ch_client.query(
        "SELECT read_rows, query FROM system.query_log WHERE type = 'QueryFinish' AND query LIKE %(m)s"
        " AND query NOT LIKE '%%system.query_log%%' ORDER BY event_time_microseconds DESC LIMIT 1",
        parameters={"m": f"%{marker}%"},
    ).result_rows[0]
    assert f"fromUnixTimestamp64Milli({now_ms})" in sql
    assert read_rows < 100_000
