from unittest.mock import MagicMock, Mock, patch

import pytest
from flyql import parse
from flyql.matcher import Evaluator, Record

from telescope.flyql_registry import transformer_registry
from telescope.models import Source, SourceColumn
from telescope.patterns import fetch
from telescope.patterns.drain import Drain
from telescope.patterns.fetch import PatternRequest
from telescope.patterns.masking import normalize
from telescope.patterns.mine import like_filter, mine_patterns, trend_step

T0 = 1767225600000
HOUR = 3600 * 1000

# The generator's cart templates (dev/otel/generate.py), one line each.
CART = [
    ("cart service started pid={} port=8080", 2),
    ("loaded cart for user user_{} items={}", 30),
    ("added item SKU-{} qty={} to cart cart_{}", 20),
    ("cache miss for cart cart_{} fetching from database", 15),
    ("slow query detected on cart_items took {} ms threshold=200ms", 5),
    ("cache evicted {} entries", 10),
    ("failed to reserve inventory for cart cart_{} retry {} of 3", 3),
]


def cart_rows():
    rows = []
    for i, (template, n) in enumerate(CART):
        for j in range(n):
            args = [i * 100 + j + 1] * template.count("{}")
            rows.append((T0 + (j * 7 + i) * 60000, template.format(*args)))
    return rows


def test_drain_merges_variable_tokens():
    drain = Drain()
    a = drain.add("user 1 logged in from web")
    b = drain.add("user 2 logged in from app")
    c = drain.add("disk full")
    assert a is b and a is not c
    assert a.template == "user <*> logged in from <*>" and a.size == 2
    assert c.template == "disk full"


def test_drain_keeps_dissimilar_messages_apart():
    drain = Drain()
    a = drain.add("connection opened to db")
    b = drain.add("request finished in time")
    assert a is not b


def test_normalize_strips_ansi_and_whitespace():
    assert normalize("\x1b[31mERROR\x1b[0m  disk\n full ") == "ERROR disk full"
    assert normalize(None) == ""


def test_cart_templates_mine_into_seven_patterns():
    rows = cart_rows()
    result = mine_patterns(rows, len(rows), T0, T0 + 6 * HOUR, "Body")
    counts = {p["pattern"]: p["count"] for p in result["patterns"]}
    assert counts == {
        "cart service started <*> port=8080": 2,
        "loaded cart for user <*> <*>": 30,
        "added item <*> <*> to cart <*>": 20,
        "cache miss for cart <*> fetching from database": 15,
        "slow query detected on cart_items took <*> ms threshold=200ms": 5,
        "cache evicted <*> entries": 10,
        "failed to reserve inventory for cart <*> retry <*> of 3": 3,
    }
    assert [p["count"] for p in result["patterns"]] == sorted(counts.values())[::-1]


def test_filter_matches_every_member():
    rows = cart_rows()
    result = mine_patterns(rows, len(rows), T0, T0 + 6 * HOUR, "Body")
    evaluator = Evaluator(registry=transformer_registry())
    for pattern in result["patterns"]:
        root = parse(pattern["filter"]).root
        matched = [
            body
            for _, body in rows
            if evaluator.evaluate(root, Record(data={"Body": body}))
        ]
        assert len(matched) == pattern["count"], pattern["filter"]


def test_like_filter_escapes():
    assert like_filter("Body", "took <*> ms 100% cart_items") == (
        "Body like 'took % ms 100\\% cart\\_items'"
    )
    assert like_filter("Body", "it's a\\b ok") == "Body like '% % ok'"


def test_scaling_trend_and_samples():
    rows = [(T0 + i * 60000, f"job {i} done") for i in range(10)]
    result = mine_patterns(rows, 40, T0, T0 + 24 * HOUR, "msg")
    assert result["step"] == HOUR and len(result["buckets"]) == 24
    assert result["buckets"][0] == T0
    (pattern,) = result["patterns"]
    assert pattern["count"] == 10 and pattern["est_total"] == 40
    assert pattern["share"] == 1.0
    assert pattern["trend"][0] == 40 and sum(pattern["trend"]) == 40
    assert [r["body"] for r in pattern["sample_rows"]] == [
        "job 0 done",
        "job 1 done",
        "job 2 done",
    ]
    assert (result["total"], result["sample_size"], result["column"]) == (
        40,
        10,
        "msg",
    )


def test_empty_sample():
    result = mine_patterns([], 0, T0, T0 + HOUR, "Body")
    assert result["patterns"] == [] and result["sample_size"] == 0


