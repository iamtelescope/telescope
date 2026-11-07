"""P2.4 event patterns against the planted cart template family of the P0.2 otel_logs data."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from telescope.models import Source, SourceColumn
from telescope.patterns import fetch
from telescope.patterns.fetch import PatternRequest, fetch_patterns

pytestmark = pytest.mark.clickhouse

COLUMNS = {
    "Timestamp": "DateTime64(9)",
    "ServiceName": "LowCardinality(String)",
    "Body": "String",
}
SAMPLED_DB = "telescope_test_patterns"


def ms(iso):
    return int(datetime.fromisoformat(iso[:26] + "+00:00").timestamp() * 1000)


def make_source(ch_settings_dict, database, table):
    source = Mock(spec=Source)
    source.kind = "clickhouse"
    source.data = {"database": database, "table": table, "settings": ""}
    source.time_column, source.date_column = "Timestamp", ""
    source._columns = {
        name: SourceColumn(name, "", t, False, True, True, True, [])
        for name, t in COLUMNS.items()
    }
    source.columns = dict(source._columns)
    source.conn = Mock(
        data={
            "host": ch_settings_dict["host"],
            "port": ch_settings_dict["port"],
            "user": ch_settings_dict["username"],
            "password": ch_settings_dict["password"],
            "ssl": False,
            "verify": False,
        }
    )
    return source


def run(source, otel_facts, sample, query="ServiceName='cart'"):
    return fetch_patterns(
        PatternRequest(
            source=source,
            time_from=ms(otel_facts["start"]),
            time_to=ms(otel_facts["end"]),
            column="Body",
            query=query,
            sample=sample,
        )
    )


@pytest.fixture
def truth(otel_facts):
    return {t["template"]: t["rows"] for t in otel_facts["cart_patterns"]["templates"]}


def test_cart_yields_exactly_seven_patterns_at_full_sample(
    ch_settings_dict, otel_db, otel_facts, truth
):
    source = make_source(ch_settings_dict, otel_db, "otel_logs")
    result = run(source, otel_facts, sample=100_000)
    assert result["total"] == result["sample_size"] == sum(truth.values())
    found = {p["pattern"]: p["est_total"] for p in result["patterns"]}
    assert len(found) == otel_facts["cart_patterns"]["count"] == 7
    assert found.keys() == truth.keys()
    for template, rows in truth.items():
        assert abs(found[template] - rows) <= 0.02 * rows
    assert sum(sum(p["trend"]) for p in result["patterns"]) == result["total"]


def test_filter_matches_its_members(ch_settings_dict, ch_client, otel_db, otel_facts):
    source = make_source(ch_settings_dict, otel_db, "otel_logs")
    for pattern in run(source, otel_facts, sample=100_000)["patterns"]:
        narrowed = run(
            source, otel_facts, 100_000, f"ServiceName='cart' and {pattern['filter']}"
        )
        assert narrowed["total"] >= 0.95 * pattern["count"], pattern["filter"]
        # The filter selects its own pattern only.
        assert [p["pattern"] for p in narrowed["patterns"]] == [pattern["pattern"]]


def test_scaled_counts_from_a_sample(ch_settings_dict, otel_db, otel_facts, truth):
    source = make_source(ch_settings_dict, otel_db, "otel_logs")
    result = run(source, otel_facts, sample=10_000)
    assert result["sample_size"] == 10_000
    found = {p["pattern"]: p["est_total"] for p in result["patterns"]}
    for template, rows in truth.items():
        if rows > 5000:
            assert abs(found[template] - rows) <= 0.1 * rows


@pytest.fixture
def sampled_table(ch_client, otel_db):
    ch_client.command(f"CREATE DATABASE IF NOT EXISTS {SAMPLED_DB}")
    ch_client.command(f"DROP TABLE IF EXISTS {SAMPLED_DB}.cart_logs")
    ch_client.command(
        f"CREATE TABLE {SAMPLED_DB}.cart_logs (Timestamp DateTime64(9), ServiceName LowCardinality(String),"
        " Body String, Id UInt64) ENGINE = MergeTree ORDER BY (ServiceName, intHash32(Id))"
        f" SAMPLE BY intHash32(Id) AS SELECT Timestamp, ServiceName, Body, rowNumberInAllBlocks()"
        f" FROM `{otel_db}`.otel_logs WHERE ServiceName = 'cart'"
    )
    yield "cart_logs"
    ch_client.command(f"DROP DATABASE {SAMPLED_DB}")


def test_sampling_key_table_uses_sample(
    ch_settings_dict, ch_client, sampled_table, otel_facts, truth
):
    source = make_source(ch_settings_dict, SAMPLED_DB, sampled_table)
    sql = fetch.clickhouse_sample_sql
    with patch.object(fetch, "clickhouse_sample_sql", side_effect=sql) as spy:
        result = run(source, otel_facts, sample=10_000)
    assert 8_000 <= result["sample_size"] <= 10_000
    assert result["total"] == sum(truth.values())
    found = {p["pattern"]: p["est_total"] for p in result["patterns"]}
    for template, rows in truth.items():
        if rows > 5000:
            assert abs(found[template] - rows) <= 0.15 * rows
    assert " SAMPLE 0." in sql(*spy.call_args.args)
