import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.models import Source
from telescope.response import UIResponse
from telescope.utils import parse_time
from telescope_otel.metrics_sql import (
    METRIC_TYPES,
    metric_attributes,
    metric_names,
    metric_tables,
)
from telescope_otel.trace_views import use_source

logger = logging.getLogger("telescope_otel.metrics_views")


class TimeField(serializers.CharField):
    """Milliseconds or a relative time such as now-1h."""

    def to_internal_value(self, data):
        value, error = parse_time(str(data))
        if error:
            raise serializers.ValidationError(error)
        return value


class RangeSerializer(serializers.Serializer):
    _from = TimeField()
    to = TimeField()

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = fields.pop("_from")
        return fields


class AttributesSerializer(RangeSerializer):
    name = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(choices=METRIC_TYPES)
    key = serializers.CharField(max_length=512, required=False)


class BaseMetricsView(APIView):
    serializer_class = RangeSerializer

    def run(self, source, data):
        raise NotImplementedError

    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        try:
            source = use_source(request.user, slug)
        except Source.DoesNotExist:
            response.mark_failed("source not found")
            return Response(response.as_dict())
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        if not metric_tables(source):
            response.mark_failed(f"source {slug} is not an OTel metrics source")
            return Response(response.as_dict())
        try:
            response.data = self.run(source, serializer.validated_data)
        except ValueError as err:
            response.mark_failed(str(err))
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to read metrics: {err}")
        return Response(response.as_dict())


class MetricNamesView(BaseMetricsView):
    def run(self, source, data):
        return {"metrics": metric_names(source, data["from"], data["to"])}


class MetricAttributesView(BaseMetricsView):
    serializer_class = AttributesSerializer

    def run(self, source, data):
        return metric_attributes(
            source, data, data["from"], data["to"], data.get("key")
        )
