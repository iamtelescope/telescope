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
    ConnectionSerializer,
    SourceWithConnectionSerializer,
    SourceFieldSerializer,
    NewSourceSerializer,
    UpdateSourceSerializer,
    SourceDataRequestSerializer,
    SourceGraphDataRequestSerializer,
    SourceAutocompleteRequestSerializer,
)


logger = logging.getLogger("telescope.views.source")


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
            serializer = NewSourceSerializer(data=request.data)
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                with transaction.atomic():
                    source = Source.create(
                        serializer.data, username=request.user.username
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
            serializer = UpdateSourceSerializer(data=request.data)
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


def get_client_kwargs(data):
    return {
        "host": data["host"],
        "port": data["port"],
        "user": data["user"],
        "password": data["password"],
        "secure": data["ssl"],
    }


def get_telescope_field(name, _type):
    data = {
        "name": name,
        "display_name": "",
        "values": "",
        "type": _type,
        "jsonstring": False,
        "autocomplete": True,
        "suggest": True,
        "group_by": True,
    }
    if "datetime" in _type.lower():
        data["autocomplete"] = False
        data["group_by"] = False
    elif _type.startswith("Enum"):
        try:
            data["values"] = ",".join(
                [
                    x.split(" = ")[0].strip().replace("'", "")
                    for x in _type.split("(")[1].split(")")[0].split(",")
                ]
            )
        except Exception:
            pass

    return data


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
            )
            data_response = fetcher.fetch_data(
                data_request,
                timezone=ZoneInfo("UTC"),
            )
        except Exception as err:
            response.mark_failed(str(err))
        else:
            response.data = {
                "fields": [f.as_dict() for f in serializer.validated_data["fields"]],
                "rows": [row.as_dict() for row in data_response.rows],
            }
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
    def post(self, request):
        response = UIResponse()
        test_data = {
            "reachability": {
                "result": False,
                "error": "",
            },
            "schema": {
                "result": False,
                "error": "",
                "data": {},
            },
        }
        try:
            serializer = ConnectionSerializer(data=request.data)
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                with Client(**get_client_kwargs(serializer.data)) as client:
                    target = (
                        f"`{serializer.data['database']}`.`{serializer.data['table']}`"
                    )
                    try:
                        client.execute(f"SELECT 1 FROM {target} LIMIT 1")
                    except Exception as err:
                        test_data["reachability"]["error"] = str(err)
                        test_data["schema"][
                            "error"
                        ] = "Skipped due to reachability test failed"
                    else:
                        test_data["reachability"]["result"] = True
                        try:
                            result = client.execute(
                                f"DESCRIBE TABLE {target} FORMAT JSON"
                            )
                        except Exception as err:
                            test_data["schema"]["error"] = str(err)
                        else:
                            test_data["schema"]["result"] = True
                            test_data["schema"]["data"] = [
                                get_telescope_field(x[0], x[1]) for x in result
                            ]
                response.data = test_data
        except Exception as err:
            response.mark_failed(f"failed to test connection: {err}")
        return Response(response.as_dict())
