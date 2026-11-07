"""MCP tools over the services /ui/v1 and API v2 use, so RBAC is the same.
Tool set, behaviour hints and the response-size limit follow HyperDX api/src/mcp/tools (MIT).
"""

import json
import logging
import secrets

import jsonschema
import mcp.types as types
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

from telescope.constants import UTC_ZONE
from telescope.fetchers.chart import (
    CHART_AGGS,
    GRANULARITIES,
    QUANTILE_LEVELS,
    QUERY_DISPLAYS,
    fetch_chart,
)
from telescope.fetchers.request import ChartDataRequest, DataRequest
from telescope.query_attribution import attribute
from telescope.serializers.dashboard import SourceChartDataRequestSerializer
from telescope.serializers.source import SourceDataRequestSerializer
from telescope.services.dashboard import DashboardService
from telescope.services.exceptions import SerializerValidationError
from telescope.services.source import SourceService
from telescope_alerts.services import AlertService
from telescope_api2.views import ApiError, fetch, usable_source
from telescope_otel.trace import TraceError, fetch_trace

logger = logging.getLogger("telescope.mcp")

MAX_RESPONSE_CHARS = 50_000
MAX_SEARCH_ROWS = 200

READ_ONLY = types.ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
# Without a tile id every call adds a tile; with one it overwrites that tile.
UPSERT = types.ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
)

source_srv = SourceService()
dashboard_srv = DashboardService()
alert_srv = AlertService()

TOOLS = {}


class ToolError(Exception):
    pass


def tool(name, title, description, properties, required=(), annotations=READ_ONLY):
    schema = {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }

    def register(fn):
        spec = types.Tool(
            name=name,
            title=title,
            description=description,
            inputSchema=schema,
            annotations=annotations,
        )
        TOOLS[name] = (spec, fn)
        return fn

    return register


def listing():
    return [
        spec.model_dump(by_alias=True, exclude_none=True, mode="json")
        for spec, _ in TOOLS.values()
    ]


def dumps(data):
    return json.dumps(data, default=str, separators=(",", ":"))


def limit_size(data):
    """JSON of `data`, dropping items from its biggest list to stay under MAX_RESPONSE_CHARS."""
    text = dumps(data)
    if len(text) <= MAX_RESPONSE_CHARS:
        return text
    if isinstance(data, list):
        data = {"items": data}
    lists = [k for k, v in data.items() if isinstance(v, list) and v]
    if lists:
        key = max(lists, key=lambda k: len(dumps(data[k])))
        items = data[key]
        rest = {k: v for k, v in data.items() if k != key and k != "cursor"}

        def shaped(n):
            note = {"field": key, "returned": n, "total": len(items)}
            note["hint"] = "narrow the query, pick fewer columns or lower limit"
            return dumps({**rest, key: items[:n], "trimmed": note})

        low, high = 0, len(items)
        while low < high:
            mid = (low + high + 1) // 2
            if len(shaped(mid)) <= MAX_RESPONSE_CHARS:
                low = mid
            else:
                high = mid - 1
        if low:
            return shaped(low)
    return dumps(
        {
            "trimmed": True,
            "error": f"the response is {len(text)} characters, over the "
            f"{MAX_RESPONSE_CHARS} limit; narrow the query or pick fewer columns",
        }
    )


def error_text(err):
    if isinstance(err, jsonschema.ValidationError):
        where = "/".join(str(p) for p in err.absolute_path)
        return f"invalid arguments{' at ' + where if where else ''}: {err.message}"
    if isinstance(err, SerializerValidationError):
        return "validation failed: " + dumps(
            getattr(err.serializer, "errors", err.serializer)
        )
    if isinstance(err, ApiError):
        return "; ".join(err.body.get("errors") or [dumps(err.body)])
    if isinstance(err, ObjectDoesNotExist):
        return str(err) or "not found"
    if isinstance(err, PermissionDenied):
        return str(err) or "Insufficient permissions"
    return str(err)


