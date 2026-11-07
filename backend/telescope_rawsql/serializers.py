from rest_framework import serializers

from telescope.fetchers.chart import GRANULARITIES, VARIABLE_NAME_RE
from telescope.models import Connection
from telescope_otel.metrics_sql import metric_tables
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.utils import parse_time
from telescope_rawsql.query import RAW_SQL_DISPLAY, RAW_SQL_MAX_LENGTH

rbac_manager = RBACManager()

NO_ACCESS = "connection not found or no raw SQL access"


def raw_sql_connection(user, pk):
    """The ClickHouse connection `user` may run raw SQL on, or None."""
    try:
        connection = rbac_manager.get_connection(
            user, pk, [permissions.Connection.RAW_SQL.value]
        )
    except Connection.DoesNotExist:
        return None
    return connection if connection.kind == "clickhouse" else None


def raw_sql_tables(user, connection) -> set:
    """The "db.table" names raw SQL may read: the tables of the sources `user` may use on `connection`."""
    tables = {"system.one"}
    for source in rbac_manager.get_sources(
        user,
        source_filter={"conn_id": connection.pk},
        required_permissions=[permissions.Source.USE.value],
    ):
        if source.kind != "clickhouse":
            continue
        database = source.data.get("database")
        names = [source.data.get("table"), *metric_tables(source).values()]
        tables.update(f"{database}.{name}" for name in names if name)
    return tables


class RawSqlChartSerializer(serializers.Serializer):
    display = serializers.ChoiceField(choices=[RAW_SQL_DISPLAY])
    connection = serializers.IntegerField()
    sql = serializers.CharField(max_length=RAW_SQL_MAX_LENGTH)
    granularity = serializers.ChoiceField(
        choices=GRANULARITIES, required=False, default="auto"
    )

    def to_internal_value(self, data):
        unknown = sorted(set(data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError({key: ["unknown key"] for key in unknown})
        return super().to_internal_value(data)


def raw_sql_tile_error(user, tile, old: set):
    """Saving a new or changed raw SQL tile needs RAW_SQL on its connection."""
    chart = tile["chart"]
    if raw_sql_key(tile) in old or raw_sql_connection(user, chart["connection"]):
        return None
    return {"connection": [NO_ACCESS]}


def raw_sql_key(tile):
    chart = tile.get("chart") or {}
    return ("sql", tile.get("id"), chart.get("connection"), chart.get("sql"))


class RawSqlRequestSerializer(serializers.Serializer):
    _from = serializers.CharField()
    to = serializers.CharField()
    sql = serializers.CharField(max_length=RAW_SQL_MAX_LENGTH)
    granularity = serializers.ChoiceField(
        choices=GRANULARITIES, required=False, default="auto"
    )
    params = serializers.DictField(required=False, default=dict)

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = fields.pop("_from")
        return fields

    def validate_from(self, value):
        value, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_to(self, value):
        value, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_params(self, value):
        # Lazy import: telescope.serializers.dashboard imports this module.
        from telescope.serializers.dashboard import ParamValueField

        field = ParamValueField()
        result = {}
        for name, item in value.items():
            if not VARIABLE_NAME_RE.match(name):
                raise serializers.ValidationError({name: ["invalid variable name"]})
            result[name] = field.to_internal_value(item)
        return result

    def validate(self, attrs):
        if attrs["from"] >= attrs["to"]:
            raise serializers.ValidationError({"to": ["must be after from"]})
        return attrs
