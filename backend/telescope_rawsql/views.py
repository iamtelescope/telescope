import logging

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager
from telescope.response import UIResponse
from telescope_rawsql.query import RawSqlError, run_raw_sql
from telescope_rawsql.serializers import (
    NO_ACCESS,
    RawSqlRequestSerializer,
    raw_sql_connection,
    raw_sql_tables,
)

logger = logging.getLogger("telescope.rawsql")
rbac_manager = RBACManager()


class RawSqlConnectionsView(APIView):
    @method_decorator(login_required)
    def get(self, request):
        response = UIResponse()
        response.data = [
            {"id": c.pk, "name": c.name}
            for c in rbac_manager.get_connections(
                request.user,
                required_permissions=[permissions.Connection.RAW_SQL.value],
            )
            if c.kind == "clickhouse"
        ]
        return Response(response.as_dict())


class RawSqlQueryView(APIView):
    @method_decorator(login_required)
    def post(self, request, pk):
        response = UIResponse()
        connection = raw_sql_connection(request.user, pk)
        if connection is None:
            response.mark_failed(NO_ACCESS)
            response.data = {"code": "no_access"}
            return Response(response.as_dict(), status=403)

        serializer = RawSqlRequestSerializer(data=request.data)
        if not serializer.is_valid():
            response.mark_invalid(serializer.errors)
            return Response(response.as_dict())
        data = serializer.validated_data
        try:
            response.data = run_raw_sql(
                connection,
                raw_sql_tables(request.user, connection),
                data["sql"],
                data["from"],
                data["to"],
                data["granularity"],
                data["params"],
            )
        except RawSqlError as err:
            response.mark_invalid({"sql": [str(err)]})
        except Exception as err:
            logger.info("raw SQL failed: %s", err)
            response.mark_failed(str(err))
            response.data = {"code": "query_failed"}
        return Response(response.as_dict())