def call(user, name, arguments):
    """The tools/call result, or None for an unknown tool."""
    if not isinstance(name, str) or name not in TOOLS:
        return None
    spec, fn = TOOLS[name]
    try:
        jsonschema.validate(arguments, spec.inputSchema)
        with attribute(
            surface="mcp",
            source=arguments.get("source"),
            dashboard=arguments.get("dashboard"),
        ):
            text, is_error = limit_size(fn(user, arguments)), False
    except (
        jsonschema.ValidationError,
        SerializerValidationError,
        ApiError,
        ToolError,
        TraceError,
        ObjectDoesNotExist,
        PermissionDenied,
        ValueError,
    ) as err:
        text, is_error = error_text(err), True
    except Exception as err:
        logger.exception("mcp tool %s failed", name)
        text, is_error = f"{name} failed: {err}", True
    result = types.CallToolResult(
        content=[types.TextContent(type="text", text=text)], isError=is_error
    )
    return result.model_dump(by_alias=True, exclude_none=True, mode="json")


def validated(serializer_cls, user, source, data):
    serializer = serializer_cls(data=data, context={"source": source, "user": user})
    if not serializer.is_valid():
        raise SerializerValidationError(serializer)
    return serializer.validated_data


SOURCE = {"type": "string", "description": "Source slug, from list_sources."}
TIME = {
    "type": ["string", "integer"],
    "description": "Epoch milliseconds, or now / now-<n><s|m|h|d>.",
}
QUERY = {
    "type": "string",
    "description": "FlyQL filter: =, !=, ~ and !~ (regex), <, >, in, has, like, ilike, "
    "and/or/not and parentheses; map and JSON keys as Attrs.'http.route'. "
    "Example: ServiceName = 'payment' and SeverityText = 'ERROR'.",
}
RAW_QUERY = {
    "type": "string",
    "description": "A ClickHouse SQL WHERE fragment; needs the raw query permission.",
}


@tool(
    "list_sources",
    "List sources",
    "Lists the sources you can read: slug, kind, OTel signal and your permissions. "
    "search, chart and get_trace need the 'use' permission.",
    {},
)
def list_sources(user, args):
    return [
        {
            "slug": s["slug"],
            "name": s["name"],
            "kind": s["kind"],
            "description": s["description"],
            "otel_signal": (s["data"].get("otel") or {}).get("signal"),
            "permissions": s["permissions"],
        }
        for s in source_srv.list(user)
    ]


@tool(
    "describe_source",
    "Describe a source",
    "Columns with their types, the time and severity columns, default columns, "
    "OTel column roles and linked sources. Call it before search or chart.",
    {"source": SOURCE},
    required=["source"],
)
def describe_source(user, args):
    s = source_srv.get(user, args["source"])
    keys = [
        "slug",
        "name",
        "kind",
        "description",
        "time_column",
        "date_column",
        "severity_column",
        "uniq_column",
        "default_chosen_columns",
        "context_columns",
        "support_raw_query",
        "permissions",
    ]
    out = {k: s[k] for k in keys}
    out["columns"] = {
        name: {"type": c.get("type"), "group_by": c.get("group_by", False)}
        for name, c in (s["columns"] or {}).items()
    }
    data = s["data"] or {}
    out.update({k: data[k] for k in ("database", "table") if k in data})
    out["otel"] = data.get("otel")
    return out


def default_columns(source):
    # Sources saved by the UI keep a list; older fixtures a comma-separated string.
    value = source.default_chosen_columns
    return value if isinstance(value, str) else ", ".join(value)


