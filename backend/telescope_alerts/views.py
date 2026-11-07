import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.response import UIResponse
from telescope.services.exceptions import SerializerValidationError
from telescope.utils import parse_time

from telescope_alerts.models import Alert, AlertChannel
from telescope_alerts.services import (
    AlertService,
    ChannelService,
    SavedViewMetaService,
    as_int,
)

logger = logging.getLogger("telescope.alerts")

alert_srv = AlertService()
channel_srv = ChannelService()
view_meta_srv = SavedViewMetaService()


def run(action, what, success=None):
    """Calls `action` and maps the service exceptions onto a UIResponse."""
    response = UIResponse()
    try:
        response.data = action()
    except SerializerValidationError as err:
        response.mark_invalid(err.serializer.errors)
        response.result = False
    except ObjectDoesNotExist as err:
        response.mark_failed(str(err))
    except PermissionDenied as err:
        response.mark_failed(str(err) or "Insufficient permissions")
    except Exception as err:
        logger.exception(err)
        response.mark_failed(f"failed to {what}: {err}")
    else:
        response.add_msg(success)
    if response.data is None:
        response.data = {}
    return Response(response.as_dict())


class AlertView(APIView):
    @method_decorator(login_required)
    def get(self, request, pk=None):
        if pk is None:
            return run(lambda: alert_srv.list(request.user, request.GET), "list alerts")
        return run(lambda: alert_srv.get(request.user, pk), "get alert")

    @method_decorator(login_required)
    def post(self, request):
        return run(
            lambda: alert_srv.create(request.user, request.data),
            "create alert",
            "Alert has been created",
        )

    @method_decorator(login_required)
    def patch(self, request, pk):
        return run(
            lambda: alert_srv.update(request.user, pk, request.data),
            "update alert",
            "Alert has been updated",
        )

    @method_decorator(login_required)
    def delete(self, request, pk):
        return run(
            lambda: alert_srv.delete(request.user, pk),
            "delete alert",
            "Alert has been deleted",
        )


class AlertHistoryView(APIView):
    @method_decorator(login_required)
    def get(self, request, pk):
        time_from, time_to = as_int(request.GET.get("from")), as_int(
            request.GET.get("to")
        )
        return run(
            lambda: alert_srv.history(request.user, pk, time_from, time_to),
            "get alert history",
        )


class AlertEvaluationsView(APIView):
    @method_decorator(login_required)
    def get(self, request, pk):
        limit = as_int(request.GET.get("limit"), 50)
        before = as_int(request.GET.get("before"))
        return run(
            lambda: alert_srv.evaluations(request.user, pk, limit, before),
            "get alert evaluations",
        )


class AlertMarkersView(APIView):
    @method_decorator(login_required)
    def get(self, request):
        return run(
            lambda: alert_srv.markers(request.user, request.GET), "get alert markers"
        )


class AlertSilenceView(APIView):
    @method_decorator(login_required)
    def post(self, request, pk):
        return run(
            lambda: alert_srv.silence(request.user, pk, request.data),
            "silence alert",
            "Alert has been silenced",
        )

    @method_decorator(login_required)
    def delete(self, request, pk):
        return run(
            lambda: alert_srv.unsilence(request.user, pk),
            "unsilence alert",
            "Alert is no longer silenced",
        )


class AlertEnabledView(APIView):
    @method_decorator(login_required)
    def post(self, request, pk):
        enabled = request.data.get("enabled")

        def action():
            if not isinstance(enabled, bool):
                raise ValueError("enabled must be true or false")
            return alert_srv.set_enabled(request.user, pk, enabled)

        return run(
            action,
            "change alert",
            "Alert has been enabled" if enabled else "Alert has been disabled",
        )


class AlertTestView(APIView):
    @method_decorator(login_required)
    def post(self, request, pk):
        return run(
            lambda: alert_srv.test(request.user, pk),
            "send test notification",
            "Test notification has been sent",
        )


class SavedViewMetaView(APIView):
    @method_decorator(login_required)
    def get(self, request, slug):
        return run(
            lambda: view_meta_srv.list(request.user, slug), "get saved view tags"
        )

    @method_decorator(login_required)
    def patch(self, request, slug, view_id):
        return run(
            lambda: view_meta_srv.update(request.user, slug, view_id, request.data),
            "update saved view",
        )


class AlertPreviewView(APIView):
    @method_decorator(login_required)
    def post(self, request):
        data = dict(request.data)
        now = data.pop("now", None)

        def action():
            at_ms = None
            if now not in (None, ""):
                at_ms, error = parse_time(str(now))
                if error:
                    raise ValueError(f"now: {error}")
            return alert_srv.preview(request.user, data, at_ms)

        return run(action, "preview alert")


class ChannelView(APIView):
    @method_decorator(login_required)
    def get(self, request):
        return run(lambda: channel_srv.list(request.user), "list channels")

    @method_decorator(login_required)
    def post(self, request):
        return run(
            lambda: channel_srv.create(request.user, request.data),
            "create channel",
            "Channel has been created",
        )

    @method_decorator(login_required)
    def patch(self, request, pk):
        return run(
            lambda: channel_srv.update(request.user, pk, request.data),
            "update channel",
            "Channel has been updated",
        )

    @method_decorator(login_required)
    def delete(self, request, pk):
        return run(
            lambda: channel_srv.delete(request.user, pk),
            "delete channel",
            "Channel has been deleted",
        )


class ChannelTestView(APIView):
    @method_decorator(login_required)
    def post(self, request, pk):
        return run(
            lambda: channel_srv.test(request.user, pk),
            "send test notification",
            "Test notification has been sent",
        )
