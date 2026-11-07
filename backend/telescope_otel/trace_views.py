import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.models import Source
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.response import UIResponse
from telescope_otel.trace import TraceError, fetch_trace, fetch_trace_logs

logger = logging.getLogger("telescope_otel.trace_views")
rbac_manager = RBACManager()


class TraceRequestSerializer(serializers.Serializer):
    trace_id = serializers.RegexField(r"^[A-Za-z0-9_\-]{1,128}$")
    around_ms = serializers.IntegerField(required=False, allow_null=True)


def use_source(user, slug):
    return rbac_manager.get_source(
        user=user,
        source_slug=slug,
        required_permissions=[permissions.Source.USE.value],
        fetch_connection=True,
    )


class BaseTraceView(APIView):
    def run(self, request, source, data):
        raise NotImplementedError

    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        try:
            source = use_source(request.user, slug)
        except Source.DoesNotExist:
            response.mark_failed("source not found")
            return Response(response.as_dict())
        serializer = TraceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        try:
            response.data = self.run(request, source, serializer.validated_data)
        except TraceError as err:
            response.mark_failed(str(err))
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to fetch trace: {err}")
        return Response(response.as_dict())


class TraceView(BaseTraceView):
    def run(self, request, source, data):
        return fetch_trace(source, data["trace_id"], data.get("around_ms"))


class TraceLogsView(BaseTraceView):
    def run(self, request, source, data):
        otel = source.data.get("otel") or {}
        if otel.get("signal") != "traces":
            raise TraceError(f"source {source.slug} is not an OTel traces source")
        slug = (otel.get("links") or {}).get("logs")
        if not slug:
            raise TraceError("no logs source is linked to this traces source")
        try:
            logs = use_source(request.user, slug)
        except Source.DoesNotExist:
            raise TraceError(f"no access to logs source {slug}")
        return fetch_trace_logs(logs, data["trace_id"], data.get("around_ms"))
