import json
import math
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
    SOURCE_KIND_CLICKHOUSE,
    SOURCE_KIND_DOCKER,
    SOURCE_KIND_KUBERNETES,
)
from telescope.fetchers.chart import (
    CHART_AGGS,
    GRANULARITIES,
    GROUPED_DISPLAYS,
    HEATMAP_DISPLAY,
    MAX_GROUP_BY,
    QUANTILE_LEVELS,
    QUERY_DISPLAYS,
    SINGLE_SERIES_DISPLAYS,
    TABLE_DISPLAYS,
    TIMESERIES_DISPLAYS,
    VARIABLE_NAME_RE,
    FormulaError,
    VariableError,
    bind_query,
    chart_range_error,
    formula_names,
    is_numeric_column_type,
    parse_formula,
)
from telescope.models import Dashboard, Source
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.serializers.source import (
    SerializeErrorMsg,
    UserSerializer,
    SourceDataRequestSerializer,
)
from telescope.utils import parse_time
from telescope_otel.metrics_sql import (
    ALL_METRIC_AGGS,
    METRIC_AGGS,
    METRIC_TYPES,
    metric_tables,
)

rbac_manager = RBACManager()

DASHBOARD_REFRESH = ["off", "30s", "1m", "5m"]
NUMBER_UNITS = [
    "number",
    "bytes",
    "duration_ms",
    "percent",
    "duration_ns",
    "duration_us",
    "duration_s",
    "bytes_si",
]
DEFAULT_CHART_LIMIT = 10
DASHBOARD_DATA_VERSION = 3
DASHBOARD_MAX_SECTIONS = 20
CHART_MAX_COLOR_RULES = 10
COLOR_RULE_OPS = ["gt", "gte", "lt", "lte", "eq"]
COLOR_RE = r"^#[0-9a-fA-F]{6}$"
ID_RE = r"^[A-Za-z0-9_-]{1,32}$"
COUNT_ONLY_KINDS = (SOURCE_KIND_DOCKER, SOURCE_KIND_KUBERNETES)
VARIABLE_TYPES = ["values", "static", "text"]
DASHBOARD_MAX_VARIABLES = 20
VARIABLE_MAX_OPTIONS = 1000
VARIABLE_MAX_VALUES = 100
VARIABLE_MAX_VALUE_LENGTH = 1000


def upgrade_dashboard_data(data):
    """Returns `data` at DASHBOARD_DATA_VERSION; v1 had no variables, v2 no sections."""
    if isinstance(data, dict) and data.get("version", 1) == 1:
        data = {**data, "version": 2}
        data.setdefault("variables", [])
    if isinstance(data, dict) and data.get("version") == 2:
        data = {**data, "version": 3}
        data.setdefault("sections", [])
    return data


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


def metric_series_error(source: Source, series: List[dict], item: dict):
    """Metric series need a metrics source, and a chart cannot mix them with column series."""
    tables = metric_tables(source)
    if item["agg"] == "metric":
        kind = item["metric"]["type"]
        if not tables:
            return {"metric": ["source is not an OTel metrics source"]}
        if kind not in tables:
            return {"metric": {"type": [f"source has no {kind} metric table"]}}
    elif item["agg"] != "formula" and any(s["agg"] == "metric" for s in series):
        return {"agg": ["a metric chart takes only metric series and formulas"]}
    return None


