import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.models import Dashboard
from telescope.response import UIResponse
from telescope.services.dashboard import DashboardService, DASHBOARD_NOT_FOUND
from telescope.services.exceptions import SerializerValidationError

logger = logging.getLogger("telescope.views.dashboard")

dashboard_srv = DashboardService()


class DashboardView(APIView):
    @method_decorator(login_required)
    def get(self, request, slug=None):
        response = UIResponse()
        try:
            if slug is None:
                response.data = dashboard_srv.list(user=request.user)
            else:
                response.data = dashboard_srv.get(user=request.user, slug=slug)
        except Dashboard.DoesNotExist:
            response.mark_failed(DASHBOARD_NOT_FOUND)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to get dashboards: {err}")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def post(self, request):
        response = UIResponse()
        try:
            response.data = dashboard_srv.create(user=request.user, data=request.data)
        except SerializerValidationError as err:
            response.mark_invalid(err.serializer.errors)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to create dashboard: {err}")
        else:
            response.add_msg("Dashboard has been created")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def patch(self, request, slug):
        response = UIResponse()
        try:
            response.data = dashboard_srv.update(
                user=request.user, slug=slug, data=request.data
            )
        except SerializerValidationError as err:
            response.mark_invalid(err.serializer.errors)
        except Dashboard.DoesNotExist:
            response.mark_failed(DASHBOARD_NOT_FOUND)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to update dashboard: {err}")
        else:
            response.add_msg("Dashboard has been updated")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def delete(self, request, slug):
        response = UIResponse()
        try:
            dashboard_srv.delete(user=request.user, slug=slug)
        except Dashboard.DoesNotExist:
            response.mark_failed(DASHBOARD_NOT_FOUND)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to delete dashboard: {err}")
        else:
            response.add_msg("Dashboard has been deleted")
        return Response(response.as_dict())
