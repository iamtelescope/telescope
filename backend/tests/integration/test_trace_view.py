"""P2.3 trace view on the planted P0.2 trace: tree, duration, errors, linked logs and RBAC."""

from datetime import datetime

import pytest
from rest_framework.test import APIClient

from telescope.models import Connection, Source
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope_otel.detect import detect
from telescope_otel.trace import fetch_trace
from telescope_otel.views import read_table
from tests.otel import columns as C

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]
rbac_manager = RBACManager()


def ms(iso):
    return int(datetime.fromisoformat(iso[:26] + "+00:00").timestamp() * 1000)


@pytest.fixture
def connection(ch_settings_dict):
    s = ch_settings_dict
    return Connection.objects.create(
        kind="clickhouse",
        name="ch",
        description="",
        data={
            "host": s["host"],
            "port": s["port"],
            "user": s["username"],
            "password": s["password"],
            "ssl": False,
            "verify": False,
        },
    )


def make_source(slug, connection, database, table, links):
    columns, tables = read_table(connection.data, database, table)
    otel = detect(table, columns, tables)["otel"]
    otel["links"] = links
    return Source.create(
        kind="clickhouse",
        data={
            "slug": slug,
            "name": slug,
            "description": "",
            "time_column": "Timestamp",
            "date_column": "",
            "severity_column": "",
            "columns": C.source_columns(columns),
            "default_chosen_columns": ["Timestamp"],
            "conn": connection,
            "data": {"database": database, "table": table, "otel": otel},
        },
    )


@pytest.fixture
def sources(connection, otel_db):
    traces = make_source(
        "p23-traces", connection, otel_db, "otel_traces", {"logs": "p23-logs"}
    )
    logs = make_source(
        "p23-logs", connection, otel_db, "otel_logs", {"traces": "p23-traces"}
    )
    return traces, logs


@pytest.fixture
def big(otel_facts):
    return otel_facts["big_trace"]


def post(user, path, body):
    client = APIClient()
    client.force_login(user)
    return client.post(f"/ui/v1/otel/{path}", body, format="json").json()


def test_big_trace_tree(root_user, sources, big, ch_client, otel_db):
    resp = post(
        root_user,
        "p23-traces/trace",
        {"trace_id": big["trace_id"], "around_ms": ms(big["start"])},
    )
    assert resp["result"], resp
    trace = resp["data"]
    spans = trace["spans"]
    assert trace["span_count"] == len(spans) == big["spans"] == 57
    assert trace["services"] == big["services"]
    assert trace["truncated"] is False

    rows = ch_client.query(
        "SELECT SpanId, ParentSpanId, StatusCode FROM {db:Identifier}.otel_traces"
        " WHERE TraceId = {t:String}",
        parameters={"db": otel_db, "t": big["trace_id"]},
    ).result_rows
    parents = {span: parent for span, parent, _ in rows}
    assert {
        s["id"]: spans[s["parent"]]["id"] if s["parent"] is not None else ""
        for s in spans
    } == parents
    roots = [s for s in spans if s["parent"] is None]
    assert len(roots) == 1 and roots[0]["depth"] == 0 and not roots[0]["synthetic"]
    for s in spans[1:]:
        assert spans[s["parent"]]["depth"] == s["depth"] - 1
        assert spans.index(s) > s["parent"]

    errored = {s["id"] for s in spans if s["error"]}
    assert errored == {span for span, _, code in rows if code == "Error"}
    assert trace["error_count"] == big["error_spans"] == 4

    lo, hi = ch_client.query(
        "SELECT toUnixTimestamp64Nano(min(Timestamp)), max(toUnixTimestamp64Nano(Timestamp) + Duration)"
        " FROM {db:Identifier}.otel_traces WHERE TraceId = {t:String}",
        parameters={"db": otel_db, "t": big["trace_id"]},
    ).result_rows[0]
    assert trace["duration_ns"] == hi - lo
    assert trace["start_ns"] == str(lo)
    assert trace["duration_ns"] == ms(big["end"]) * 10**6 - ms(big["start"]) * 10**6

    # The critical path covers the root's whole duration exactly once.
    segments = sorted(seg for s in spans for seg in s["critical"])
    assert segments[0][0] == 0 and segments[-1][1] == roots[0]["duration_ns"]
    assert all(a[1] == b[0] for a, b in zip(segments, segments[1:]))