def chart_series_errors(source: Source, series: List[dict]) -> dict:
    errors = {}
    names = formula_names(series)
    aliases = [s.get("alias") for s in series if s.get("alias")]
    for i, item in enumerate(series):
        agg, column = item["agg"], item.get("column")
        metric_error = metric_series_error(source, series, item)
        if metric_error:
            errors[i] = metric_error
        elif agg == "heatmap" and source.kind != SOURCE_KIND_CLICKHOUSE:
            errors[i] = {
                "agg": [f"heatmaps are not supported for {source.kind} sources"]
            }
        elif source.kind in COUNT_ONLY_KINDS and agg != "count":
            errors[i] = {
                "agg": [f"aggregation {agg} is not supported for {source.kind} sources"]
            }
        elif source.kind in COUNT_ONLY_KINDS and item.get("where"):
            errors[i] = {
                "where": [f"series filters are not supported for {source.kind} sources"]
            }
        elif item.get("alias") and aliases.count(item["alias"]) > 1:
            errors[i] = {"alias": [f"duplicate alias {item['alias']}"]}
        elif agg == "formula":
            try:
                parse_formula(item["formula"], names)
            except FormulaError as err:
                errors[i] = {"formula": [str(err)]}
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
    limit = 1 if source.kind in COUNT_ONLY_KINDS else MAX_GROUP_BY
    if len(result) > limit:
        if limit == 1:
            raise serializers.ValidationError("at most 1 group by column is supported")
        raise serializers.ValidationError(
            f"at most {limit} group by columns are supported"
        )
    return result


def chart_shape_errors(attrs: dict) -> dict:
    errors = {}
    display = attrs["display"]
    series = attrs["series"]
    visible = [s for s in series if not s.get("hidden")]
    if display == HEATMAP_DISPLAY:
        return heatmap_shape_errors(attrs)
    if any(s["agg"] == "heatmap" for s in series):
        return {"series": ["a heatmap series only draws a heatmap tile"]}
    if display in SINGLE_SERIES_DISPLAYS and len(series) > 1 and len(visible) != 1:
        errors["series"] = [f"{display} needs exactly 1 series shown"]
    elif not visible:
        errors["series"] = ["at least 1 series must be shown"]
    if all(s["agg"] == "formula" for s in series):
        errors["series"] = ["a formula needs at least one query series"]
    if display == "number" and attrs.get("group_by"):
        errors["group_by"] = ["number does not support group by"]
    if display in GROUPED_DISPLAYS and not attrs.get("group_by"):
        errors["group_by"] = [f"{display} needs a group by column"]
    if attrs.get("compare") and display not in TIMESERIES_DISPLAYS + ["number"]:
        errors["compare"] = [
            "only time series and number compare to the previous period"
        ]
    if attrs.get("sparkline") and display != "number":
        errors["sparkline"] = ["only number tiles have a sparkline"]
    max_limit = (
        CHART_MAX_TABLE_LIMIT if display in TABLE_DISPLAYS else CHART_MAX_TS_LIMIT
    )
    if not 1 <= attrs.get("limit", DEFAULT_CHART_LIMIT) <= max_limit:
        errors["limit"] = [f"must be between 1 and {max_limit}"]
    return errors


def heatmap_shape_errors(attrs: dict) -> dict:
    """A heatmap draws exactly one heatmap series: the numeric column on its y axis."""
    errors = {}
    series = attrs["series"]
    if len(series) != 1 or series[0]["agg"] != "heatmap" or series[0].get("hidden"):
        errors["series"] = ["heatmap needs exactly 1 shown heatmap series"]
    if attrs.get("group_by"):
        errors["group_by"] = ["heatmap does not support group by"]
    for key in ("compare", "sparkline"):
        if attrs.get(key):
            errors[key] = [f"heatmap does not support {key}"]
    return errors


class MetricSeriesSerializer(StrictSerializer):
    name = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(choices=METRIC_TYPES)
    agg = serializers.ChoiceField(choices=ALL_METRIC_AGGS)
    attrs_filter = serializers.CharField(
        required=False, allow_blank=True, max_length=10000
    )

    def validate(self, attrs):
        if attrs["agg"] not in METRIC_AGGS[attrs["type"]]:
            raise serializers.ValidationError(
                {
                    "agg": [
                        f"a {attrs['type']} metric takes "
                        + ", ".join(METRIC_AGGS[attrs["type"]])
                    ]
                }
            )
        return attrs


