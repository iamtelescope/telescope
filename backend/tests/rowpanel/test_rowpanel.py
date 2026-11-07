"""P3.4: what the row panel's Overview and Infrastructure tabs derive from a row (rowpanel.js)."""

import pytest

from tests.rowpanel.rowpaneljs import call, ui_source

LOG_ROLES = {
    "timestamp": "Timestamp",
    "body": "Body",
    "severity_text": "SeverityText",
    "service": "ServiceName",
    "trace_id": "TraceId",
    "span_id": "SpanId",
    "resource_attrs": "ResourceAttributes",
    "attrs": "LogAttributes",
    "scope": "ScopeName",
}
TRACE_ROLES = {
    "trace_id": "TraceId",
    "span_id": "SpanId",
    "span_name": "SpanName",
    "duration": "Duration",
    "duration_precision": 9,
    "status_code": "StatusCode",
    "service": "ServiceName",
    "resource_attrs": "ResourceAttributes",
    "attrs": "SpanAttributes",
    "events": "Events",
}
METRIC_ROLES = {
    "metric_name": "MetricName",
    "value": "Value",
    "resource_attrs": "ResourceAttributes",
}
STACK = 'Traceback (most recent call last):\n  File "/app/payment/gateway.py", line 203, in _post\nGatewayTimeoutError'
RESOURCE = {
    "service.name": "payment",
    "service.version": "3.0.2",
    "host.name": "payment-1",
    "k8s.namespace.name": "payments",
    "k8s.node.name": "k8s-node-1",
    "k8s.pod.name": "payment-1",
}
LOG_ROW = {
    "time": {"unixtime": 1767268833082, "microseconds": "082000"},
    "data": {
        "Timestamp": "2026-01-01 12:00:33.082000",
        "TraceId": "48be0a02058c9faade57bb5d79a01b67",
        "SpanId": "26c3e5617552d4e3",
        "SeverityText": "ERROR",
        "ServiceName": "payment",
        "Body": '{"order": {"id": "ord_1", "items": [1, 2]}, "ok": false}',
        "ResourceAttributes": RESOURCE,
        "ScopeName": "payment.logger",
        "LogAttributes": {
            "exception.type": "GatewayTimeoutError",
            "exception.message": "payment gateway timeout after 5000ms",
            "exception.stacktrace": STACK,
            "http.method": "POST",
            "http.route": "/charge",
            "http.status_code": "500",
            "http.request.header.content-type": "application/json",
            "http.response.body": '{"error":"timeout"}',
        },
    },
}
SPAN_ROW = {
    "time": {"unixtime": 1767268833037, "microseconds": "037819"},
    "data": {
        "TraceId": "48be0a02058c9faade57bb5d79a01b67",
        "SpanId": "26c3e5617552d4e3",
        "SpanName": "POST /charge",
        "ServiceName": "payment",
        "Duration": 187985903,
        "StatusCode": "Error",
        "ResourceAttributes": RESOURCE,
        "SpanAttributes": {"http.request.method": "POST", "url.path": "/charge"},
        "Events.Timestamp": [
            "2026-01-01 12:00:33.100000",
            "2026-01-01 12:00:33.207006",
        ],
        "Events.Name": ["retry", "exception"],
        "Events.Attributes": [
            {"attempt": "2"},
            {"exception.type": "UpstreamError", "exception.stacktrace": STACK},
        ],
    },
}
LOGS = ui_source("clickhouse", {"signal": "logs", "roles": LOG_ROLES})
TRACES = ui_source("clickhouse", {"signal": "traces", "roles": TRACE_ROLES})
METRICS = ui_source("clickhouse", {"signal": "metrics", "roles": METRIC_ROLES})


