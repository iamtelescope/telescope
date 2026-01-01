import logging

from telescope.constants import UTC_ZONE

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group

from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.rbac.manager import RBACManager

from telescope.services.source import SourceService, SourceSavedViewService
from telescope.services.exceptions import SerializerValidationError
from telescope.fetchers import get_fetchers
from telescope.fetchers.request import (
    DataRequest,
    GraphDataRequest,
    DataAndGraphDataRequest,
)
from telescope.rbac import permissions
from telescope.response import UIResponse
from telescope.models import Source, SavedView, Connection
from telescope.serializers.source import (
    SourceRoleSerializer,
    ClickhouseConnectionSerializer,
    DockerConnectionSerializer,
    KubernetesConnectionSerializer,
    SourceDataRequestSerializer,
    SourceGraphDataRequestSerializer,
    SourceDataAndGraphDataRequestSerializer,
    SourceAutocompleteRequestSerializer,
    SourceContextFieldDataSerializer,
    GetSourceSchemaClickhouseSerializer,
    GetSourceSchemaDockerSerializer,
    GetSourceSchemaKubernetesSerializer,
)

logger = logging.getLogger("telescope.views.source")

CONNECTION_KIND_TO_SERIALIZER = {
    "clickhouse": ClickhouseConnectionSerializer,
    "docker": DockerConnectionSerializer,
    "kubernetes": KubernetesConnectionSerializer,
}

SCHEMA_KIND_TO_SERIALIZER = {
    "clickhouse": GetSourceSchemaClickhouseSerializer,
    "docker": GetSourceSchemaDockerSerializer,
    "kubernetes": GetSourceSchemaKubernetesSerializer,
}

source_srv = SourceService()
rbac_manager = RBACManager()


class SourceRoleBindingView(APIView):
    @method_decorator(login_required)
    def get(self, request, slug):
        response = UIResponse()

        try:
            response.data = source_srv.get_role_bindings(user=request.user, slug=slug)
        except Exception as err:
            response.mark_failed(f"failed to get source role bindings: {err}")
        return Response(response.as_dict())


class SourceSavedViewView(APIView):
    @method_decorator(login_required)
    def get(self, request, slug, view_slug=None):
        response = UIResponse()
        saved_view_srv = SourceSavedViewService(slug=slug)

        try:
            if view_slug is None:
                data = saved_view_srv.list(user=request.user)
            else:
                data = saved_view_srv.get(user=request.user, view_slug=view_slug)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to list source saved views: {err}")
        else:
            response.data = data
        return Response(response.as_dict())

    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        saved_view_srv = SourceSavedViewService(slug=slug)

        try:
            response.data = saved_view_srv.create(
                user=request.user, slug=slug, data=request.data
            )
        except SerializerValidationError as err:
            response.mark_invalid(err.serializer.errors)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to create saved view: {err}")
        else:
            response.add_msg("View has been created")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def patch(self, request, slug, view_slug):
        response = UIResponse()
        saved_view_srv = SourceSavedViewService(slug=slug)

        try:
            response.data = saved_view_srv.update(
                user=request.user, slug=view_slug, data=request.data
            )
        except SerializerValidationError as err:
            response.mark_invalid(err.serializer.errors)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to update saved view: {err}")
        else:
            response.add_msg("View has been updated")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def delete(self, request, slug, view_slug):
        response = UIResponse()
        saved_view_srv = SourceSavedViewService(slug=slug)

        try:
            saved_view_srv.delete(user=request.user, view_slug=view_slug)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to delete saved view: {err}")
        else:
            response.add_msg(f"View {view_slug} has been deleted")
        return Response(response.as_dict())


class SourceView(APIView):
    @method_decorator(login_required)
    def get(self, request, slug=None):
        response = UIResponse()
        try:
            if slug is None:
                data = source_srv.list(user=request.user)
            else:
                data = source_srv.get(user=request.user, slug=slug)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to get sources: {err}")
        else:
            response.data = data
        return Response(response.as_dict())

    @method_decorator(login_required)
    def post(self, request):
        response = UIResponse()

        try:
            response.data = source_srv.create(user=request.user, data=request.data)
        except SerializerValidationError as err:
            response.mark_invalid(err.serializer.errors)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to create source: {err}")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def patch(self, request, slug):
        response = UIResponse()

        try:
            response.data = source_srv.update(
                user=request.user, slug=slug, data=request.data
            )
        except SerializerValidationError as err:
            response.mark_invalid(err.serializer.errors)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to update source: {err}")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def delete(self, request, slug):
        response = UIResponse()

        try:
            source_srv.delete(user=request.user, slug=slug)
        except Exception as err:
            logger.exception("unhandled exception: %s", err)
            response.mark_failed(f"failed to delete source: {err}")
        else:
            response.add_msg(f"source {slug} has been deleted")
        return Response(response.as_dict())


