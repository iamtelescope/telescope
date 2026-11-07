import pytest

pytestmark = pytest.mark.clickhouse


def test_planted_trace(ch_client, otel_db, otel_facts):
    sql = f"SELECT count(), uniqExact(ServiceName) FROM `{otel_db}`.otel_traces WHERE TraceId = %(t)s"
    assert ch_client.query(
        sql, parameters={"t": otel_facts["trace_id"]}
    ).result_rows == [(57, 5)]


def test_planted_error_spike(ch_client, otel_db, otel_facts):
    spike = otel_facts["error_spike"]
    sql = (
        "SELECT toStartOfInterval(Timestamp, INTERVAL 5 MINUTE) AS w, count() AS n "
        f"FROM `{otel_db}`.otel_logs WHERE {spike['query']} GROUP BY w HAVING n > 50 ORDER BY w"
    )
    assert [n for _, n in ch_client.query(sql).result_rows] == spike[
        "error_logs_per_5m_spike"
    ]
