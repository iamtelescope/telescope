"""Sources for the dashboard template tests."""

from telescope.models import Source
from telescope_otel.detect import detect
from tests.otel import columns as C

QUERY_LOG = [
    ("event_time", "DateTime"),
    (
        "type",
        "Enum8('QueryStart' = 1, 'QueryFinish' = 2, 'ExceptionBeforeStart' = 3,"
        " 'ExceptionWhileProcessing' = 4)",
    ),
    ("query_duration_ms", "UInt64"),
    ("read_rows", "UInt64"),
    ("memory_usage", "UInt64"),
    ("normalized_query_hash", "UInt64"),
    ("query_kind", "LowCardinality(String)"),
    ("tables", "Array(LowCardinality(String))"),
    ("exception_code", "Int32"),
]
METRIC_LOG = [
    ("event_time", "DateTime"),
    ("ProfileEvent_OSCPUVirtualTimeMicroseconds", "UInt64"),
    ("ProfileEvent_OSReadChars", "UInt64"),
    ("ProfileEvent_OSWriteChars", "UInt64"),
    ("CurrentMetric_Query", "Int64"),
    ("CurrentMetric_Merge", "Int64"),
    ("CurrentMetric_MemoryTracking", "Int64"),
]
PARTS = [
    ("modification_time", "DateTime"),
    ("database", "String"),
    ("table", "String"),
    ("partition", "String"),
    ("active", "UInt8"),
    ("rows", "UInt64"),
]
OTEL = {
    "otel_logs": C.LOGS,
    "otel_traces": C.TRACES,
    "otel_metrics_gauge": C.GAUGE,
}


def make_source(conn, slug, database, table, columns, time_column, otel=None):
    data = {"database": database, "table": table}
    if otel:
        data["otel"] = otel
    return Source.create(
        kind="clickhouse",
        data={
            "slug": slug,
            "name": slug,
            "description": "",
            "time_column": time_column,
            "date_column": "",
            "uniq_column": "",
            "severity_column": "",
            "columns": C.source_columns(columns),
            "default_chosen_columns": [time_column],
            "data": data,
            "conn": conn,
        },
    )


def otel_source(conn, slug, table, columns=None, database="otel"):
    columns = columns or OTEL[table]
    found = detect(table, columns, C.METRIC_TABLES)
    time_column = "TimeUnix" if table.startswith("otel_metrics") else "Timestamp"
    return make_source(conn, slug, database, table, columns, time_column, found["otel"])


def system_sources(conn, prefix="ch"):
    return {
        "query_log": make_source(
            conn, f"{prefix}-query-log", "system", "query_log", QUERY_LOG, "event_time"
        ),
        "metric_log": make_source(
            conn,
            f"{prefix}-metric-log",
            "system",
            "metric_log",
            METRIC_LOG,
            "event_time",
        ),
        "parts": make_source(
            conn, f"{prefix}-parts", "system", "parts", PARTS, "modification_time"
        ),
    }
