import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.models import Source
from telescope.response import UIResponse
from telescope_otel.service_map import fetch_service_map
from telescope_otel.trace import TraceError
from telescope_otel.trace_views import use_source

logger = logging.getLogger("telescope_otel.service_map_views")


class ServiceMapRequestSerializer(serializers.Serializer):
    to = serializers.IntegerField()
    query = serializers.CharField(required=False, allow_blank=True, default="")
    sampling = serializers.IntegerField(min_value=1, max_value=100, default=1)
    trace_id = serializers.RegexField(
        r"^[A-Za-z0-9_\-]{1,128}$", required=False, allow_null=True
    )

    def get_fields(self):
        # "from" is a Python keyword, so it cannot be a class attribute.
        fields = super().get_fields()
        fields["from"] = serializers.IntegerField()
        return fields

    def validate(self, data):
        if data["from"] > data["to"]:
            raise serializers.ValidationError("from must not be after to")
        return data


class ServiceMapView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        try:
            source = use_source(request.user, slug)
        except Source.DoesNotExist:
            response.mark_failed("source not found")
            return Response(response.as_dict())
        serializer = ServiceMapRequestSerializer(data=request.data)
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        data = serializer.validated_data
        try:
            response.data = fetch_service_map(
                source,
                data["from"],
                data["to"],
                data["query"],
                data["sampling"],
                data.get("trace_id"),
            )
        except TraceError as err:
            response.mark_failed(str(err))
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to build the service map: {err}")
        return Response(response.as_dict())
