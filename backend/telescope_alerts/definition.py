"""Turns an alert definition into a validated chart-engine query, as a given user."""

from typing import Dict, List, Optional

from django.contrib.auth.models import User

from telescope.fetchers.request import ChartDataRequest
from telescope.models import Dashboard, Source
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.serializers.dashboard import SourceChartDataRequestSerializer

from telescope_alerts.models import KIND_TILE

rbac_manager = RBACManager()

SOURCE_NOT_FOUND = "source not found"
DASHBOARD_NOT_FOUND = "dashboard not found"
TILE_NOT_FOUND = "tile not found"
GROUP_LIMIT = 100


class AlertDefinitionError(Exception):
    """The alert cannot run: lost access, a missing tile, or a query the chart engine rejects."""

    def __init__(self, message, errors: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or {}


def flatten_errors(errors) -> str:
    if isinstance(errors, dict):
        parts = []
        for key, value in errors.items():
            text = flatten_errors(value)
            parts.append(text if key == "non_field_errors" else f"{key}: {text}")
        return "; ".join(parts)
    if isinstance(errors, (list, tuple)):
        return ", ".join(flatten_errors(e) for e in errors)
    return str(errors)


class AlertQuery:
    """A resolved alert query: the source, its filters and one series."""

    def __init__(self, source, query, raw_query, context_columns, series, group_by):
        self.source = source
        self.query = query
        self.raw_query = raw_query
        self.context_columns = context_columns
        self.series = series
        self.group_by = group_by

    @property
    def grouped(self) -> bool:
        return bool(self.group_by)

    @property
    def group_by_name(self) -> str:
        return self.group_by[0].name if self.group_by else ""

    @property
    def source_query(self) -> str:
        parts = [p for p in [self.query, self.raw_query] if p]
        if len(parts) == 1:
            return parts[0]
        return " AND ".join(f"({p})" for p in parts)

    def request(self, time_from: int, time_to: int, display: str, **kw):
        return ChartDataRequest(
            source=self.source,
            query=self.query,
            raw_query=self.raw_query,
            time_from=time_from,
            time_to=time_to,
            context_columns=self.context_columns,
            display=display,
            series=[self.series],
            group_by=self.group_by,
            granularity=kw.get("granularity", "auto"),
            limit=kw.get("limit", GROUP_LIMIT),
        )


def tile_chart(user: User, dashboard: Optional[Dashboard], tile_id: str) -> Dict:
    if dashboard is None:
        raise AlertDefinitionError(DASHBOARD_NOT_FOUND)
    perms = rbac_manager.calculate_dashboard_permissions(user, dashboard)
    if permissions.Dashboard.READ.value not in perms:
        raise AlertDefinitionError(DASHBOARD_NOT_FOUND)
    for tile in (dashboard.data or {}).get("tiles", []):
        if tile.get("id") == tile_id:
            chart = tile.get("chart") or {}
            if chart.get("display") == "text" or not chart.get("source"):
                raise AlertDefinitionError("tile has no query")
            return chart
    raise AlertDefinitionError(TILE_NOT_FOUND)


def _combine(queries: List[str]) -> str:
    queries = [q for q in queries if q]
    if len(queries) <= 1:
        return queries[0] if queries else ""
    return " and ".join(f"({q})" for q in queries)


def definition_fields(user: User, data: Dict) -> Dict:
    """Search alerts use their own fields; tile alerts read them from the live tile."""
    if data["kind"] != KIND_TILE:
        return {
            "source": data["source"],
            "query": data.get("query") or "",
            "raw_query": data.get("raw_query") or "",
            "context_columns": data.get("context_columns") or {},
            "group_by": data.get("group_by") or "",
            "series": data["series"],
        }
    dashboard = data.get("dashboard")
    chart = tile_chart(user, dashboard, data.get("tile_id") or "")
    index = data.get("series_index") or 0
    series = chart.get("series") or []
    if index >= len(series):
        raise AlertDefinitionError(
            "tile has no such series", {"series_index": ["tile has no such series"]}
        )
    return {
        "source": chart["source"],
        "query": _combine([chart.get("query"), (dashboard.data or {}).get("query")]),
        "raw_query": chart.get("raw_query") or "",
        "context_columns": chart.get("context_columns") or {},
        "group_by": chart.get("group_by") or "",
        "series": series[index],
    }


def resolve(user: User, data: Dict) -> AlertQuery:
    """Re-checks Source.USE (and RAW_QUERY through the chart serializer) for `user`."""
    fields = definition_fields(user, data)
    try:
        source = rbac_manager.get_source(
            user,
            fields["source"],
            required_permissions=[permissions.Source.USE.value],
            fetch_connection=True,
        )
    except Source.DoesNotExist:
        raise AlertDefinitionError(SOURCE_NOT_FOUND, {"source": [SOURCE_NOT_FOUND]})
    display = "table" if fields["group_by"] else "number"
    serializer = SourceChartDataRequestSerializer(
        data={
            "query": fields["query"],
            "raw_query": fields["raw_query"],
            "from": "0",
            "to": "1",
            "context_columns": fields["context_columns"],
            "display": display,
            "series": [fields["series"]],
            "group_by": fields["group_by"],
            "limit": GROUP_LIMIT if fields["group_by"] else 1,
        },
        context={"source": source, "user": user},
    )
    if not serializer.is_valid():
        errors = dict(serializer.errors)
        # The alert has one series, so drop the list index the chart serializer reports.
        series_errors = errors.get("series")
        if isinstance(series_errors, dict) and len(series_errors) == 1:
            errors["series"] = next(iter(series_errors.values()))
        raise AlertDefinitionError(flatten_errors(errors), errors)
    validated = serializer.validated_data
    return AlertQuery(
        source=source,
        query=validated.get("query") or "",
        raw_query=validated.get("raw_query") or "",
        context_columns=validated.get("context_columns") or {},
        series=dict(validated["series"][0]),
        group_by=validated["group_by"],
    )


def alert_data(alert) -> Dict:
    return {
        "kind": alert.kind,
        "source": alert.source_slug,
        "query": alert.query,
        "raw_query": alert.raw_query,
        "context_columns": alert.context_columns,
        "group_by": alert.group_by,
        "series": alert.series,
        "dashboard": alert.dashboard,
        "tile_id": alert.tile_id,
        "series_index": alert.series_index,
    }