class ChartSeriesSerializer(StrictSerializer):
    agg = serializers.ChoiceField(choices=CHART_AGGS)
    metric = MetricSeriesSerializer(required=False)
    column = serializers.CharField(required=False)
    level = serializers.FloatField(required=False)
    alias = serializers.CharField(required=False, allow_blank=True, max_length=64)
    where = serializers.CharField(required=False, allow_blank=True, max_length=10000)
    formula = serializers.CharField(required=False, max_length=1024)
    color = serializers.RegexField(COLOR_RE, required=False)
    hidden = serializers.BooleanField(required=False)

    def validate(self, attrs):
        errors = {}
        agg = attrs["agg"]
        if agg == "metric":
            if "metric" not in attrs:
                errors["metric"] = ["This field is required."]
            if attrs.get("where"):
                errors["where"] = ["filter a metric series with metric.attrs_filter"]
        elif "metric" in attrs:
            errors["metric"] = ["metric is only allowed for agg metric"]
        if agg in ("count", "formula", "metric"):
            if "column" in attrs:
                errors["column"] = [f"{agg} does not take a column"]
        elif "column" not in attrs:
            errors["column"] = ["This field is required."]
        if agg == "quantile":
            if attrs.get("level") not in QUANTILE_LEVELS:
                errors["level"] = [
                    "must be one of " + ", ".join(str(x) for x in QUANTILE_LEVELS)
                ]
        elif "level" in attrs:
            errors["level"] = ["level is only allowed for quantile"]
        if agg == "formula":
            if "formula" not in attrs:
                errors["formula"] = ["This field is required."]
            if attrs.get("where"):
                errors["where"] = ["a formula takes the filters of its series"]
        elif "formula" in attrs:
            errors["formula"] = ["formula is only allowed for agg formula"]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class TileSeriesSerializer(ChartSeriesSerializer):
    """A chart series, which may also be the one series of a heatmap; alerts keep ChartSeriesSerializer."""

    agg = serializers.ChoiceField(choices=CHART_AGGS + ["heatmap"])


class NumberFormatSerializer(StrictSerializer):
    unit = serializers.ChoiceField(choices=NUMBER_UNITS)
    decimals = serializers.IntegerField(min_value=0, max_value=6)
    # Spaces are kept, so " req/s" stays apart from the number.
    prefix = serializers.CharField(
        required=False, allow_blank=True, max_length=16, trim_whitespace=False
    )
    suffix = serializers.CharField(
        required=False, allow_blank=True, max_length=16, trim_whitespace=False
    )
    compact = serializers.BooleanField(required=False)


class ColorRuleSerializer(StrictSerializer):
    op = serializers.ChoiceField(choices=COLOR_RULE_OPS)
    value = serializers.FloatField()
    color = serializers.RegexField(COLOR_RE)


class TextChartSerializer(StrictSerializer):
    display = serializers.ChoiceField(choices=["text"])
    text = serializers.CharField(max_length=10000, allow_blank=True)


