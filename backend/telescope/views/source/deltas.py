import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.constants import SOURCE_KIND_CLICKHOUSE
from telescope.fetchers.chart import GRANULARITIES, chart_range_error
from telescope.fetchers.chart import is_numeric_column_type
from telescope.fetchers.deltas import (
    DELTAS_DEFAULT_SAMPLE,
    DELTAS_MAX_SAMPLE,
    Selection,
    fetch_deltas,
    fetch_heatmap,
)
from telescope.models import Source
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.response import UIResponse
from telescope.serializers.source import SourceDataRequestSerializer

logger = logging.getLogger("telescope.views.source.deltas")
rbac_manager = RBACManager()


class OutlierSerializer(serializers.Serializer):
    y_min = serializers.FloatField()
    y_max = serializers.FloatField()
    t_min = serializers.IntegerField()
    t_max = serializers.IntegerField()

    def validate(self, attrs):
        if attrs["y_min"] > attrs["y_max"]:
            raise serializers.ValidationError({"y_max": ["must be at least y_min"]})
        if attrs["t_min"] > attrs["t_max"]:
            raise serializers.ValidationError({"t_max": ["must be at least t_min"]})
        return attrs


class HeatmapRequestSerializer(SourceDataRequestSerializer):
    column = serializers.CharField()
    granularity = serializers.ChoiceField(
        choices=GRANULARITIES, required=False, default="auto"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("columns", None)
        self.fields.pop("limit", None)
        self.fields.pop("before", None)

    def validate_column(self, value):
        source = self.context["source"]
        if value not in source._columns:
            raise serializers.ValidationError(f"unknown column: {value}")
        if not is_numeric_column_type(source.kind, source._columns[value].type):
            raise serializers.ValidationError(f"column {value} is not numeric")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs["from"] >= attrs["to"]:
            raise serializers.ValidationError({"to": ["must be after from"]})
        error = chart_range_error(
            attrs["from"], attrs["to"], attrs.get("granularity", "auto")
        )
        if error:
            raise serializers.ValidationError({"to": [error]})
        return attrs


class DeltasRequestSerializer(HeatmapRequestSerializer):
    outlier = OutlierSerializer()
    sample = serializers.IntegerField(
        min_value=1, max_value=DELTAS_MAX_SAMPLE, default=DELTAS_DEFAULT_SAMPLE
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("granularity", None)


class SelectionView(APIView):
    serializer_class = None

    def run(self, selection: Selection, data: dict):
        raise NotImplementedError

    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        try:
            source = rbac_manager.get_source(
                user=request.user,
                source_slug=slug,
                required_permissions=[permissions.Source.USE.value],
                fetch_connection=True,
            )
        except Source.DoesNotExist:
            response.mark_failed("source not found")
            return Response(response.as_dict())
        if source.kind != SOURCE_KIND_CLICKHOUSE:
            response.mark_failed(f"deltas are not supported for {source.kind} sources")
            return Response(response.as_dict())
        serializer = self.serializer_class(
            data=request.data, context={"source": source, "user": request.user}
        )
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        data = serializer.validated_data
        selection = Selection(
            source=source,
            time_from=data["from"],
            time_to=data["to"],
            column=data["column"],
            query=data.get("query") or "",
            raw_query=data.get("raw_query") or "",
            text=data.get("text") or "",
        )
        try:
            response.data = self.run(selection, data)
        except Exception as err:
            logger.exception("%s failed: %s", self.__class__.__name__, err)
            response.mark_failed(str(err))
        return Response(response.as_dict())


class SourceHeatmapView(SelectionView):
    serializer_class = HeatmapRequestSerializer

    def run(self, selection, data):
        return fetch_heatmap(selection, data["granularity"]).as_dict()


class SourceDeltasView(SelectionView):
    serializer_class = DeltasRequestSerializer

    def run(self, selection, data):
        return fetch_deltas(selection, data["outlier"], data["sample"])