def test_trend_step_aligns_to_standard_steps():
    assert trend_step(T0, T0 + HOUR) == 300_000
    assert trend_step(T0, T0 + 7 * 24 * HOUR) == 12 * HOUR


def make_source(kind="clickhouse"):
    source = Mock(spec=Source)
    source.kind = kind
    source.data = {"database": "db", "table": "logs", "settings": ""}
    source.time_column, source.date_column = "ts", ""
    source._columns = {
        n: SourceColumn(n, "", t, False, True, True, True, [])
        for n, t in {"ts": "DateTime64(3)", "Body": "String"}.items()
    }
    source.columns = dict(source._columns)
    source.conn = Mock(data={})
    return source


def make_request(source, **kwargs):
    values = dict(source=source, time_from=T0, time_to=T0 + HOUR, column="Body")
    values.update(kwargs)
    return PatternRequest(**values)


def test_clickhouse_sample_sql():
    request = make_request(make_source(), sample=500)
    sql = fetch.clickhouse_sample_sql(request, "true", None)
    assert "SAMPLE" not in sql
    assert sql.endswith("WHERE true ORDER BY rand() LIMIT 500")
    assert "toString(`Body`)" in sql
    assert " FROM db.logs SAMPLE 0.250000 WHERE" in fetch.clickhouse_sample_sql(
        request, "true", 0.25
    )


def test_clickhouse_where_binds_text():
    params = {}
    where = fetch.clickhouse_where(
        make_request(make_source(), query="Body='x'", text="boom"), params
    )
    assert "(Body = 'x')" in where
    assert "{telescope_text:String}" in where and params == {"telescope_text": "boom"}


@pytest.fixture
def ch_client():
    with patch("telescope.fetchers.clickhouse.ClickhouseConnect") as connect:
        client = MagicMock()
        connect.return_value.__enter__.return_value.client = client
        yield client


@pytest.mark.parametrize(
    "sampling_key, total, ratio",
    [("", 5000, None), ("id", 5000, 0.24), ("id", 10, None)],
)
def test_fetch_clickhouse_uses_sample_with_a_sampling_key(
    ch_client, sampling_key, total, ratio
):
    ch_client.query.side_effect = [
        Mock(result_rows=[[total]]),
        Mock(result_rows=[[sampling_key]]),
        Mock(result_rows=[[T0, "a 1"], [T0 + 1, "a 2"]]),
    ]
    with patch.object(fetch, "clickhouse_sample_sql", return_value="S") as sample_sql:
        rows, got_total = fetch.fetch_clickhouse(
            make_request(make_source(), sample=1000)
        )
    assert rows == [(T0, "a 1"), (T0 + 1, "a 2")] and got_total == total
    assert sample_sql.call_args.args[2] == (pytest.approx(ratio) if ratio else None)


def row(t, body):
    return Mock(time={"unixtime": t}, data={"message": body})


def test_fetch_rows_samples_docker_rows():
    fetcher = Mock()
    fetcher._collect_rows.return_value = [row(T0 + i, f"m {i}") for i in range(50)]
    rows, total = fetch.fetch_rows(
        make_request(make_source("docker"), column="message", sample=20), fetcher
    )
    assert total == 50 and len(rows) == 20
    assert all(body.startswith("m ") for _, body in rows)


def test_fetch_rows_raises_kubernetes_error():
    fetcher = Mock()
    fetcher._collect_rows.return_value = ([], "boom")
    with pytest.raises(ValueError, match="boom"):
        fetch.fetch_rows(make_request(make_source("kubernetes")), fetcher)


def test_fetch_patterns_docker_and_kubernetes_share_the_python_path():
    for kind in ("docker", "kubernetes"):
        fetcher = Mock()
        fetcher._collect_rows.return_value = [
            row(T0 + i, f"user {i} logged in") for i in range(5)
        ]
        with patch("telescope.fetchers.get_fetchers", return_value={kind: fetcher}):
            result = fetch.fetch_patterns(
                make_request(make_source(kind), column="message")
            )
        (pattern,) = result["patterns"]
        assert pattern["pattern"] == "user <*> logged in" and pattern["count"] == 5
        assert pattern["filter"] == "message like 'user % logged in'"


def test_fetch_patterns_refuses_starrocks():
    with pytest.raises(ValueError, match="not supported"):
        fetch.fetch_patterns(make_request(make_source("starrocks")))