@tool(
    "search",
    "Search rows",
    "Returns individual rows (newest first) matching a FlyQL query, as /api/v1/sources/<slug>/search. "
    "Pass the returned cursor as `before` for the next, older page. "
    "For counts or aggregates use chart instead.",
    {
        "source": SOURCE,
        "query": QUERY,
        "raw_query": RAW_QUERY,
        "text": {"type": "string", "description": "Bare text searched in the body."},
        "columns": {
            "type": "string",
            "description": "Comma-separated columns; the source's defaults if empty.",
        },
        "from": {**TIME, "default": "now-1h"},
        "to": {**TIME, "default": "now"},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_SEARCH_ROWS,
            "default": 50,
        },
        "before": {"type": "object", "description": "The cursor of a previous page."},
        "context_columns": {"type": "object"},
    },
    required=["source"],
)
def search(user, args):
    source = usable_source(user, args["source"])
    body = {
        "columns": args.get("columns") or default_columns(source),
        "query": args.get("query", ""),
        "raw_query": args.get("raw_query", ""),
        "text": args.get("text", ""),
        "from": str(args.get("from", "now-1h")),
        "to": str(args.get("to", "now")),
        "limit": args.get("limit", 50),
        "before": args.get("before"),
        "context_columns": args.get("context_columns") or {},
    }
    v = validated(SourceDataRequestSerializer, user, source, body)
    request = DataRequest(
        source=source,
        query=v.get("query", ""),
        raw_query=v.get("raw_query", ""),
        time_from=v["from"],
        time_to=v["to"],
        limit=v["limit"],
        context_columns=v.get("context_columns") or {},
        before=v.get("before"),
        text=v.get("text") or "",
    )
    response = fetch(lambda f: f.fetch_data(request, tz=UTC_ZONE), source)
    if response.error:
        raise ToolError(response.error)
    return {
        "columns": [f.as_dict() for f in v["columns"]],
        "rows": [row.as_dict() for row in response.rows],
        "cursor": response.cursor,
        "from": v["from"],
        "to": v["to"],
    }


@tool(
    "chart",
    "Chart a source",
    "Aggregates rows over time (line, stacked_area, stacked_bar), into one number, "
    "or per group (table, bar, pie), as /api/v1/sources/<slug>/chart. "
    f"Series aggs: {', '.join(CHART_AGGS)}; every agg but count takes a column; "
    f"quantile takes a level in {QUANTILE_LEVELS}.",
    {
        "source": SOURCE,
        "display": {"type": "string", "enum": QUERY_DISPLAYS, "default": "line"},
        "series": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "object"},
            "description": 'E.g. [{"agg": "count"}, {"agg": "quantile", "column": '
            '"Duration", "level": 0.95, "where": "ServiceName = \'cart\'"}].',
            "default": [{"agg": "count"}],
        },
        "query": QUERY,
        "raw_query": RAW_QUERY,
        "group_by": {
            "type": "string",
            "description": "Comma-separated columns, at most 3.",
        },
        "granularity": {"type": "string", "enum": GRANULARITIES, "default": "auto"},
        "limit": {"type": "integer", "description": "Top N groups.", "default": 10},
        "from": {**TIME, "default": "now-1h"},
        "to": {**TIME, "default": "now"},
        "params": {"type": "object", "description": "Values for $name placeholders."},
        "compare": {"type": "boolean", "description": "Add the previous period."},
    },
    required=["source"],
)
def chart(user, args):
    source = usable_source(user, args["source"])
    body = {
        "query": args.get("query", ""),
        "raw_query": args.get("raw_query", ""),
        "from": str(args.get("from", "now-1h")),
        "to": str(args.get("to", "now")),
        "display": args.get("display", "line"),
        "series": args.get("series") or [{"agg": "count"}],
        "group_by": args.get("group_by", ""),
        "granularity": args.get("granularity", "auto"),
        "limit": args.get("limit", 10),
        "params": args.get("params") or {},
        "compare": args.get("compare", False),
    }
    v = validated(SourceChartDataRequestSerializer, user, source, body)
    request = ChartDataRequest(
        source=source,
        query=v.get("query") or "",
        raw_query=v.get("raw_query") or "",
        time_from=v["from"],
        time_to=v["to"],
        context_columns={},
        display=v["display"],
        series=v["series"],
        group_by=v["group_by"],
        granularity=v["granularity"],
        limit=v["limit"],
    )
    return fetch(
        lambda f: fetch_chart(f, request, compare=v["compare"], sparkline=False),
        source,
    ).as_dict()


