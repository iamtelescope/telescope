"""Release markers: when a service first reports a new service.version, for the services a tile's filters select."""

import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.fetchers.chart import quote_column
from telescope.fetchers.clickhouse import (
    ClickhouseConnect,
    Fetcher,
    _client_query,
    build_time_clause,
)
from telescope.models import Source
from telescope.response import UIResponse
from telescope.serializers.dashboard import SourceChartDataRequestSerializer
from telescope_otel.trace_views import use_source

logger = logging.getLogger("telescope_otel.releases")

MAX_ROWS = 500
MIN_LOOKBACK_MS = 30 * 60_000
LOOKBACK_RATIO = 0.1
QUERY_TIMEOUT_SECONDS = 30


def release_columns(source):
    """(service, version) SQL expressions, or None when the source has no OTel service roles."""
    otel = source.data.get("otel") or {}
    roles = otel.get("roles") or {}
    if source.kind != "clickhouse" or otel.get("signal") not in ("logs", "traces"):
        return None
    if not roles.get("service") or not roles.get("resource_attrs"):
        return None
    service = quote_column(source, roles["service"])
    return (
        service,
        f"{quote_column(source, roles['resource_attrs'])}['service.version']",
    )


def releases_from_rows(rows, window_from):
    """Rows of (service, version, first seen ms) to markers. A service's earliest version was
    already running, so only later versions inside the window count as releases."""
    seen = set()
    result = []
    for service, version, first in sorted(rows, key=lambda r: (r[2], r[0], r[1])):
        if service not in seen:
            seen.add(service)
            continue
        if first >= window_from:
            result.append({"time": first, "service": service, "version": version})
    return result


def scope_where(source, query, series):
    """The tile's filter: its query and, when every series has one, the OR of the series filters."""
    parts = [f"({Fetcher._flyql_sql(source, query)})"]
    wheres = [s.get("where") for s in series if s.get("agg") != "formula"]
    if wheres and all(wheres):
        parts.append(
            "("
            + " OR ".join(f"({Fetcher._flyql_sql(source, w)})" for w in wheres)
            + ")"
        )
    return " AND ".join(parts)


def fetch_releases(source, query, raw_query, series, time_from, time_to):
    columns = release_columns(source)
    if not columns:
        return []
    service, version = columns
    lookback = max(MIN_LOOKBACK_MS, int((time_to - time_from) * LOOKBACK_RATIO))
    time_clause = build_time_clause(
        source.time_column, source.date_column, time_from - lookback, time_to
    )
    time_column = quote_column(source, source.time_column)
    table = f"{source.data['database']}.{source.data['table']}"
    scope = f"{scope_where(source, query, series)} AND ({raw_query or 'true'})"
    # The tile's filters pick the services; a release is dated on all rows of its service.
    sql = (
        f"SELECT toString({service}) AS s, {version} AS v,"
        f" toUnixTimestamp64Milli(toDateTime64(min({time_column}), 3)) AS first_seen"
        f" FROM {table} WHERE {time_clause} AND v != ''"
        f" AND s IN (SELECT DISTINCT toString({service}) FROM {table} WHERE {time_clause} AND {scope})"
        f" GROUP BY s, v ORDER BY first_seen LIMIT {MAX_ROWS}"
    )
    if source.data.get("settings"):
        sql += f" SETTINGS {source.data['settings']}"
    with ClickhouseConnect(source.conn.data) as c:
        rows = _client_query(
            c.client, sql, settings={"max_execution_time": QUERY_TIMEOUT_SECONDS}
        ).result_rows
    return releases_from_rows(rows, time_from)


class ReleasesView(APIView):
    """Takes a tile's chartData body and returns [{time, service, version}]."""

    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        try:
            source = use_source(request.user, slug)
        except Source.DoesNotExist:
            response.mark_failed("source not found")
            return Response(response.as_dict())
        serializer = SourceChartDataRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        data = serializer.validated_data
        queries = [q for q in (data.get("query"), data.get("dashboard_query")) if q]
        query = " and ".join(f"({q})" for q in queries)
        try:
            response.data = fetch_releases(
                source,
                query,
                data.get("raw_query") or "",
                data["series"],
                data["from"],
                data["to"],
            )
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to fetch releases: {err}")
        return Response(response.as_dict())