class QueryChartSerializer(StrictSerializer):
    source = serializers.CharField(max_length=64)
    display = serializers.ChoiceField(choices=QUERY_DISPLAYS)
    series = serializers.ListField(
        child=TileSeriesSerializer(), min_length=1, max_length=CHART_MAX_SERIES
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
    compare = serializers.BooleanField(required=False)
    sparkline = serializers.BooleanField(required=False)
    color_rules = serializers.ListField(
        child=ColorRuleSerializer(), required=False, max_length=CHART_MAX_COLOR_RULES
    )

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


class VariableDefaultField(serializers.Field):
    """A string, or a list of strings for a multi-value variable."""

    def to_internal_value(self, data):
        items = data if isinstance(data, list) else [data]
        if len(items) > VARIABLE_MAX_VALUES:
            raise serializers.ValidationError(
                f"at most {VARIABLE_MAX_VALUES} values are allowed"
            )
        for item in items:
            if not isinstance(item, str) or len(item) > VARIABLE_MAX_VALUE_LENGTH:
                raise serializers.ValidationError(
                    f"must be strings of at most {VARIABLE_MAX_VALUE_LENGTH} characters"
                )
        return data

    def to_representation(self, value):
        return value


class DashboardVariableSerializer(StrictSerializer):
    name = serializers.RegexField(VARIABLE_NAME_RE)
    label = serializers.CharField(required=False, allow_blank=True, max_length=128)
    type = serializers.ChoiceField(choices=VARIABLE_TYPES)
    source = serializers.CharField(required=False, max_length=64)
    column = serializers.CharField(required=False, max_length=255)
    options = serializers.ListField(
        child=serializers.CharField(max_length=VARIABLE_MAX_VALUE_LENGTH),
        required=False,
        max_length=VARIABLE_MAX_OPTIONS,
    )
    multi = serializers.BooleanField(required=False, default=False)
    required = serializers.BooleanField(required=False, default=False)
    default = VariableDefaultField(required=False, allow_null=True)

    def validate(self, attrs):
        errors = {}
        kind = attrs["type"]
        for key in ("source", "column"):
            if kind == "values" and key not in attrs:
                errors[key] = ["This field is required."]
            elif kind != "values" and key in attrs:
                errors[key] = ["only allowed for type values"]
        if kind == "static" and not attrs.get("options"):
            errors["options"] = ["a static variable needs at least 1 option"]
        elif kind != "static" and "options" in attrs:
            errors["options"] = ["only allowed for type static"]
        if kind == "text" and attrs["multi"]:
            errors["multi"] = ["a text variable takes one value"]
        default = attrs.get("default")
        if isinstance(default, list) and not attrs["multi"]:
            errors["default"] = ["a single-value variable takes one default"]
        elif kind == "static" and default:
            unknown = [
                v
                for v in (default if isinstance(default, list) else [default])
                if v not in attrs.get("options", [])
            ]
            if unknown:
                errors["default"] = [f"{unknown[0]} is not one of the options"]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class DashboardSectionSerializer(StrictSerializer):
    id = serializers.RegexField(ID_RE)
    title = serializers.CharField(allow_blank=True, max_length=128)
    collapsed = serializers.BooleanField(required=False, default=False)


class DashboardTileSerializer(StrictSerializer):
    id = serializers.RegexField(ID_RE)
    x = serializers.IntegerField(min_value=0, max_value=23)
    y = serializers.IntegerField(min_value=0, max_value=10000)
    w = serializers.IntegerField(min_value=1, max_value=24)
    h = serializers.IntegerField(min_value=1, max_value=48)
    title = serializers.CharField(required=False, allow_blank=True, max_length=128)
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=1024
    )
    section = serializers.RegexField(ID_RE, required=False)
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
    """Context: `user` saving it, `old_sources`, the slugs already stored, and
    `old_raw_queries`, the stored (tile id, source, raw_query) triples."""

    version = serializers.ChoiceField(choices=[DASHBOARD_DATA_VERSION])
    time = DashboardTimeSerializer()
    query = serializers.CharField(allow_blank=True, max_length=10000)
    refresh = serializers.ChoiceField(choices=DASHBOARD_REFRESH)
    variables = serializers.ListField(
        child=DashboardVariableSerializer(), max_length=DASHBOARD_MAX_VARIABLES
    )
    sections = serializers.ListField(
        child=DashboardSectionSerializer(), max_length=DASHBOARD_MAX_SECTIONS
    )
    tiles = serializers.ListField(
        child=DashboardTileSerializer(), max_length=DASHBOARD_MAX_TILES
    )

    def to_internal_value(self, data):
        data = upgrade_dashboard_data(data)
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

    def _raw_query_error(self, tile, source):
        chart = tile["chart"]
        old = self.context.get("old_raw_queries", set())
        if not chart["raw_query"] or (
            (tile["id"], chart["source"], chart["raw_query"]) in old
        ):
            return None
        if source is None:
            return SerializeErrorMsg.RAW_QUERIES_PERMISSIONS
        if not source.support_raw_query:
            return SerializeErrorMsg.RAW_QUERIES_NOT_SUPPORTED
        if not rbac_manager.user_has_source_permissions(
            self.context["user"],
            source_slug=source.slug,
            required_permissions=[permissions.Source.RAW_QUERY.value],
        ):
            return SerializeErrorMsg.RAW_QUERIES_PERMISSIONS
        return None

    def validate(self, attrs):
        sections = set()
        for section in attrs["sections"]:
            if section["id"] in sections:
                raise serializers.ValidationError(
                    {"sections": [f"duplicate section id {section['id']}"]}
                )
            sections.add(section["id"])
        seen = set()
        for tile in attrs["tiles"]:
            if tile["id"] in seen:
                raise serializers.ValidationError(
                    {"tiles": [f"duplicate tile id {tile['id']}"]}
                )
            seen.add(tile["id"])
            if "section" in tile and tile["section"] not in sections:
                raise serializers.ValidationError(
                    {
                        "tiles": [
                            f"tile {tile['id']} is in unknown section {tile['section']}"
                        ]
                    }
                )

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
            raw_query_error = self._raw_query_error(tile, source)
            if source is None:
                # Tiles already on the dashboard keep a source the saver lost.
                if slug not in old_sources:
                    tile_errors[i] = {"chart": {"source": [f"source {slug} not found"]}}
                elif raw_query_error:
                    tile_errors[i] = {"chart": {"raw_query": [raw_query_error]}}
                continue
            chart_errors = {}
            if raw_query_error:
                chart_errors["raw_query"] = [raw_query_error]
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
        self._validate_variables(attrs["variables"], sources, old_sources)
        return attrs

    def _validate_variables(self, variables, sources, old_sources):
        names = set()
        errors = {}
        for i, variable in enumerate(variables):
            if variable["name"] in names:
                errors[i] = {"name": [f"duplicate variable {variable['name']}"]}
                continue
            names.add(variable["name"])
            if variable["type"] != "values":
                continue
            slug = variable["source"]
            if slug not in sources:
                sources[slug] = self._get_source(slug)
            source = sources[slug]
            if source is None:
                if slug not in old_sources:
                    errors[i] = {"source": [f"source {slug} not found"]}
            elif variable["column"] not in source._columns:
                errors[i] = {"column": [f"source has no column {variable['column']}"]}
        if errors:
            raise serializers.ValidationError({"variables": errors})