@tool(
    "get_trace",
    "Get a trace",
    "All spans of one trace from an OTel traces source, as a tree in start order, "
    "with services, errors and durations in nanoseconds. "
    "Each span's resource is an index into `resources`.",
    {
        "source": SOURCE,
        "trace_id": {"type": "string", "pattern": r"^[A-Za-z0-9_\-]{1,128}$"},
        "around_ms": {
            "type": "integer",
            "description": "A time near the trace, to narrow the lookup window.",
        },
    },
    required=["source", "trace_id"],
)
def get_trace(user, args):
    source = usable_source(user, args["source"])
    trace = fetch_trace(source, args["trace_id"], args.get("around_ms"))
    # Spans of one service repeat its resource; send each distinct one once.
    resources = []
    for span in trace.get("spans", []):
        span.pop("_key", None)
        resource = span.pop("resource", {})
        if resource not in resources:
            resources.append(resource)
        span["resource"] = resources.index(resource)
    if resources:
        trace["resources"] = resources
    return trace


@tool(
    "list_dashboards",
    "List dashboards",
    "Dashboards you can read: slug, name, tile count, owner and your permissions.",
    {},
)
def list_dashboards(user, args):
    return dashboard_srv.list(user)


@tool(
    "get_dashboard",
    "Get a dashboard",
    "A dashboard with its time range, filter, variables, sections and tiles. "
    "Tiles on sources you cannot use show as text unless you can edit the dashboard.",
    {"dashboard": {"type": "string", "description": "Dashboard slug."}},
    required=["dashboard"],
)
def get_dashboard(user, args):
    return dashboard_srv.get(user, args["dashboard"])


@tool(
    "upsert_tile",
    "Add or replace a dashboard tile",
    "Adds a tile, or replaces the fields given of the tile with the same id. "
    "chart is a chart definition as in get_dashboard: source, display, series, "
    "query, group_by, granularity, limit; or {display: text, text}. "
    "A new tile goes below the others, 12 of 24 columns wide. Needs edit rights.",
    {
        "dashboard": {"type": "string", "description": "Dashboard slug."},
        "tile": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "pattern": r"^[A-Za-z0-9_-]{1,32}$"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "section": {"type": "string"},
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "w": {"type": "integer"},
                "h": {"type": "integer"},
                "chart": {"type": "object"},
            },
            "additionalProperties": False,
        },
    },
    required=["dashboard", "tile"],
    annotations=UPSERT,
)
def upsert_tile(user, args):
    slug, tile = args["dashboard"], dict(args["tile"])
    current = dashboard_srv.get(user, slug)
    tiles = current["data"]["tiles"]
    index = next((i for i, t in enumerate(tiles) if t["id"] == tile.get("id")), None)
    if index is not None:
        tiles[index] = {**tiles[index], **tile}
    elif "chart" not in tile:
        raise ToolError("a new tile needs a chart")
    else:
        tile.setdefault("id", secrets.token_hex(4))
        tile = {"x": 0, "w": 12, "h": 6, **tile}
        tile.setdefault("y", max((t["y"] + t["h"] for t in tiles), default=0))
        tiles.append(tile)
    saved = dashboard_srv.update(
        user,
        slug,
        {
            "name": current["name"],
            "description": current["description"],
            "shared": current["shared"],
            "data": current["data"],
            "version": current["version"],
        },
    )
    tile_id = tiles[index]["id"] if index is not None else tile["id"]
    return {
        "dashboard": slug,
        "version": saved["version"],
        "created": index is None,
        "tile": next(t for t in saved["data"]["tiles"] if t["id"] == tile_id),
    }


@tool(
    "list_alerts",
    "List alerts",
    "Alerts on sources you can use: name, kind, query or tile, threshold, interval, "
    "state, channels and whether you can edit them.",
    {
        "dashboard": {
            "type": "string",
            "description": "Only the tile alerts of this dashboard slug.",
        }
    },
)
def list_alerts(user, args):
    return alert_srv.list(user, {"dashboard": args.get("dashboard")})
