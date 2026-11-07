"""External API v2: token-authenticated REST over the same services as /ui/v1.
Resource shapes and pagination follow HyperDX api/src/routers/external-api/v2 (MIT)."""

import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.auth.token import TokenAuth
from telescope.constants import UTC_ZONE
from telescope.fetchers import get_fetchers
from telescope.fetchers.request import ChartDataRequest, DataRequest
from telescope.query_attribution import debug_sql
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.serializers.dashboard import SourceChartDataRequestSerializer
from telescope.serializers.source import SourceDataRequestSerializer
from telescope.services.dashboard import DashboardService
from telescope.services.exceptions import SerializerValidationError
from telescope.services.source import SourceSavedViewService

from telescope_alerts.services import AlertService
from telescope_api2.openapi import SPEC
from telescope_api2.throttle import TokenRateThrottle

logger = logging.getLogger("telescope.api2")

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500

rbac_manager = RBACManager()
dashboard_srv = DashboardService()
alert_srv = AlertService()


class ApiError(Exception):
    def __init__(self, code, body):
        self.code = code
        self.body = body


def error(code, message):
    return Response({"errors": [message]}, status=code)


def paginate(request, items):
    try:
        page = max(int(request.query_params.get("page", 1)), 1)
        size = int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE))
    except ValueError:
        raise ApiError(400, {"errors": ["page and page_size must be integers"]})
    size = min(max(size, 1), MAX_PAGE_SIZE)
    start = (page - 1) * size
    return {
        "data": items[start : start + size],
        "page": page,
        "page_size": size,
        "total": len(items),
        "has_more": start + size < len(items),
    }


class V2View(APIView):
    authentication_classes = [TokenAuth]
    permission_classes = [IsAuthenticated]
    throttle_classes = [TokenRateThrottle]

    def handle_exception(self, exc):
        # Maps the service exceptions /ui/v1 reports in its envelope onto HTTP codes.
        if isinstance(exc, ApiError):
            return Response(exc.body, status=exc.code)
        if isinstance(exc, SerializerValidationError):
            errors = getattr(exc.serializer, "errors", exc.serializer)
            return Response({"validation": errors}, status=400)
        if isinstance(exc, ObjectDoesNotExist):
            return error(404, str(exc) or "Not found")
        if isinstance(exc, PermissionDenied):
            return error(403, str(exc) or "Insufficient permissions")
        if isinstance(exc, ValueError):
            return error(400, str(exc))
        return super().handle_exception(exc)


class DashboardView(V2View):
    def get(self, request, slug=None):
        if slug is None:
            return Response(paginate(request, dashboard_srv.list(request.user)))
        return Response(dashboard_srv.get(request.user, slug))

    def post(self, request):
        data = dashboard_srv.create(request.user, request.data)
        return Response(data, status=201)

    def patch(self, request, slug):
        return Response(dashboard_srv.update(request.user, slug, request.data))

    def delete(self, request, slug):
        dashboard_srv.delete(request.user, slug)
        return Response(status=204)


class AlertView(V2View):
    def get(self, request, pk=None):
        if pk is None:
            return Response(paginate(request, alert_srv.list(request.user)))
        return Response(alert_srv.get(request.user, pk))

    def post(self, request):
        return Response(alert_srv.create(request.user, request.data), status=201)

    def patch(self, request, pk):
        return Response(alert_srv.update(request.user, pk, request.data))

    def delete(self, request, pk):
        alert_srv.delete(request.user, pk)
        return Response(status=204)


class SavedViewView(V2View):
    def get(self, request, source=None, view_slug=None):
        if view_slug is not None:
            return Response(SourceSavedViewService(source).get(request.user, view_slug))
        slugs = (
            [request.query_params["source"]]
            if "source" in request.query_params
            else None
        )
        if slugs is None:
            slugs = sorted(
                s.slug
                for s in rbac_manager.get_sources(
                    request.user, required_permissions=[permissions.Source.READ.value]
                )
            )
        items = []
        for slug in slugs:
            items.extend(SourceSavedViewService(slug).list(request.user))
        return Response(paginate(request, items))

    def post(self, request):
        source = request.data.get("source")
        if not source:
            return Response({"validation": {"source": ["required"]}}, status=400)
        data = SourceSavedViewService(source).create(request.user, source, request.data)
        return Response(data, status=201)

    def patch(self, request, source, view_slug):
        srv = SourceSavedViewService(source)
        return Response(srv.update(request.user, view_slug, request.data))

    def delete(self, request, source, view_slug):
        SourceSavedViewService(source).delete(request.user, view_slug)
        return Response(status=204)


def usable_source(user, slug):
    return rbac_manager.get_source(
        user=user,
        source_slug=slug,
        required_permissions=[permissions.Source.USE.value],
        fetch_connection=True,
    )


def fetch(call, source):
    try:
        return call(get_fetchers()[source.kind])
    except Exception as err:
        logger.exception("api query failed: %s", err)
        raise ApiError(400, {"errors": [str(err)]})


def with_debug(data, user, slug):
    if debug := debug_sql(user, slug):
        data["debug"] = debug
    return data


class SearchView(V2View):
    def post(self, request, slug):
        source = usable_source(request.user, slug)
        serializer = SourceDataRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )
        if not serializer.is_valid():
            return Response({"validation": serializer.errors}, status=400)
        v = serializer.validated_data
        data_request = DataRequest(
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
        response = fetch(lambda f: f.fetch_data(data_request, tz=UTC_ZONE), source)
        if response.error:
            return error(400, response.error)
        data = {
            "columns": [f.as_dict() for f in v["columns"]],
            "rows": [row.as_dict() for row in response.rows],
            "message": response.message,
            # Pass as `before` to get the next (older) page; null on the last one.
            "cursor": response.cursor,
            "from": v["from"],
            "to": v["to"],
        }
        return Response(with_debug(data, request.user, slug))


class ChartView(V2View):
    def post(self, request, slug):
        source = usable_source(request.user, slug)
        serializer = SourceChartDataRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )
        if not serializer.is_valid():
            return Response({"validation": serializer.errors}, status=400)
        v = serializer.validated_data
        queries = [q for q in [v.get("query"), v.get("dashboard_query")] if q]
        query = " and ".join(f"({q})" for q in queries)
        chart_request = ChartDataRequest(
            source=source,
            query=query,
            raw_query=v.get("raw_query") or "",
            time_from=v["from"],
            time_to=v["to"],
            context_columns=v.get("context_columns") or {},
            display=v["display"],
            series=v["series"],
            group_by=v["group_by"],
            granularity=v["granularity"],
            limit=v["limit"],
        )
        data = fetch(lambda f: f.fetch_chart_data(chart_request), source).as_dict()
        return Response(with_debug(data, request.user, slug))


class OpenAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(SPEC)
