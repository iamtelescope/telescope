"""P3.4 row panel on the P0.2 data: the planted exception and the restarting pod's CPU, against SQL."""

import pytest
from rest_framework.test import APIClient

from telescope.models import Connection, Source
from telescope_otel.detect import detect
from telescope_otel.views import read_table
from tests.otel import columns as C
from tests.rowpanel.rowpaneljs import call, ui_source

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]


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


def make_source(slug, connection, database, table, time_column, links):
    columns, tables = read_table(connection.data, database, table)
    otel = detect(table, columns, tables)["otel"]
    otel["links"] = links
    return Source.create(
        kind="clickhouse",
        data={
            "slug": slug,
            "name": slug,
            "description": "",
            "time_column": time_column,
            "date_column": "",
            "severity_column": "",
            "columns": C.source_columns(columns),
            "default_chosen_columns": [time_column],
            "conn": connection,
            "data": {"database": database, "table": table, "otel": otel},
        },
    )


@pytest.fixture
def sources(connection, otel_db):
    links = {"metrics": "p34-metrics", "traces": "p34-traces"}
    return {
        "logs": make_source(
            "p34-logs", connection, otel_db, "otel_logs", "Timestamp", links
        ),
        "traces": make_source(
            "p34-traces", connection, otel_db, "otel_traces", "Timestamp", {}
        ),
        "metrics": make_source(
            "p34-metrics", connection, otel_db, "otel_metrics_gauge", "TimeUnix", {}
        ),
    }


def post(user, path, body):
    client = APIClient()
    client.force_login(user)
    doc = client.post(f"/ui/v1/sources/{path}", body, format="json").json()
    assert doc["result"] and doc["validation"]["result"], doc
    return doc["data"]


def rows(user, source, query, frm=0, to="now"):
    body = {"columns": "Timestamp", "from": frm, "to": to, "query": query}
    body.update({"limit": 10, "context_columns": {}})
    return post(user, f"{source.slug}/data", body)["rows"]


def js_source(source):
    return ui_source(source.kind, source.data["otel"], source.columns)


def test_planted_exception_log_shows_type_and_stack(
    tmp_path, root_user, sources, otel_facts, ch_client, otel_db
):
    f = otel_facts["exception_log"]
    ids = f"TraceId = '{f['trace_id']}' and SpanId = '{f['span_id']}'"
    (row,) = rows(root_user, sources["logs"], f"{ids} and SeverityText = 'ERROR'")
    expected = ch_client.query(
        f"SELECT LogAttributes['exception.type'], LogAttributes['exception.stacktrace']"
        f" FROM `{otel_db}`.otel_logs WHERE TraceId = %(t)s AND SpanId = %(s)s"
        " AND SeverityText = 'ERROR'",
        parameters={"t": f["trace_id"], "s": f["span_id"]},
    ).result_rows
    assert expected == [("GatewayTimeoutError", expected[0][1])]
    (exc,) = call(tmp_path, "exceptions", js_source(sources["logs"]), row)
    assert (exc["type"], exc["stacktrace"], exc["origin"]) == (
        *expected[0],
        "attributes",
    )
    assert "Traceback" in exc["stacktrace"]

    # The span of that log carries the same exception as a span event.
    (span,) = rows(root_user, sources["traces"], ids)
    (event,) = call(tmp_path, "exceptions", js_source(sources["traces"]), span)
    assert (event["type"], event["origin"]) == ("GatewayTimeoutError", "event")


def test_restarting_pod_log_shows_cpu_near_95(
    tmp_path, root_user, sources, otel_facts, ch_client, otel_db
):
    pod = otel_facts["restarting_pod"]["pod"]
    t0 = ch_client.command(
        f"SELECT toUnixTimestamp64Milli(Timestamp) FROM `{otel_db}`.otel_logs"
        " WHERE ResourceAttributes['k8s.pod.name'] = %(p)s"
        " AND Body LIKE 'cart service started%%' ORDER BY Timestamp LIMIT 1 OFFSET 10",
        parameters={"p": pod},
    )
    query = f"ResourceAttributes.'k8s.pod.name' = '{pod}' and Body ~ 'cart service started.*'"
    (row,) = rows(root_user, sources["logs"], query, t0, t0 + 1)
    logs, metrics = js_source(sources["logs"]), js_source(sources["metrics"])
    assert call(tmp_path, "infraAvailable", logs, row) is True
    group = call(tmp_path, "infraGroups", logs, row)[0]
    assert (group["title"], group["value"]) == ("Pod", pod)

    t = row["time"]["unixtime"]
    window = call(tmp_path, "infraWindow", row, 30 * 60000, t + 10**9)
    cpu = group["charts"][0]
    body = call(tmp_path, "infraChartRequest", metrics, group, cpu, window)
    data = post(root_user, f"{sources['metrics'].slug}/chartData", body)
    assert data["step_ms"] == 60000
    got = call(tmp_path, "valueAt", data, t)
    expected = ch_client.command(
        f"SELECT avg(Value) * 100 FROM `{otel_db}`.otel_metrics_gauge"
        " WHERE MetricName = 'k8s.pod.cpu.utilization'"
        " AND ResourceAttributes['k8s.pod.name'] = %(p)s"
        " AND toStartOfMinute(TimeUnix) = toStartOfMinute(fromUnixTimestamp64Milli(%(t)s))",
        parameters={"p": pod, "t": t},
    )
    assert got == pytest.approx(float(expected), rel=1e-9)
    assert 94 <= got <= 96
    # Every bucket of the hour is the planted ~95%.
    values = [v for v in data["series"][-1]["values"] if v is not None]
    assert len(values) >= 55 and min(values) > 93
