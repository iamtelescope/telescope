import json
from typing import List

from flyql import FlyqlError
from rest_framework import serializers

from telescope.columns import ParsedColumn, parse_columns, ColumnsParserError
from telescope.constants import (
    CHART_MAX_SERIES,
    CHART_MAX_TABLE_LIMIT,
    CHART_MAX_TS_LIMIT,
    DASHBOARD_MAX_DATA_BYTES,
    DASHBOARD_MAX_TILES,
    SOURCE_KIND_DOCKER,
    SOURCE_KIND_KUBERNETES,
)
from telescope.fetchers.chart import (
    CHART_AGGS,
    GRANULARITIES,
    QUANTILE_LEVELS,
    QUERY_DISPLAYS,
    TABLE_DISPLAYS,
    TIMESERIES_DISPLAYS,
    chart_range_error,
    is_numeric_column_type,
)
from telescope.models import Dashboard, Source
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.serializers.source import UserSerializer, SourceDataRequestSerializer
from telescope.utils import parse_time

rbac_manager = RBACManager()

DASHBOARD_REFRESH = ["off", "30s", "1m", "5m"]
NUMBER_UNITS = ["number", "bytes", "duration_ms", "percent"]
DEFAULT_CHART_LIMIT = 10


class StrictSerializer(serializers.Serializer):
    """Rejects keys that are not declared fields."""

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise serializers.ValidationError(
                    {key: ["unknown key"] for key in unknown}
                )
        return super().to_internal_value(data)


def chart_series_errors(source: Source, series: List[dict]) -> dict:
    errors = {}
    for i, item in enumerate(series):
        agg, column = item["agg"], item.get("column")
        if (
            source.kind in (SOURCE_KIND_DOCKER, SOURCE_KIND_KUBERNETES)
            and agg != "count"
        ):
            errors[i] = {
                "agg": [f"aggregation {agg} is not supported for {source.kind} sources"]
            }
        elif column is not None and column not in source._columns:
            errors[i] = {"column": [f"source has no column {column}"]}
        elif (
            column is not None
            and agg != "uniq"
            and not is_numeric_column_type(source.kind, source._columns[column].type)
        ):
            errors[i] = {"column": [f"column {column} is not numeric"]}
    return errors


def parse_chart_group_by(source: Source, value: str) -> List[ParsedColumn]:
    if not value:
        return []
    try:
        result = parse_columns(source, value)
    except (ColumnsParserError, FlyqlError) as err:
        raise serializers.ValidationError(getattr(err, "message", str(err)))
    if len(result) > 1:
        raise serializers.ValidationError("at most 1 group by column is supported")
    return result


def chart_shape_errors(attrs: dict) -> dict:
    errors = {}
    display = attrs["display"]
    if display in ("number", "bar") and len(attrs["series"]) != 1:
        errors["series"] = [f"{display} needs exactly 1 series"]
    if display == "number" and attrs.get("group_by"):
        errors["group_by"] = ["number does not support group by"]
    if display == "bar" and not attrs.get("group_by"):
        errors["group_by"] = ["bar needs a group by column"]
    max_limit = (
        CHART_MAX_TABLE_LIMIT if display in TABLE_DISPLAYS else CHART_MAX_TS_LIMIT
    )
    if not 1 <= attrs.get("limit", DEFAULT_CHART_LIMIT) <= max_limit:
        errors["limit"] = [f"must be between 1 and {max_limit}"]
    return errors


class ChartSeriesSerializer(StrictSerializer):
    agg = serializers.ChoiceField(choices=CHART_AGGS)
    column = serializers.CharField(required=False)
    level = serializers.FloatField(required=False)
    alias = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def validate(self, attrs):
        errors = {}
        if attrs["agg"] == "count":
            if "column" in attrs:
                errors["column"] = ["count does not take a column"]
        elif "column" not in attrs:
            errors["column"] = ["This field is required."]
        if attrs["agg"] == "quantile":
            if attrs.get("level") not in QUANTILE_LEVELS:
                errors["level"] = [
                    "must be one of " + ", ".join(str(x) for x in QUANTILE_LEVELS)
                ]
        elif "level" in attrs:
            errors["level"] = ["level is only allowed for quantile"]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class NumberFormatSerializer(StrictSerializer):
    unit = serializers.ChoiceField(choices=NUMBER_UNITS)
    decimals = serializers.IntegerField(min_value=0, max_value=6)