def test_only_otel_logs_and_traces_are_enriched(tmp_path):
    assert call(tmp_path, "isEnriched", LOGS) is True
    assert call(tmp_path, "isEnriched", TRACES) is True
    assert call(tmp_path, "isEnriched", METRICS) is False
    assert call(tmp_path, "isEnriched", ui_source("clickhouse", None)) is False
    otel_on_docker = ui_source("docker", {"signal": "logs", "roles": LOG_ROLES})
    assert call(tmp_path, "isEnriched", otel_on_docker) is False
    assert (
        call(tmp_path, "infraAvailable", ui_source("clickhouse", None), LOG_ROW)
        is False
    )


def test_exception_from_log_attributes(tmp_path):
    assert call(tmp_path, "exceptions", LOGS, LOG_ROW) == [
        {
            "type": "GatewayTimeoutError",
            "message": "payment gateway timeout after 5000ms",
            "stacktrace": STACK,
            "origin": "attributes",
        }
    ]


def test_exception_from_span_events_and_events_list(tmp_path):
    assert call(tmp_path, "exceptions", TRACES, SPAN_ROW) == [
        {"type": "UpstreamError", "message": "", "stacktrace": STACK, "origin": "event"}
    ]
    events = call(tmp_path, "spanEvents", TRACES, SPAN_ROW)
    assert [e["name"] for e in events] == ["retry", "exception"]
    assert events[0] == {
        "time": "2026-01-01 12:00:33.100000",
        "name": "retry",
        "attributes": {"attempt": "2"},
    }
    assert call(tmp_path, "spanEvents", LOGS, LOG_ROW) == []


def test_no_exception_without_exception_attributes(tmp_path):
    row = {**LOG_ROW, "data": {**LOG_ROW["data"], "LogAttributes": {"a": "b"}}}
    assert call(tmp_path, "exceptions", LOGS, row) == []


def test_http_message_old_and_new_semconv(tmp_path):
    log = call(tmp_path, "httpMessage", LOGS, LOG_ROW)
    assert (log["method"], log["route"], log["status"]) == ("POST", "/charge", "500")
    assert log["requestHeaders"] == [
        {"name": "content-type", "value": "application/json"}
    ]
    assert log["responseBody"] == '{"error":"timeout"}'
    span = call(tmp_path, "httpMessage", TRACES, SPAN_ROW)
    assert (span["method"], span["url"]) == ("POST", "/charge")
    row = {**LOG_ROW, "data": {**LOG_ROW["data"], "LogAttributes": {"a": "b"}}}
    assert call(tmp_path, "httpMessage", LOGS, row) is None


def test_highlighted_defaults_and_configured_keys(tmp_path):
    got = call(tmp_path, "highlighted", LOGS, LOG_ROW)
    assert [h["key"] for h in got] == [
        "service.version",
        "k8s.namespace.name",
        "k8s.pod.name",
        "host.name",
    ]
    assert got[2] == {
        "key": "k8s.pod.name",
        "value": "payment-1",
        "path": ["ResourceAttributes", "k8s.pod.name"],
    }
    configured = ui_source(
        "clickhouse",
        {
            "signal": "logs",
            "roles": LOG_ROLES,
            "highlighted": ["http.route", "ScopeName", "missing", "service.name"],
        },
    )
    assert call(tmp_path, "highlighted", configured, LOG_ROW) == [
        {
            "key": "http.route",
            "value": "/charge",
            "path": ["LogAttributes", "http.route"],
        },
        {"key": "ScopeName", "value": "payment.logger", "path": ["ScopeName"]},
        {
            "key": "service.name",
            "value": "payment",
            "path": ["ResourceAttributes", "service.name"],
        },
    ]


def test_top_level_and_duration(tmp_path):
    top = call(tmp_path, "topLevel", TRACES, SPAN_ROW)
    assert [t["role"] for t in top] == [
        "service",
        "span_name",
        "status_code",
        "duration",
        "trace_id",
        "span_id",
    ]
    assert call(tmp_path, "durationNs", TRACES, 187985903) == 187985903
    micros = ui_source(
        "clickhouse",
        {"signal": "traces", "roles": {**TRACE_ROLES, "duration_precision": 6}},
    )
    assert call(tmp_path, "durationNs", micros, 1500) == 1500000


