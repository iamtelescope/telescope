"""Column lists of the OTel exporter tables (dev/otel/schema), as system.columns reports them."""

MAP = "Map(LowCardinality(String), String)"

LOGS = [
    ("Timestamp", "DateTime64(9)"),
    ("TraceId", "String"),
    ("SpanId", "String"),
    ("TraceFlags", "UInt8"),
    ("SeverityText", "LowCardinality(String)"),
    ("SeverityNumber", "UInt8"),
    ("ServiceName", "LowCardinality(String)"),
    ("Body", "String"),
    ("ResourceSchemaUrl", "LowCardinality(String)"),
    ("ResourceAttributes", MAP),
    ("ScopeSchemaUrl", "LowCardinality(String)"),
    ("ScopeName", "String"),
    ("ScopeVersion", "LowCardinality(String)"),
    ("ScopeAttributes", MAP),
    ("LogAttributes", MAP),
    ("EventName", "String"),
]

TRACES = [
    ("Timestamp", "DateTime64(9)"),
    ("TraceId", "String"),
    ("SpanId", "String"),
    ("ParentSpanId", "String"),
    ("TraceState", "String"),
    ("SpanName", "LowCardinality(String)"),
    ("SpanKind", "LowCardinality(String)"),
    ("ServiceName", "LowCardinality(String)"),
    ("ResourceAttributes", MAP),
    ("ScopeName", "String"),
    ("ScopeVersion", "String"),
    ("SpanAttributes", MAP),
    ("Duration", "UInt64"),
    ("StatusCode", "LowCardinality(String)"),
    ("StatusMessage", "String"),
    ("Events.Timestamp", "Array(DateTime64(9))"),
    ("Events.Name", "Array(LowCardinality(String))"),
    ("Events.Attributes", f"Array({MAP})"),
    ("Links.TraceId", "Array(String)"),
    ("Links.SpanId", "Array(String)"),
    ("Links.TraceState", "Array(String)"),
    ("Links.Attributes", f"Array({MAP})"),
]

_METRIC_BASE = [
    ("ResourceAttributes", MAP),
    ("ScopeName", "String"),
    ("ServiceName", "LowCardinality(String)"),
    ("MetricName", "String"),
    ("MetricUnit", "String"),
    ("Attributes", MAP),
    ("StartTimeUnix", "DateTime64(9)"),
    ("TimeUnix", "DateTime64(9)"),
]
GAUGE = _METRIC_BASE + [("Value", "Float64"), ("Flags", "UInt32")]
SUM = GAUGE + [("AggregationTemporality", "Int32"), ("IsMonotonic", "Bool")]
HISTOGRAM = _METRIC_BASE + [
    ("Count", "UInt64"),
    ("Sum", "Float64"),
    ("BucketCounts", "Array(UInt64)"),
    ("ExplicitBounds", "Array(Float64)"),
    ("AggregationTemporality", "Int32"),
]
EXP_HISTOGRAM = _METRIC_BASE + [
    ("Count", "UInt64"),
    ("PositiveBucketCounts", "Array(UInt64)"),
]
SUMMARY = _METRIC_BASE + [
    ("Count", "UInt64"),
    ("ValueAtQuantiles.Quantile", "Array(Float64)"),
]
METRIC_TABLES = [
    "otel_metrics_gauge",
    "otel_metrics_sum",
    "otel_metrics_histogram",
    "otel_metrics_exponential_histogram",
    "otel_metrics_summary",
]


def source_columns(columns):
    return {
        name: {
            "display_name": "",
            "type": type_,
            "autocomplete": False,
            "suggest": False,
            "jsonstring": False,
            "group_by": False,
            "values": [],
        }
        for name, type_ in columns
    }
