"""SQL shape of P1.2 keyset paging and bare-text search, with the database mocked."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from telescope.fetchers.clickhouse import Fetcher as ClickhouseFetcher
from telescope.fetchers.request import DataRequest
from telescope.fetchers.search import body_column, next_cursor
from telescope.fetchers.starrocks import Fetcher as StarrocksFetcher
from telescope.models import Connection, Source


def column(type_):
    return {
        "display_name": "",
        "type": type_,
        "autocomplete": False,
        "suggest": False,
        "jsonstring": False,
        "group_by": False,
        "values": [],
    }


def make_source(kind="clickhouse", uniq="", time_type="DateTime64(9)", data=None):
    source = Source(
        kind=kind,
        slug="s",
        time_column="ts",
        date_column="",
        uniq_column=uniq,
        severity_column="",
        columns={
            "ts": column(time_type),
            "id": column("UInt64"),
            "Body": column("LowCardinality(String)"),
            "attrs": column("Map(String, String)"),
        },
        default_chosen_columns=["ts"],
        support_raw_query=True,
        context_columns={},
        data=data or {"database": "db", "table": "t", "catalog": "c", "settings": ""},
    )
    source.conn = Connection(kind=kind, name="c", data={})
    return source


def request(source, **kw):
    args = dict(
        source=source,
        query="",
        raw_query="",
        time_from=1_000,
        time_to=9_000_000,
        limit=3,
        context_columns={},
    )
    args.update(kw)
    return DataRequest(**args)


@pytest.fixture
def ch():
    with patch("telescope.fetchers.clickhouse.ClickhouseConnect") as connect:
        client = MagicMock()
        client.query.return_value.result_rows = []
        connect.return_value.__enter__.return_value.client = client
        yield client


def sent(client):
    call = client.query.call_args
    return call[0][0], call[1].get("parameters")


def ch_row(cursor_time, uniq=None):
    # generateUUIDv4(), Body, attrs, id, ts, cursor time, cursor uniq
    return ("u", "b", {}, 1, datetime(2026, 1, 1), cursor_time, uniq)


def test_clickhouse_first_page_orders_by_time_then_row_hash(ch):
    ClickhouseFetcher.fetch_data(request(make_source()))
    sql, params = sent(ch)
    assert "ORDER BY `ts` DESC, cityHash64(`Body`, `attrs`, `id`, `ts`) DESC" in sql
    assert "toUnixTimestamp64Nano(`ts`)" in sql
    assert "LIMIT 3" in sql and "OFFSET" not in sql
    assert params is None


def test_clickhouse_cursor_without_uniq_uses_skip(ch):
    ch.query.return_value.result_rows = [ch_row(30), ch_row(20), ch_row(20)]
    response = ClickhouseFetcher.fetch_data(
        request(make_source(), before={"time": "20", "skip": 4})
    )
    sql, params = sent(ch)
    assert "`ts` <= fromUnixTimestamp64Nano({telescope_before_time:Int64})" in sql
    assert "LIMIT 3 OFFSET 4" in sql
    assert params == {"telescope_before_time": 20}
    # Two rows share the last time, plus the 4 skipped before at the same time.
    assert response.cursor == {"time": "20", "skip": 6}


def test_clickhouse_cursor_narrows_the_time_range(ch):
    ClickhouseFetcher.fetch_data(
        request(make_source(), before={"time": "5000000001", "skip": 0})
    )
    sql, _ = sent(ch)
    # 5000000001 ns rounds up to 5001 ms
    assert "fromUnixTimestamp64Milli(5001)" in sql


def test_clickhouse_cursor_with_uniq(ch):
    ch.query.return_value.result_rows = [
        ch_row(30, "9"),
        ch_row(20, "8"),
        ch_row(20, "7"),
    ]
    response = ClickhouseFetcher.fetch_data(
        request(make_source(uniq="id"), before={"time": "40", "uniq": "1"})
    )
    sql, params = sent(ch)
    assert (
        "(`ts` < fromUnixTimestamp64Nano({telescope_before_time:Int64}) OR (`ts` = fromUnixTimestamp64Nano"
        "({telescope_before_time:Int64}) AND toString(`id`) < {telescope_before_uniq:String}))"
    ) in sql
    assert "ORDER BY `ts` DESC, toString(`id`) DESC" in sql
    assert params == {"telescope_before_time": 40, "telescope_before_uniq": "1"}
    assert response.cursor == {"time": "20", "uniq": "7"}
    assert [r.data["id"] for r in response.rows] == [1, 1, 1]


def test_clickhouse_short_page_has_no_cursor(ch):
    ch.query.return_value.result_rows = [ch_row(30)]
    assert ClickhouseFetcher.fetch_data(request(make_source())).cursor is None


@pytest.mark.parametrize(
    "time_type,value,bound",
    [
        (
            "DateTime",
            "toInt64(toUnixTimestamp(`ts`))",
            "toDateTime({telescope_before_time:Int64})",
        ),
        ("UInt64", "toInt64(`ts`)", "{telescope_before_time:Int64}"),
    ],
)
def test_clickhouse_cursor_per_time_type(ch, time_type, value, bound):
    ClickhouseFetcher.fetch_data(
        request(make_source(time_type=time_type), before={"time": "7", "skip": 0})
    )
    sql, _ = sent(ch)
    assert value in sql and f"`ts` <= {bound}" in sql


def test_clickhouse_text_is_a_bound_parameter(ch):
    ClickhouseFetcher.fetch_data(request(make_source(), text="it's 100%"))
    sql, params = sent(ch)
    assert "positionCaseInsensitiveUTF8(`Body`, {telescope_text:String}) > 0" in sql
    assert "it's" not in sql
    assert params == {"telescope_text": "it's 100%"}


def test_clickhouse_text_on_non_string_body_casts(ch):
    source = make_source()
    source.columns["Body"]["type"] = "Map(String, String)"
    ClickhouseFetcher.fetch_data(request(source, text="x"))
    assert "positionCaseInsensitiveUTF8(toString(`Body`)" in sent(ch)[0]


def test_text_without_body_column_fails():
    source = make_source()
    source.columns.pop("Body")
    with pytest.raises(ValueError, match="no body column"):
        ClickhouseFetcher.fetch_data(request(source, text="x"))


def test_body_column_prefers_the_otel_role():
    source = make_source()
    source.columns["message"] = column("String")
    assert body_column(source) == "Body"
    source.data["otel"] = {"roles": {"body": "message"}}
    assert body_column(source) == "message"
    source.data["otel"] = {"roles": {"body": "missing"}}
    assert body_column(source) == "Body"


def test_next_cursor_end_and_skip_accumulation():
    source = make_source()
    assert next_cursor(source, [(3, None)], 2, None) is None
    keys = [(5, None), (5, None)]
    assert next_cursor(source, keys, 2, None) == {"time": "5", "skip": 2}
    assert next_cursor(source, keys, 2, {"time": "5", "skip": 2}) == {
        "time": "5",
        "skip": 4,
    }
    assert next_cursor(source, keys, 2, {"time": "6", "skip": 2}) == {
        "time": "5",
        "skip": 2,
    }


@pytest.fixture
def sr():
    with patch("telescope.fetchers.starrocks.StarrocksConnect") as connect:
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        connect.return_value.__enter__.return_value.client.cursor.return_value = cursor
        yield cursor


def sr_row(ts, uniq=None):
    # uuid_numeric(), Body, attrs, id, ts, cursor uniq
    return (1, "b", {}, 7, ts, uniq)


def test_starrocks_text_and_skip_cursor(sr):
    source = make_source(kind="starrocks", time_type="DATETIME")
    t = datetime(2026, 1, 1, 0, 0, 1, 5)
    sr.fetchall.return_value = [sr_row(t), sr_row(t), sr_row(t)]
    response = StarrocksFetcher.fetch_data(
        request(
            source,
            text="O'Brien",
            before={"time": "2026-01-01 00:00:01.000005", "skip": 3},
        )
    )
    sql = sr.execute.call_args[0][0]
    assert "instr(lower(CAST(`Body` AS STRING)), lower('O\\'Brien')) > 0" in sql
    assert "`ts` <= '2026-01-01 00:00:01.000005'" in sql
    assert "LIMIT 3 OFFSET 3" in sql
    assert "ORDER BY `ts` DESC, murmur_hash3_32(concat_ws('|', " in sql
    assert "`attrs`" not in sql.split("ORDER BY")[1]
    assert response.cursor == {"time": "2026-01-01 00:00:01.000005", "skip": 6}


def test_starrocks_uniq_cursor(sr):
    source = make_source(kind="starrocks", uniq="id", time_type="DATETIME")
    t5, t4 = datetime(2026, 1, 1, 0, 0, 5), datetime(2026, 1, 1, 0, 0, 4)
    sr.fetchall.return_value = [sr_row(t5, "3"), sr_row(t4, "2"), sr_row(t4, "1")]
    response = StarrocksFetcher.fetch_data(
        request(source, before={"time": "9", "uniq": "4"})
    )
    sql = sr.execute.call_args[0][0]
    assert "(`ts` < '9' OR (`ts` = '9' AND CAST(`id` AS STRING) < '4'))" in sql
    assert response.cursor == {"time": "2026-01-01 00:00:04.000000", "uniq": "1"}