def test_parsed_body_flattens_json(tmp_path):
    assert call(tmp_path, "parsedBody", LOGS, LOG_ROW) == [
        {"path": ["Body", "order", "id"], "value": "ord_1"},
        {"path": ["Body", "order", "items", "0"], "value": 1},
        {"path": ["Body", "order", "items", "1"], "value": 2},
        {"path": ["Body", "ok"], "value": False},
    ]
    row = {**LOG_ROW, "data": {**LOG_ROW["data"], "Body": "plain {text"}}
    assert call(tmp_path, "parsedBody", LOGS, row) is None


@pytest.mark.parametrize(
    "path,field",
    [
        (["ServiceName"], "ServiceName"),
        (["ResourceAttributes", "k8s.pod.name"], 'ResourceAttributes."k8s.pod.name"'),
        (["LogAttributes", 'a"b.c'], 'LogAttributes."a\\"b.c"'),
    ],
)
def test_query_field_quotes_dotted_segments(tmp_path, path, field):
    assert call(tmp_path, "queryField", path) == field


def test_row_link_query(tmp_path):
    assert call(tmp_path, "rowLinkQuery", LOGS, LOG_ROW) == {
        "from": 1767268832082,
        "to": 1767268834082,
        "query": "TraceId = '48be0a02058c9faade57bb5d79a01b67' and SpanId = '26c3e5617552d4e3'",
    }
    row = {**LOG_ROW, "data": {**LOG_ROW["data"], "TraceId": "", "SpanId": "x'y"}}
    assert call(tmp_path, "rowLinkQuery", LOGS, row)["query"] == "SpanId = 'x\\'y'"


def test_infra_groups_need_pod_or_node(tmp_path):
    groups = call(tmp_path, "infraGroups", LOGS, LOG_ROW)
    assert [(g["title"], g["value"]) for g in groups] == [
        ("Pod", "payment-1"),
        ("Node", "k8s-node-1"),
    ]
    assert call(tmp_path, "infraAvailable", LOGS, LOG_ROW) is True
    res = {"service.name": "payment"}
    row = {**LOG_ROW, "data": {**LOG_ROW["data"], "ResourceAttributes": res}}
    assert call(tmp_path, "infraGroups", LOGS, row) == []
    assert call(tmp_path, "infraAvailable", LOGS, row) is False


def test_infra_chart_request(tmp_path):
    pod = call(tmp_path, "infraGroups", LOGS, LOG_ROW)[0]
    window = call(tmp_path, "infraWindow", LOG_ROW, 1800000, 1767268833082 + 60000)
    assert window == {"from": 1767268833082 - 1800000, "to": 1767268833082 + 60000}
    cpu, memory, restarts = pod["charts"]
    req = call(tmp_path, "infraChartRequest", METRICS, pod, cpu, window)
    assert req["query"] == "ResourceAttributes.'k8s.pod.name' = 'payment-1'"
    assert req["series"] == [
        {
            "agg": "avg",
            "column": "Value",
            "alias": "value",
            "where": "MetricName = 'k8s.pod.cpu.utilization'",
            "hidden": True,
        },
        {"agg": "formula", "formula": "value * 100", "alias": "CPU usage"},
    ]
    req = call(tmp_path, "infraChartRequest", METRICS, pod, restarts, window)
    assert req["series"] == [
        {
            "agg": "max",
            "column": "Value",
            "alias": "Container restarts",
            "where": "MetricName = 'k8s.container.restarts'",
        }
    ]


def test_value_at_row_time(tmp_path):
    data = {
        "timestamps": [0, 60000, 120000],
        "series": [
            {"name": "value", "values": [0.5, 0.95, None]},
            {"name": "CPU usage", "values": [50, 95, None]},
        ],
    }
    assert call(tmp_path, "valueAt", data, 90000) == 95
    assert call(tmp_path, "valueAt", data, 130000) is None
    assert call(tmp_path, "valueAt", data, -1) is None
    data["series"][1]["values"][0] = 0
    assert call(tmp_path, "valueAt", data, 0) == 0