def test_default_lookup_is_last_24h(sources, big):
    traces = sources[0]
    end = ms(big["end"])
    assert fetch_trace(traces, big["trace_id"], now_ms=end + 3600_000)["found"]
    assert not fetch_trace(traces, big["trace_id"], now_ms=end + 25 * 3600_000)["found"]
    assert not fetch_trace(traces, big["trace_id"], around_ms=end + 2 * 3600_000)[
        "found"
    ]


def test_linked_logs_are_exactly_the_trace_logs(
    root_user, sources, big, ch_client, otel_db
):
    resp = post(
        root_user,
        "p23-traces/traceLogs",
        {"trace_id": big["trace_id"], "around_ms": ms(big["start"])},
    )
    assert resp["result"], resp
    data = resp["data"]
    expected = ch_client.query(
        "SELECT toString(toUnixTimestamp64Nano(Timestamp)), SpanId, Body FROM {db:Identifier}.otel_logs"
        " WHERE TraceId = {t:String} ORDER BY Timestamp",
        parameters={"db": otel_db, "t": big["trace_id"]},
    ).result_rows
    assert len(expected) > 0
    assert [(r["ts_ns"], r["span_id"], r["body"]) for r in data["logs"]] == [
        tuple(r) for r in expected
    ]
    assert data["source"] == "p23-logs" and data["truncated"] is False


def test_logs_need_use_on_the_logs_source(test_user, sources, big):
    traces, logs = sources
    body = {"trace_id": big["trace_id"], "around_ms": ms(big["start"])}
    assert post(test_user, "p23-traces/trace", body)["errors"] == ["source not found"]

    rbac_manager.grant_source_role(traces, SourceRole.USER.value, user=test_user)
    trace = post(test_user, "p23-traces/trace", body)
    assert trace["result"] and trace["data"]["span_count"] == 57
    resp = post(test_user, "p23-traces/traceLogs", body)
    assert not resp["result"]
    assert resp["errors"] == ["no access to logs source p23-logs"]

    rbac_manager.grant_source_role(logs, SourceRole.USER.value, user=test_user)
    assert post(test_user, "p23-traces/traceLogs", body)["result"]


def test_missing_parent_hangs_under_synthetic_root(connection, ch_client, otel_db, big):
    ch_client.command("CREATE DATABASE IF NOT EXISTS telescope_test")
    ch_client.command("DROP TABLE IF EXISTS telescope_test.p23_traces")
    ch_client.command(
        f"CREATE TABLE telescope_test.p23_traces AS `{otel_db}`.otel_traces"
    )
    try:
        # Drop checkout's server span: its children lose their parent.
        missing = ch_client.query(
            "SELECT SpanId FROM {db:Identifier}.otel_traces WHERE TraceId = {t:String}"
            " AND ServiceName = 'checkout' AND SpanName = 'POST /checkout'",
            parameters={"db": otel_db, "t": big["trace_id"]},
        ).result_rows[0][0]
        ch_client.command(
            f"INSERT INTO telescope_test.p23_traces SELECT * FROM `{otel_db}`.otel_traces"
            f" WHERE TraceId = '{big['trace_id']}' AND SpanId != '{missing}'"
        )
        source = make_source(
            "p23-orphans", connection, "telescope_test", "p23_traces", {}
        )
        trace = fetch_trace(source, big["trace_id"], around_ms=ms(big["start"]))
        spans = trace["spans"]
        assert trace["span_count"] == 56
        synthetic = [s for s in spans if s["synthetic"]]
        assert len(synthetic) == 1
        root = synthetic[0]
        assert root["id"] == missing and root["parent"] is None and root["depth"] == 0
        orphans = [s for s in spans if s["parent_id"] == missing]
        assert orphans and all(spans[s["parent"]] is root for s in orphans)
        assert root["children"] == len(orphans)
    finally:
        ch_client.command("DROP TABLE IF EXISTS telescope_test.p23_traces")
