"""P1.4 facet counts against plain GROUP BY on the P0.2 otel_logs data."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from telescope.fetchers.facets import FacetRequest, fetch_facets
from telescope.models import Source, SourceColumn

pytestmark = pytest.mark.clickhouse

COLUMNS = {
    "Timestamp": "DateTime64(9)",
    "ServiceName": "LowCardinality(String)",
    "SeverityText": "LowCardinality(String)",
    "SeverityNumber": "UInt8",
    "Body": "String",
    "LogAttributes": "Map(LowCardinality(String), String)",
}


def ms(iso):
    return int(datetime.fromisoformat(iso[:26] + "+00:00").timestamp() * 1000)


@pytest.fixture
def source(ch_settings_dict, otel_db):
    source = Mock(spec=Source)
    source.kind = "clickhouse"
    source.data = {"database": otel_db, "table": "otel_logs", "settings": ""}
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


@pytest.fixture
def window(otel_facts):
    return ms(otel_facts["start"]), ms(otel_facts["end"])


def oracle(ch_client, sql):
    return [{"value": v, "count": c} for v, c in ch_client.query(sql).result_rows]


def group_by_sql(db, expr, where="1"):
    return (
        f"SELECT {expr} AS v, count() AS c FROM `{db}`.otel_logs WHERE {where}"
        " GROUP BY v ORDER BY c DESC, v LIMIT 10"
    )


def test_counts_equal_group_by(source, window, ch_client, otel_db, otel_facts):
    result = fetch_facets(
        FacetRequest(
            source=source,
            time_from=window[0],
            time_to=window[1],
            columns=["ServiceName", "SeverityNumber"],
            sample=10_000_000,
        )
    )
    assert result["sampled"] is False
    assert result["total_sampled"] == otel_facts["rows"]["otel_logs"]
    assert result["facets"]["ServiceName"] == oracle(
        ch_client, group_by_sql(otel_db, "ServiceName")
    )
    assert result["facets"]["SeverityNumber"] == oracle(
        ch_client, group_by_sql(otel_db, "toString(SeverityNumber)")
    )


def test_sampling_keeps_top_three(source, window, ch_client, otel_db):
    result = fetch_facets(
        FacetRequest(
            source=source,
            time_from=window[0],
            time_to=window[1],
            columns=["ServiceName"],
            sample=50_000,
        )
    )
    assert result["sampled"] is True and result["total_sampled"] == 50_000
    full = oracle(ch_client, group_by_sql(otel_db, "ServiceName"))
    assert [v["value"] for v in result["facets"]["ServiceName"][:3]] == [
        v["value"] for v in full[:3]
    ]


def test_map_keys_and_values(source, window, ch_client, otel_db):
    result = fetch_facets(
        FacetRequest(
            source=source,
            time_from=window[0],
            time_to=window[1],
            columns=["LogAttributes"],
            map_keys={"LogAttributes": ["http.method"]},
            sample=10_000_000,
        )
    )
    keys = oracle(
        ch_client,
        f"SELECT k AS v, count() AS c FROM `{otel_db}`.otel_logs"
        " ARRAY JOIN mapKeys(LogAttributes) AS k GROUP BY v ORDER BY c DESC, v LIMIT 10",
    )
    assert result["map_keys"]["LogAttributes"] == keys
    assert "http.method" in [k["value"] for k in keys]
    assert result["facets"]["LogAttributes.http.method"] == oracle(
        ch_client,
        group_by_sql(
            otel_db,
            "LogAttributes['http.method']",
            "mapContains(LogAttributes, 'http.method')",
        ),
    )


def test_query_filter_applies(source, window, ch_client, otel_db):
    result = fetch_facets(
        FacetRequest(
            source=source,
            time_from=window[0],
            time_to=window[1],
            query='ServiceName="payment"',
            text="payment",
            columns=["SeverityText"],
            sample=10_000_000,
        )
    )
    assert result["facets"]["SeverityText"]
    assert result["facets"]["SeverityText"] == oracle(
        ch_client,
        group_by_sql(
            otel_db,
            "SeverityText",
            "ServiceName = 'payment' AND positionCaseInsensitive(Body, 'payment') > 0",
        ),
    )
