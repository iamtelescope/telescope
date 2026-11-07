# Source.data["otel"] = {"signal", "roles": {role: column}, "links": {signal: slug}, "metric_tables"}.
# Role lists follow HyperDX packages/api/src/models/source.ts.

import re

SIGNALS = ("logs", "traces", "metrics")

ROLES = {
    "logs": (
        "timestamp",
        "body",
        "severity_text",
        "severity_number",
        "service",
        "trace_id",
        "span_id",
        "resource_attrs",
        "attrs",
        "scope",
    ),
    "traces": (
        "timestamp",
        "trace_id",
        "span_id",
        "parent_span_id",
        "span_name",
        "span_kind",
        "duration",
        "duration_precision",
        "status_code",
        "status_message",
        "service",
        "resource_attrs",
        "attrs",
        "events",
        "links",
    ),
    "metrics": (
        "timestamp",
        "start_time",
        "metric_name",
        "metric_unit",
        "value",
        "service",
        "resource_attrs",
        "attrs",
        "scope",
    ),
}

# Roles that name a Nested column, stored flattened as `<name>.<field>` columns.
NESTED_ROLES = {"events", "links"}
METRIC_KINDS = ("gauge", "sum", "histogram", "exponential_histogram", "summary")
# 9 = nanoseconds, 6 = microseconds, 3 = milliseconds, 0 = seconds.
DURATION_PRECISIONS = (0, 3, 6, 9)
DEFAULT_DURATION_PRECISION = 9

_TABLE_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,256}$")
_SLUG_RE = re.compile(r"^[-a-zA-Z0-9_]{1,64}$")


def column_exists(name, columns):
    return name in columns or any(c.startswith(name + ".") for c in columns)


def validate_otel(otel, columns, source_exists=None):
    """Error messages for an otel block, empty when valid. `columns` None skips column checks,
    `source_exists` None skips link checks."""
    if not isinstance(otel, dict):
        return ["otel must be an object"]
    errors = []
    unknown = set(otel) - {"signal", "roles", "links", "metric_tables"}
    if unknown:
        errors.append(f"unknown otel keys: {', '.join(sorted(unknown))}")

    signal = otel.get("signal")
    if signal not in SIGNALS:
        return errors + [f"signal must be one of {', '.join(SIGNALS)}"]

    roles = otel.get("roles", {})
    if not isinstance(roles, dict):
        errors.append("roles must be an object")
        roles = {}
    for role, value in roles.items():
        if role not in ROLES[signal]:
            errors.append(f"unknown {signal} role {role}")
        elif role == "duration_precision":
            if value not in DURATION_PRECISIONS:
                errors.append(
                    "duration_precision must be one of "
                    + ", ".join(map(str, DURATION_PRECISIONS))
                )
        elif value in (None, ""):
            continue
        elif not isinstance(value, str):
            errors.append(f"role {role} must be a column name")
        elif columns is not None and not column_exists(value, columns):
            errors.append(f"column {value} not found")

    links = otel.get("links", {})
    if not isinstance(links, dict):
        errors.append("links must be an object")
        links = {}
    for target, slug in links.items():
        if target not in SIGNALS:
            errors.append(f"unknown link {target}")
        elif slug in (None, ""):
            continue
        elif not isinstance(slug, str) or not _SLUG_RE.match(slug):
            errors.append(f"link {target} must be a source slug")
        elif source_exists is not None and not source_exists(slug):
            errors.append(f"source {slug} not found")

    tables = otel.get("metric_tables")
    if tables is not None:
        if signal != "metrics":
            errors.append("metric_tables is only allowed for metrics")
        elif not isinstance(tables, dict):
            errors.append("metric_tables must be an object")
        else:
            for kind, table in tables.items():
                if kind not in METRIC_KINDS:
                    errors.append(f"unknown metric table kind {kind}")
                elif table in (None, ""):
                    continue
                elif not isinstance(table, str) or not _TABLE_RE.match(table):
                    errors.append(f"metric table {kind} must be a table name")
    return errors


def validate_source_otel(attrs):
    """Serializer hook for a ClickHouse source: {"otel": [errors]} or {}; drops a null block."""
    from telescope.models import Source

    data = attrs.get("data") or {}
    if "otel" not in data:
        return {}
    if data["otel"] is None:
        data.pop("otel")
        return {}
    errors = validate_otel(
        data["otel"],
        attrs.get("columns"),
        lambda slug: Source.objects.filter(slug=slug).exists(),
    )
    return {"otel": errors} if errors else {}
