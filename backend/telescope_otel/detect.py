# Recognise the OpenTelemetry ClickHouse exporter schemas and prefill roles and source settings.
# Adapted from HyperDX packages/app/src/source.ts (inferTableSourceConfig).

from telescope_otel.roles import DEFAULT_DURATION_PRECISION, METRIC_KINDS

LOG_COLUMNS = {
    "Timestamp",
    "Body",
    "SeverityText",
    "TraceId",
    "SpanId",
    "ServiceName",
    "LogAttributes",
    "ResourceAttributes",
}
TRACE_COLUMNS = {
    "Timestamp",
    "SpanName",
    "Duration",
    "SpanKind",
    "TraceId",
    "SpanId",
    "ParentSpanId",
    "ServiceName",
    "SpanAttributes",
    "ResourceAttributes",
    "StatusCode",
    "StatusMessage",
}
METRIC_COLUMNS = {
    "TimeUnix",
    "MetricName",
    "ServiceName",
    "Attributes",
    "ResourceAttributes",
}
DATE_TYPES = ("date", "date32")


def _base_type(type_):
    t = type_.strip()
    while True:
        for wrapper in ("Nullable(", "LowCardinality("):
            if t.startswith(wrapper) and t.endswith(")"):
                t = t[len(wrapper) : -1]
                break
        else:
            return t


def _is_integer(type_):
    return _base_type(type_).lower().lstrip("u").startswith("int")


def _metric_kind(names):
    if "PositiveBucketCounts" in names:
        return "exponential_histogram"
    if "BucketCounts" in names and "ExplicitBounds" in names:
        return "histogram"
    if "ValueAtQuantiles.Quantile" in names:
        return "summary"
    if "Value" in names:
        return "sum" if "AggregationTemporality" in names else "gauge"
    return None


def _date_column(columns, time_column):
    """A Date/Date32 column next to the time column; Telescope needs a real date type here."""
    for name, type_ in columns:
        if name != time_column and _base_type(type_).lower() in DATE_TYPES:
            return name
    return ""


def _pick(names, *candidates):
    return next((c for c in candidates if c in names), "")


def _metric_tables(table, kind, tables):
    """Sibling tables named like `<prefix><kind>`, e.g. otel_metrics_gauge -> otel_metrics_sum."""
    if not table.endswith(kind):
        return {kind: table}
    prefix = table[: -len(kind)]
    return {k: prefix + k for k in METRIC_KINDS if prefix + k in tables}


def detect(table, columns, tables=()):
    """{"otel", "settings"} for an OTel exporter table, else None. `columns` is [(name, type)],
    `tables` the table names of the same database."""
    names = {name for name, _ in columns}
    types = dict(columns)

    if LOG_COLUMNS <= names:
        signal = "logs"
        roles = {
            "timestamp": "Timestamp",
            "body": "Body",
            "severity_text": "SeverityText",
            "severity_number": (
                "SeverityNumber" if _is_integer(types.get("SeverityNumber", "")) else ""
            ),
            "service": "ServiceName",
            "trace_id": "TraceId",
            "span_id": "SpanId",
            "resource_attrs": "ResourceAttributes",
            "attrs": "LogAttributes",
            "scope": _pick(names, "ScopeName"),
        }
        time_column = "Timestamp"
        severity = "SeverityText"
        default = ["Timestamp", "ServiceName", "SeverityText", "Body"]
    elif TRACE_COLUMNS <= names:
        signal = "traces"
        roles = {
            "timestamp": "Timestamp",
            "trace_id": "TraceId",
            "span_id": "SpanId",
            "parent_span_id": "ParentSpanId",
            "span_name": "SpanName",
            "span_kind": "SpanKind",
            "duration": "Duration",
            "duration_precision": DEFAULT_DURATION_PRECISION,
            "status_code": "StatusCode",
            "status_message": "StatusMessage",
            "service": "ServiceName",
            "resource_attrs": "ResourceAttributes",
            "attrs": "SpanAttributes",
            "events": "Events" if "Events.Timestamp" in names else "",
            "links": "Links" if "Links.TraceId" in names else "",
        }
        time_column = "Timestamp"
        severity = "StatusCode"
        default = ["Timestamp", "ServiceName", "SpanName", "StatusCode", "Duration"]
    elif METRIC_COLUMNS <= names and _metric_kind(names):
        signal = "metrics"
        kind = _metric_kind(names)
        roles = {
            "timestamp": "TimeUnix",
            "start_time": _pick(names, "StartTimeUnix"),
            "metric_name": "MetricName",
            "metric_unit": _pick(names, "MetricUnit"),
            "value": _pick(names, "Value"),
            "service": "ServiceName",
            "resource_attrs": "ResourceAttributes",
            "attrs": "Attributes",
            "scope": _pick(names, "ScopeName"),
        }
        time_column = "TimeUnix"
        severity = ""
        default = ["TimeUnix", "ServiceName", "MetricName"]
        default += ["Value"] if "Value" in names else ["Count", "Sum"]
    else:
        return None

    otel = {
        "signal": signal,
        "roles": {k: v for k, v in roles.items() if v != ""},
        "links": {},
    }
    if signal == "metrics":
        otel["metric_tables"] = _metric_tables(table, kind, set(tables))
    return {
        "otel": otel,
        "settings": {
            "time_column": time_column,
            "date_column": _date_column(columns, time_column),
            "severity_column": severity,
            "default_chosen_columns": [c for c in default if c in names],
        },
    }
