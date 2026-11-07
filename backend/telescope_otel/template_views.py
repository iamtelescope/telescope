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
from telescope.services.dashboard import DashboardService
from telescope.services.exceptions import SerializerValidationError
from telescope_otel.provision import (
    TemplateError,
    get_template,
    instantiate,
    load_templates,
    role_candidates,
    template_summary,
)

logger = logging.getLogger("telescope_otel.template_views")
rbac_manager = RBACManager()


class InstantiateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(
        max_length=4096, allow_blank=True, required=False
    )
    shared = serializers.BooleanField(default=False)
    sources = serializers.DictField(child=serializers.CharField(max_length=64))


class TemplateListView(APIView):
    @method_decorator(login_required)
    def get(self, request):
        response = UIResponse()
        response.data = [
            {**template_summary(t), "roles": role_candidates(request.user, t)}
            for t in load_templates().values()
        ]
        return Response(response.as_dict())


class TemplateInstantiateView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        serializer = InstantiateSerializer(data=request.data)
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        body = serializer.validated_data
        try:
            template = get_template(slug)
            sources = {}
            for role, source_slug in body["sources"].items():
                try:
                    sources[role] = rbac_manager.get_source(
                        request.user, source_slug, [permissions.Source.USE.value]
                    )
                except Source.DoesNotExist:
                    raise TemplateError(f"source {source_slug} not found")
            data = instantiate(template, sources)
            response.data = DashboardService().create(
                request.user,
                {
                    "name": body["name"],
                    "description": body.get("description", template["description"]),
                    "shared": body["shared"],
                    "data": data,
                },
            )
        except TemplateError as err:
            response.mark_failed(str(err))
        except SerializerValidationError as err:
            response.mark_invalid(err.serializer.errors)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to create dashboard: {err}")
        else:
            response.add_msg("Dashboard has been created")
        return Response(response.as_dict())