class TextChartSerializer(StrictSerializer):
    display = serializers.ChoiceField(choices=["text"])
    text = serializers.CharField(max_length=10000, allow_blank=True)


class QueryChartSerializer(StrictSerializer):
    source = serializers.CharField(max_length=64)
    display = serializers.ChoiceField(choices=QUERY_DISPLAYS)
    series = serializers.ListField(
        child=ChartSeriesSerializer(), min_length=1, max_length=CHART_MAX_SERIES
    )
    query = serializers.CharField(required=False, allow_blank=True, default="")
    raw_query = serializers.CharField(required=False, allow_blank=True, default="")
    context_columns = serializers.DictField(required=False, default=dict)
    group_by = serializers.CharField(required=False, allow_blank=True, default="")
    granularity = serializers.ChoiceField(
        choices=GRANULARITIES, required=False, default="auto"
    )
    limit = serializers.IntegerField(required=False, default=DEFAULT_CHART_LIMIT)
    number_format = NumberFormatSerializer(required=False)

    def validate(self, attrs):
        errors = chart_shape_errors(attrs)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ChartField(serializers.Field):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected an object")
        if data.get("display") == "text":
            serializer = TextChartSerializer(data=data)
        else:
            serializer = QueryChartSerializer(data=data)
        if not serializer.is_valid():
            raise serializers.ValidationError(serializer.errors)
        return dict(serializer.validated_data)

    def to_representation(self, value):
        return value


class DashboardTileSerializer(StrictSerializer):
    id = serializers.RegexField(r"^[A-Za-z0-9_-]{1,32}$")
    x = serializers.IntegerField(min_value=0, max_value=23)
    y = serializers.IntegerField(min_value=0, max_value=10000)
    w = serializers.IntegerField(min_value=1, max_value=24)
    h = serializers.IntegerField(min_value=1, max_value=48)
    title = serializers.CharField(required=False, allow_blank=True, max_length=128)
    chart = ChartField()

    def validate(self, attrs):
        if attrs["x"] + attrs["w"] > 24:
            raise serializers.ValidationError({"w": ["x + w must be at most 24"]})
        return attrs


class DashboardTimeSerializer(StrictSerializer):
    _from = serializers.CharField()
    to = serializers.CharField()
    time_zone = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = fields.pop("_from")
        return fields

    def validate_from(self, value):
        _, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_to(self, value):
        _, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value


class DashboardDataSerializer(StrictSerializer):
    """Context: `user` saving it and `old_sources`, the slugs already stored."""

    time = DashboardTimeSerializer()
    query = serializers.CharField(allow_blank=True, max_length=10000)
    refresh = serializers.ChoiceField(choices=DASHBOARD_REFRESH)
    tiles = serializers.ListField(
        child=DashboardTileSerializer(), max_length=DASHBOARD_MAX_TILES
    )

    def to_internal_value(self, data):
        size = len(json.dumps(data, separators=(",", ":")).encode())
        if size > DASHBOARD_MAX_DATA_BYTES:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        f"data must be at most {DASHBOARD_MAX_DATA_BYTES} bytes"
                    ]
                }
            )
        return super().to_internal_value(data)

    def _get_source(self, slug: str):
        user = self.context["user"]
        try:
            return rbac_manager.get_source(user, slug, [permissions.Source.USE.value])
        except Source.DoesNotExist:
            return None

    def validate(self, attrs):
        seen = set()
        for tile in attrs["tiles"]:
            if tile["id"] in seen:
                raise serializers.ValidationError(
                    {"tiles": [f"duplicate tile id {tile['id']}"]}
                )
            seen.add(tile["id"])

        old_sources = self.context.get("old_sources", set())
        sources = {}
        tile_errors = {}
        for i, tile in enumerate(attrs["tiles"]):
            chart = tile["chart"]
            if chart["display"] == "text":
                continue
            slug = chart["source"]
            if slug not in sources:
                sources[slug] = self._get_source(slug)
            source = sources[slug]
            if source is None:
                # Tiles already on the dashboard keep a source the saver lost.
                if slug not in old_sources:
                    tile_errors[i] = {"chart": {"source": [f"source {slug} not found"]}}
                continue
            chart_errors = {}
            series_errors = chart_series_errors(source, chart["series"])
            if series_errors:
                chart_errors["series"] = series_errors
            try:
                parse_chart_group_by(source, chart["group_by"])
            except serializers.ValidationError as err:
                chart_errors["group_by"] = err.detail
            if chart_errors:
                tile_errors[i] = {"chart": chart_errors}
        if tile_errors:
            raise serializers.ValidationError({"tiles": tile_errors})
        return attrs


