import logging

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group

from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.services.connection import ConnectionService
from telescope.services.exceptions import SerializerValidationError, ConnectionInUseError
from telescope.rbac.manager import RBACManager
from telescope.rbac import permissions

from telescope.fetchers import get_fetchers
from telescope.response import UIResponse
from telescope.models import Connection

from telescope.serializers.connection import (
    ClickhouseConnectionSerializer,
    DockerConnectionSerializer,
    KubernetesConnectionSerializer,
    ConnectionRoleSerializer,
)

CONNECTION_KIND_TO_SERIALIZER = {
    "clickhouse": ClickhouseConnectionSerializer,
    "docker": DockerConnectionSerializer,
    "kubernetes": KubernetesConnectionSerializer,
}

rbac_manager = RBACManager()
logger = logging.getLogger("telescope.views.connection")
connection_srv = ConnectionService()


class ConnectionView(APIView):
    @method_decorator(login_required)
    def get(self, request, pk=None):
        response = UIResponse()

        try:
            if pk is None:
                data = connection_srv.list(user=request.user)
            else:
                data = connection_srv.get(user=request.user, pk=pk)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to get connections: {err}")
        else:
            response.data = data
        return Response(response.as_dict())

    @method_decorator(login_required)
    def post(self, request):
        response = UIResponse()

        try:
            response.data = connection_srv.create(user=request.user, data=request.data)
        except SerializerValidationError as err:
            response.mark_invalid(err.serializer.errors)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to create connection: {err}")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def patch(self, request, pk):
        response = UIResponse()
        try:
            response.data = connection_srv.update(
                user=request.user, pk=pk, data=request.data
            )
        except SerializerValidationError as err:
            response.mark_invalid(err.serializer.errors)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to update connection: {err}")
        return Response(response.as_dict())

    @method_decorator(login_required)
    def delete(self, request, pk):
        response = UIResponse()

        try:
            connection_srv.delete(user=request.user, pk=pk)
        except ConnectionInUseError as err:
            response.mark_failed(err.message)
        except Exception as err:
            logger.exception("unhandled exception: %s", err)
            response.mark_failed(f"failed to delete connection: {err}")
        else:
            response.add_msg(f"connection {pk} has been deleted")
        return Response(response.as_dict())


class UsableConnectionsView(APIView):
    """Returns connections that user can use (for source creation)"""

    @method_decorator(login_required)
    def get(self, request):
        response = UIResponse()

        try:
            data = connection_srv.list_usable(user=request.user)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to get usable connections: {err}")
        else:
            response.data = data
        return Response(response.as_dict())


class ConnectionNamesView(APIView):
    """Returns map of connection IDs to names for connections user can read"""

    @method_decorator(login_required)
    def get(self, request):
        response = UIResponse()

        try:
            data = connection_srv.get_names_map(user=request.user)
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to get connection names: {err}")
        else:
            response.data = data
        return Response(response.as_dict())


class TestConnectionView(APIView):
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
                connection_test_response = fetcher.test_connection_ng(serializer.data)
                response.data = connection_test_response.as_dict()
        except Exception as err:
            logger.exception(err)
            response.mark_failed(f"failed to test connection: {err}")
        return Response(response.as_dict())


class ConnectionRoleBindingView(APIView):
    @method_decorator(login_required)
    def get(self, request, pk):
        response = UIResponse()

        try:
            response.data = connection_srv.get_role_bindings(user=request.user, pk=pk)
        except Exception as err:
            response.mark_failed(f"failed to get connection role bindings: {err}")
        return Response(response.as_dict())


class ConnectionRoleView(APIView):
    def get_binding_params(self, pk, serializer):
        params = {
            "user": None,
            "group": None,
            "role": serializer.data["role"],
            "connection": Connection.objects.get(pk=pk),
        }
        if serializer.data["subject"]["kind"] == "user":
            params["user"] = User.objects.get(
                username=serializer.data["subject"]["name"]
            )
        else:
            params["group"] = Group.objects.get(name=serializer.data["subject"]["name"])
        return params


class ConnectionGrantRoleView(ConnectionRoleView):
    @method_decorator(login_required)
    def post(self, request, pk):
        response = UIResponse()
        serializer = ConnectionRoleSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                params = self.get_binding_params(pk, serializer)
                _, created = connection_srv.grant_role(
                    user=request.user,
                    pk=pk,
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


class ConnectionRevokeRoleView(ConnectionRoleView):
    @method_decorator(login_required)
    def post(self, request, pk):
        response = UIResponse()
        serializer = ConnectionRoleSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                params = self.get_binding_params(pk, serializer)
                deleted = connection_srv.revoke_role(
                    user=request.user,
                    pk=pk,
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