class SourceRoleView(APIView):
    def get_binding_params(self, slug, serializer):
        params = {
            "user": None,
            "group": None,
            "role": serializer.data["role"],
            "source": Source.objects.get(slug=slug),
        }
        if serializer.data["subject"]["kind"] == "user":
            params["user"] = User.objects.get(
                username=serializer.data["subject"]["name"]
            )
        else:
            params["group"] = Group.objects.get(name=serializer.data["subject"]["name"])
        return params


class SourceGrantRoleView(SourceRoleView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        serializer = SourceRoleSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                params = self.get_binding_params(slug, serializer)
                _, created = source_srv.grant_role(
                    user=request.user,
                    slug=slug,
                    role=params["role"],
                    target_user=params["user"],
                    target_group=params["group"],
                )
                if created:
                    response.add_msg("Role has been granted")
                else:
                    response.add_msg("Grant already exist")
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to grant role: {err}")
        return Response(response.as_dict())


class SourceRevokeRoleView(SourceRoleView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()
        serializer = SourceRoleSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                params = self.get_binding_params(slug, serializer)
                deleted = source_srv.revoke_role(
                    user=request.user,
                    slug=slug,
                    role=params["role"],
                    target_user=params["user"],
                    target_group=params["group"],
                )
                if deleted:
                    response.add_msg("Grant has been revoked")
                else:
                    response.add_msg("Grant does not exist")
        except Exception as err:
            response.mark_failed(f"failed to revoke role: {err}")
        return Response(response.as_dict())


class SourceDataAutocompleteView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()

        source = rbac_manager.get_source(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
            fetch_connection=True,
        )
        serializer = SourceAutocompleteRequestSerializer(
            data=request.data,
        )
        if not serializer.is_valid():
            response.validation["result"] = False
            response.validation["fields"] = serializer.errors
            return Response(response.as_dict())
        fetcher = get_fetchers()[source.kind]
        autocomplete_response = fetcher.autocomplete(
            source=source,
            field=serializer.validated_data["field"],
            time_from=serializer.validated_data["from"],
            time_to=serializer.validated_data["to"],
            value=serializer.validated_data["value"],
        )
        response.data["items"] = autocomplete_response.items
        response.data["incomplete"] = autocomplete_response.incomplete
        return Response(response.as_dict())


class SourceDataView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()

        source = rbac_manager.get_source(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
            fetch_connection=True,
        )
        serializer = SourceDataRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )

        if not serializer.is_valid():
            response.validation["result"] = False
            response.validation["fields"] = serializer.errors
            return Response(response.as_dict())

        try:
            fetcher = get_fetchers()[source.kind]
            data_request = DataRequest(
                source=source,
                query=serializer.validated_data.get("query", ""),
                raw_query=serializer.validated_data.get("raw_query", ""),
                time_from=serializer.validated_data["from"],
                time_to=serializer.validated_data["to"],
                limit=serializer.validated_data["limit"],
                context_fields=serializer.validated_data["context_fields"],
            )
            data_response = fetcher.fetch_data(
                data_request,
                tz=UTC_ZONE,
            )
        except Exception as err:
            logger.exception(f"unhandled exception: {err}")
            response.mark_failed(str(err))
        else:
            if data_response.error:
                response.mark_failed(data_response.error)
            else:
                response.data = {
                    "fields": [
                        f.as_dict() for f in serializer.validated_data["fields"]
                    ],
                    "rows": [row.as_dict() for row in data_response.rows],
                    "message": data_response.message,
                }
        return Response(response.as_dict())


class SourceContextFieldDataView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()

        source = rbac_manager.get_source(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
            fetch_connection=True,
        )
        serializer = SourceContextFieldDataSerializer(data=request.data)

        if not serializer.is_valid():
            response.validation["result"] = False
            response.validation["fields"] = serializer.errors
            return Response(response.as_dict())
        try:
            fetcher = get_fetchers()[source.kind]
            response.data["data"] = fetcher.get_context_field_data(
                source,
                serializer.validated_data["field"],
                serializer.validated_data.get("params", {}),
            )
        except Exception as err:
            logger.exception("unhandled exception", err)
            response.mark_failed(str(err))
        return Response(response.as_dict())


class SourceContextFieldsDataView(APIView):
    """Returns all context fields data in a single call."""

    @method_decorator(login_required)
    def get(self, request, slug):
        response = UIResponse()

        source = rbac_manager.get_source(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
            fetch_connection=True,
        )
        try:
            fetcher = get_fetchers()[source.kind]
            if hasattr(fetcher, "get_all_context_fields_data"):
                response.data = fetcher.get_all_context_fields_data(source)
            else:
                response.data = {}
        except Exception as err:
            logger.exception("unhandled exception", err)
            response.mark_failed(str(err))
        return Response(response.as_dict())


class SourceGraphDataView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()

        source = rbac_manager.get_source(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
            fetch_connection=True,
        )
        serializer = SourceGraphDataRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )

        if not serializer.is_valid():
            response.validation["result"] = False
            response.validation["fields"] = serializer.errors
            return Response(response.as_dict())

        try:
            fetcher = get_fetchers()[source.kind]
            graph_data_request = GraphDataRequest(
                source=source,
                query=serializer.validated_data.get("query", ""),
                raw_query=serializer.validated_data.get("raw_query", ""),
                time_from=serializer.validated_data["from"],
                time_to=serializer.validated_data["to"],
                group_by=serializer.validated_data["group_by"],
                context_fields=serializer.validated_data["context_fields"],
            )
            graph_data_response = fetcher.fetch_graph_data(graph_data_request)
        except Exception as err:
            logger.exception("Unhandled error: %s", err)
            response.mark_failed(str(err))
        else:
            response.data = {
                "timestamps": graph_data_response.timestamps,
                "data": graph_data_response.data,
                "total": graph_data_response.total,
            }
        return Response(response.as_dict())