def dashboard_sources(data) -> set:
    return {
        tile["chart"]["source"]
        for tile in (data or {}).get("tiles", [])
        if isinstance(tile.get("chart"), dict) and tile["chart"].get("source")
    }


class NewDashboardSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=4096, allow_blank=True)
    shared = serializers.BooleanField()
    data = DashboardDataSerializer()


class UpdateDashboardSerializer(NewDashboardSerializer):
    """Context also carries `version`, the stored one."""

    version = serializers.IntegerField()

    def validate_version(self, value):
        if value != self.context["version"]:
            raise serializers.ValidationError(
                "Dashboard was changed elsewhere, reload it"
            )
        return value


class DashboardSerializer(serializers.ModelSerializer):
    owner = UserSerializer(allow_null=True)
    updated_by = UserSerializer(allow_null=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Dashboard
        fields = [
            "slug",
            "name",
            "description",
            "shared",
            "data",
            "version",
            "owner",
            "updated_by",
            "created_at",
            "updated_at",
            "permissions",
        ]

    def get_permissions(self, obj):
        return [p.value for p in permissions.Dashboard if p.value in obj.permissions]


class DashboardListSerializer(DashboardSerializer):
    tiles_count = serializers.SerializerMethodField()

    class Meta(DashboardSerializer.Meta):
        fields = [f for f in DashboardSerializer.Meta.fields if f != "data"] + [
            "tiles_count"
        ]

    def get_tiles_count(self, obj):
        return len((obj.data or {}).get("tiles", []))


class SourceChartDataRequestSerializer(SourceDataRequestSerializer):
    dashboard_query = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )
    display = serializers.ChoiceField(choices=QUERY_DISPLAYS)
    series = serializers.ListField(
        child=ChartSeriesSerializer(), min_length=1, max_length=CHART_MAX_SERIES
    )
    group_by = serializers.CharField(allow_blank=True, required=False, default="")
    granularity = serializers.ChoiceField(
        choices=GRANULARITIES, required=False, default="auto"
    )
    limit = serializers.IntegerField(required=False, default=DEFAULT_CHART_LIMIT)

    def __init__(self, *args, **kwargs):
        super(SourceChartDataRequestSerializer, self).__init__(*args, **kwargs)
        self.fields.pop("columns", None)

    def validate_dashboard_query(self, value):
        return self.validate_query(value)

    def validate_series(self, value):
        errors = chart_series_errors(self.context["source"], value)
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate_group_by(self, value):
        return parse_chart_group_by(self.context["source"], value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        errors = chart_shape_errors(attrs)
        if attrs["from"] >= attrs["to"]:
            errors["to"] = ["must be after from"]
        elif attrs["display"] in TIMESERIES_DISPLAYS:
            error = chart_range_error(attrs["from"], attrs["to"], attrs["granularity"])
            if error:
                errors["to"] = [error]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