def dashboard_raw_queries(data) -> set:
    return {
        (tile.get("id"), tile["chart"].get("source"), tile["chart"].get("raw_query"))
        for tile in (data or {}).get("tiles", [])
        if isinstance(tile.get("chart"), dict) and tile["chart"].get("raw_query")
    }


def dashboard_sources(data) -> set:
    return {
        tile["chart"]["source"]
        for tile in (data or {}).get("tiles", [])
        if isinstance(tile.get("chart"), dict) and tile["chart"].get("source")
    } | {
        variable["source"]
        for variable in (data or {}).get("variables", [])
        if isinstance(variable, dict) and variable.get("source")
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

    def to_representation(self, instance):
        result = super().to_representation(instance)
        if "data" in result:
            result["data"] = upgrade_dashboard_data(result["data"])
        return result


class DashboardListSerializer(DashboardSerializer):
    tiles_count = serializers.SerializerMethodField()

    class Meta(DashboardSerializer.Meta):
        fields = [f for f in DashboardSerializer.Meta.fields if f != "data"] + [
            "tiles_count"
        ]

    def get_tiles_count(self, obj):
        return len((obj.data or {}).get("tiles", []))


class ParamValueField(serializers.Field):
    """A variable value: a string, number or boolean, or a list of them."""

    def to_internal_value(self, data):
        items = data if isinstance(data, list) else [data]
        if len(items) > VARIABLE_MAX_VALUES:
            raise serializers.ValidationError(
                f"at most {VARIABLE_MAX_VALUES} values are allowed"
            )
        for item in items:
            if isinstance(item, float) and not math.isfinite(item):
                raise serializers.ValidationError("must be a finite number")
            if isinstance(item, str) and len(item) > VARIABLE_MAX_VALUE_LENGTH:
                raise serializers.ValidationError(
                    f"must be at most {VARIABLE_MAX_VALUE_LENGTH} characters"
                )
            if item is not None and not isinstance(item, (str, int, float, bool)):
                raise serializers.ValidationError(
                    "must be a string, number, boolean or a list of them"
                )
        return data

    def to_representation(self, value):
        return value


class SourceChartDataRequestSerializer(SourceDataRequestSerializer):
    dashboard_query = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )
    display = serializers.ChoiceField(choices=QUERY_DISPLAYS)
    series = serializers.ListField(
        child=TileSeriesSerializer(), min_length=1, max_length=CHART_MAX_SERIES
    )
    group_by = serializers.CharField(allow_blank=True, required=False, default="")
    granularity = serializers.ChoiceField(
        choices=GRANULARITIES, required=False, default="auto"
    )
    limit = serializers.IntegerField(required=False, default=DEFAULT_CHART_LIMIT)
    params = serializers.DictField(
        child=ParamValueField(), required=False, default=dict
    )
    compare = serializers.BooleanField(required=False, default=False)
    sparkline = serializers.BooleanField(required=False, default=False)

    def __init__(self, *args, **kwargs):
        super(SourceChartDataRequestSerializer, self).__init__(*args, **kwargs)
        self.fields.pop("columns", None)

    # Queries are checked in validate(), once their variables are bound.
    def validate_query(self, value):
        return value or ""

    def validate_dashboard_query(self, value):
        return value or ""

    def _bind_queries(self, attrs) -> dict:
        errors = {}
        for field in ("query", "dashboard_query"):
            try:
                bound = bind_query(attrs.get(field) or "", attrs["params"])
            except VariableError as err:
                errors.setdefault("params", {})[err.name] = [err.message]
                continue
            try:
                attrs[field] = SourceDataRequestSerializer.validate_query(self, bound)
            except serializers.ValidationError as err:
                errors[field] = err.detail
        series_errors = {}
        for i, item in enumerate(attrs.get("series") or []):
            if not item.get("where"):
                continue
            try:
                bound = bind_query(item["where"], attrs["params"])
                item["where"] = SourceDataRequestSerializer.validate_query(self, bound)
            except VariableError as err:
                errors.setdefault("params", {})[err.name] = [err.message]
            except serializers.ValidationError as err:
                series_errors[i] = {"where": err.detail}
        for i, item in enumerate(attrs.get("series") or []):
            metric = item.get("metric") or {}
            if not metric.get("attrs_filter"):
                continue
            try:
                bound = bind_query(metric["attrs_filter"], attrs["params"])
                metric["attrs_filter"] = SourceDataRequestSerializer.validate_query(
                    self, bound
                )
            except VariableError as err:
                errors.setdefault("params", {})[err.name] = [err.message]
            except serializers.ValidationError as err:
                series_errors[i] = {"metric": {"attrs_filter": err.detail}}
        if series_errors:
            errors["series"] = series_errors
        return errors

    def validate_series(self, value):
        errors = chart_series_errors(self.context["source"], value)
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate_group_by(self, value):
        return parse_chart_group_by(self.context["source"], value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        errors = self._bind_queries(attrs)
        errors.update(chart_shape_errors(attrs))
        if attrs["from"] >= attrs["to"]:
            errors["to"] = ["must be after from"]
        elif attrs["display"] in TIMESERIES_DISPLAYS + [HEATMAP_DISPLAY]:
            error = chart_range_error(attrs["from"], attrs["to"], attrs["granularity"])
            if error:
                errors["to"] = [error]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