class SourceDataAndGraphDataView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()

        source = rbac_manager.get_source(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
            fetch_connection=True,
        )

        # Only allow combined mode for sources that support it
        if source.query_mode != "combined":
            response.mark_failed(
                "This source does not support combined data/graph queries"
            )
            return Response(response.as_dict())

        serializer = SourceDataAndGraphDataRequestSerializer(
            data=request.data, context={"source": source, "user": request.user}
        )

        if not serializer.is_valid():
            response.validation["result"] = False
            response.validation["fields"] = serializer.errors
            return Response(response.as_dict())

        try:
            fetcher = get_fetchers()[source.kind]
            combined_request = DataAndGraphDataRequest(
                source=source,
                query=serializer.validated_data.get("query", ""),
                raw_query=serializer.validated_data.get("raw_query", ""),
                time_from=serializer.validated_data["from"],
                time_to=serializer.validated_data["to"],
                limit=serializer.validated_data["limit"],
                group_by=serializer.validated_data["group_by"],
                context_fields=serializer.validated_data["context_fields"],
            )
            combined_response = fetcher.fetch_data_and_graph(
                combined_request,
                tz=UTC_ZONE,
            )
        except NotImplementedError:
            response.mark_failed("Combined fetch not supported for this source type")
        except Exception as err:
            logger.exception(f"unhandled exception: {err}")
            response.mark_failed(str(err))
        else:
            if combined_response.error:
                response.mark_failed(combined_response.error)
            else:
                response.data = {
                    "fields": [
                        f.as_dict() for f in serializer.validated_data["fields"]
                    ],
                    "rows": [row.as_dict() for row in combined_response.rows],
                    "message": combined_response.message,
                    "graph": {
                        "timestamps": combined_response.graph_timestamps,
                        "data": combined_response.graph_data,
                        "total": combined_response.graph_total,
                    },
                }
        return Response(response.as_dict())


class SourceTestConnectionView(APIView):
    @method_decorator(login_required)
    def post(self, request, kind):
        response = UIResponse()
        fetcher = get_fetchers()[kind]

        serializer_cls = CONNECTION_KIND_TO_SERIALIZER.get(kind)
        if not serializer_cls:
            response.mark_failed(f"Unsupported source kind: {kind}")
            Response(response.as_dict())

        try:
            serializer = serializer_cls(data=request.data)
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                connection_test_response = fetcher.test_connection(serializer.data)
                response.data = connection_test_response.as_dict()
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to test connection: {err}")
        return Response(response.as_dict())


class GetSourceSchemaView(APIView):
    @method_decorator(login_required)
    def post(self, request, kind):
        response = UIResponse()

        serializer_cls = SCHEMA_KIND_TO_SERIALIZER.get(kind)
        if not serializer_cls:
            response.mark_failed(f"Unsupported source kind: {kind}")
            return Response(response.as_dict())

        try:
            serializer = serializer_cls(data=request.data)
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
                return Response(response.as_dict())

            # Fetch the connection
            connection = Connection.objects.get(
                id=serializer.validated_data["connection_id"]
            )

            # Check USE permission
            rbac_manager.require_connection_permissions(
                user=request.user,
                connection_id=connection.id,
                required_permissions=[permissions.Connection.USE.value],
            )

            # Get the fetcher and call get_schema
            fetcher = get_fetchers()[kind]

            # Build data dict with connection data + additional params
            data = dict(connection.data)
            if kind == "clickhouse":
                data["database"] = serializer.validated_data["database"]
                data["table"] = serializer.validated_data["table"]

            schema = fetcher.get_schema(data)
            response.data = schema

        except Connection.DoesNotExist:
            response.mark_failed("Connection not found")
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"Failed to get source schema: {err}")

        return Response(response.as_dict())
