import json
import logging

from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User, Group

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from clickhouse_driver import Client

from telescope.rbac.helpers import (
    get_sources,
    get_source,
    grant_source_role,
    revoke_source_role,
    require_source_permissions,
    user_has_source_permissions,
)

from telescope.fetchers import get_fetchers
from telescope.fetchers.request import DataRequest, GraphDataRequest
from telescope.rbac.roles import SourceRole
from telescope.rbac import permissions
from telescope.auth.decorators import global_permission_required
from telescope.fields import parse as parse_fields
from telescope.fields import ParserError as FieldsParserError
from telescope.response import UIResponse
from telescope.models import Source, SourceRoleBinding
from telescope.serializers.source import (
    SourceAdminSerializer,
    SourceSerializer,
    UserSerializer,
    GroupSerializer,
    SubjectSerializer,
    SourceRoleSerializer,
    SourceRoleBindingSerializer,
    ClickhouseConnectionSerializer,
    DockerConnectionSerializer,
    SourceWithConnectionSerializer,
    SourceFieldSerializer,
    SourceKindSerializer,
    NewClickhouseSourceSerializer,
    NewDockerSourceSerializer,
    UpdateClickhouseSourceSerializer,
    UpdateDockerSourceSerializer,
    SourceDataRequestSerializer,
    SourceGraphDataRequestSerializer,
    SourceAutocompleteRequestSerializer,
    SourceContextFieldDataSerializer,
)


logger = logging.getLogger("telescope.views.source")

CONNECTION_KIND_TO_SERIALIZER = {
    "clickhouse": ClickhouseConnectionSerializer,
    "docker": DockerConnectionSerializer,
}


class SourceRoleBindingView(APIView):
    @method_decorator(login_required)
    def get(self, request, slug):
        response = UIResponse()

        require_source_permissions(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.GRANT.value],
        )

        try:
            bindings = SourceRoleBinding.objects.filter(source__slug=slug)
            serializer = SourceRoleBindingSerializer(bindings, many=True)
        except Exception as err:
            response.mark_failed(f"failed to get source role bindings: {err}")
        else:
            response.data = serializer.data
        return Response(response.as_dict())


class SourceView(APIView):
    @method_decorator(login_required)
    def get(self, request, slug=None):
        response = UIResponse()
        try:
            if slug is None:
                sources = get_sources(
                    request.user, required_permissions=[permissions.Source.READ.value]
                )
                serializer = SourceSerializer(sources, many=True)
            else:
                source = get_source(
                    request.user,
                    slug=slug,
                    required_permissions=[permissions.Source.READ.value],
                )
                if user_has_source_permissions(
                    request.user,
                    source_slug=slug,
                    required_permissions=[permissions.Source.EDIT.value],
                ):
                    serializer_class = SourceWithConnectionSerializer
                else:
                    serializer_class = SourceSerializer
                serializer = serializer_class(source)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to get sources: {err}")
        else:
            response.data = serializer.data
        return Response(response.as_dict())

    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.CREATE_SOURCE.value])
    )
    def post(self, request):
        response = UIResponse()

        try:
            kind_serializer = SourceKindSerializer(data=request.data)
            if not kind_serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
                return Response(response.as_dict())
            kind = kind_serializer.data["kind"]
            if kind == "clickhouse":
                serializer_cls = NewClickhouseSourceSerializer
            elif kind == "docker":
                serializer_cls = NewDockerSourceSerializer
            serializer = serializer_cls(data=request.data)
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                with transaction.atomic():
                    source = Source.create(
                        kind, serializer.data, username=request.user.username
                    )
                    grant_source_role(
                        source=source, role=SourceRole.OWNER.value, user=request.user
                    )
                    response.data = {"slug": source.slug}
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to create source: {err}")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def patch(self, request, slug):
        response = UIResponse()

        require_source_permissions(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.EDIT.value],
        )

        try:
            source = Source.objects.get(slug=slug)
            if source.kind == "clickhouse":
                serializer_cls = UpdateClickhouseSourceSerializer
            elif source.kind == "docker":
                serializer_cls = UpdateDockerSourceSerializer
            serializer = serializer_cls(data=request.data)
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                with transaction.atomic():
                    for key, value in serializer.data.items():
                        if key != "slug":
                            setattr(source, key, value)
                    source.save()

                    response.data = {"slug": source.slug}
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to update source: {err}")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def delete(self, request, slug):
        response = UIResponse()

        require_source_permissions(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.DELETE.value],
        )

        try:
            with transaction.atomic():
                Source.objects.get(slug=slug).delete()
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

        require_source_permissions(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.GRANT.value],
        )

        try:
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                params = self.get_binding_params(slug, serializer)
                _, created = grant_source_role(
                    source=params["source"],
                    role=params["role"],
                    user=params["user"],
                    group=params["group"],
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

        require_source_permissions(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.GRANT.value],
        )

        try:
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                params = self.get_binding_params(slug, serializer)
                deleted = revoke_source_role(
                    source=params["source"],
                    role=params["role"],
                    user=params["user"],
                    group=params["group"],
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

        require_source_permissions(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
        )
        source = Source.objects.get(slug=slug)
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

        require_source_permissions(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
        )

        source = Source.objects.get(slug=slug)
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
                query=serializer.validated_data["query"],
                raw_query=serializer.validated_data.get("raw_query", ""),
                time_from=serializer.validated_data["from"],
                time_to=serializer.validated_data["to"],
                limit=serializer.validated_data["limit"],
                context_fields=serializer.validated_data["context_fields"],
            )
            data_response = fetcher.fetch_data(
                data_request,
                timezone=ZoneInfo("UTC"),
            )
        except Exception as err:
            logger.exception(f"unhandled exception: {err}")
            response.mark_failed(str(err))
        else:
            response.data = {
                "fields": [f.as_dict() for f in serializer.validated_data["fields"]],
                "rows": [row.as_dict() for row in data_response.rows],
            }
        return Response(response.as_dict())


class SourceContextFieldDataView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()

        require_source_permissions(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
        )

        source = Source.objects.get(slug=slug)

        serializer = SourceContextFieldDataSerializer(data=request.data)

        if not serializer.is_valid():
            response.validation["result"] = False
            response.validation["fields"] = serializer.errors
            return Response(response.as_dict())
        try:
            fetcher = get_fetchers()[source.kind]
            response.data["data"] = fetcher.get_context_field_data(
                source, serializer.validated_data["field"]
            )
        except Exception as err:
            logger.exception("unhandled exception", err)
            response.mark_failed(str(err))
        return Response(response.as_dict())


class SourceGraphDataView(APIView):
    @method_decorator(login_required)
    def post(self, request, slug):
        response = UIResponse()

        require_source_permissions(
            user=request.user,
            source_slug=slug,
            required_permissions=[permissions.Source.USE.value],
        )
        source = Source.objects.get(slug=slug)

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
                query=serializer.validated_data["query"],
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
