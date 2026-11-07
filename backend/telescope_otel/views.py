import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.fetchers.clickhouse import ClickhouseConnect, _client_query
from telescope.models import Connection
from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.response import UIResponse
from telescope_otel.detect import detect

logger = logging.getLogger("telescope_otel.views")
rbac_manager = RBACManager()


class DetectRequestSerializer(serializers.Serializer):
    connection_id = serializers.IntegerField()
    database = serializers.CharField()
    table = serializers.CharField()


def read_table(conn_data, database, table):
    """(columns, sibling table names) of database.table, columns as (name, type)."""
    with ClickhouseConnect(conn_data) as c:
        params = {"database": database, "table": table}
        columns = _client_query(
            c.client,
            "SELECT name, type FROM system.columns"
            " WHERE database = %(database)s AND table = %(table)s ORDER BY position",
            parameters=params,
        ).result_rows
        tables = _client_query(
            c.client,
            "SELECT name FROM system.tables WHERE database = %(database)s",
            parameters=params,
        ).result_rows
    return [(n, t) for n, t in columns], [r[0] for r in tables]


def suggest_links(user, connection_id, database, signal):
    """Readable OTel sources of the other signals on the same connection and database."""
    links = {}
    sources = rbac_manager.get_sources(
        user=user,
        source_filter={"kind": "clickhouse", "conn_id": connection_id},
        required_permissions=[permissions.Source.READ.value],
    )
    for source in sorted(sources, key=lambda s: s.slug):
        other = (source.data or {}).get("otel", {}).get("signal")
        if (
            source.data.get("database") == database
            and other
            and other != signal
            and other not in links
        ):
            links[other] = source.slug
    return links


class DetectView(APIView):
    @method_decorator(login_required)
    def post(self, request):
        response = UIResponse()
        serializer = DetectRequestSerializer(data=request.data)
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        data = serializer.validated_data
        try:
            connection = Connection.objects.get(id=data["connection_id"])
            rbac_manager.require_connection_permissions(
                user=request.user,
                connection_id=connection.id,
                required_permissions=[permissions.Connection.USE.value],
            )
            if connection.kind != "clickhouse":
                response.data = {"otel": None}
                return Response(response.as_dict())
            columns, tables = read_table(
                connection.data, data["database"], data["table"]
            )
            if not columns:
                response.mark_failed(
                    f"table {data['database']}.{data['table']} not found"
                )
                return Response(response.as_dict())
            result = detect(data["table"], columns, tables)
            if result:
                result["otel"]["links"] = suggest_links(
                    request.user,
                    connection.id,
                    data["database"],
                    result["otel"]["signal"],
                )
            response.data = result or {"otel": None}
        except Connection.DoesNotExist:
            response.mark_failed("Connection not found")
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to detect OTel schema: {err}")
        return Response(response.as_dict())
