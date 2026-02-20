from typing import Optional, Tuple
from django.contrib.auth.models import User, Group
from django.db import transaction

from telescope.services.exceptions import (
    SerializerValidationError,
    ConnectionInUseError,
)
from telescope.models import Connection, Source
from telescope.rbac import permissions
from telescope.rbac.roles import ConnectionRole
from telescope.rbac.manager import RBACManager
from telescope.serializers.connection import (
    ConnectionSerializer,
    ConnectionListSerializer,
    ConnectionCreateResponseSerializer,
    ConnectionUpdateResponseSerializer,
    ClickhouseConnectionSerializer,
    DockerConnectionSerializer,
    KubernetesConnectionSerializer,
    StarrocksConnectionSerializer
)


class ConnectionService:
    def __init__(self):
        self.rbac_manager = RBACManager()

    def get(self, user: User, pk: int):
        with transaction.atomic():
            conn = self.rbac_manager.get_connection(
                user=user,
                connection_id=pk,
                required_permissions=[permissions.Connection.READ.value],
            )
            return ConnectionSerializer(conn).data

    def list(self, user: User):
        with transaction.atomic():
            conns = self.rbac_manager.get_connections(
                user=user,
                required_permissions=[permissions.Connection.READ.value],
            )
            return ConnectionListSerializer(conns, many=True).data

    def list_usable(self, user: User):
        with transaction.atomic():
            conns = self.rbac_manager.get_connections(
                user=user,
                required_permissions=[permissions.Connection.USE.value],
            )
            return ConnectionListSerializer(conns, many=True).data

    def get_names_map(self, user: User):
        with transaction.atomic():
            conns = self.rbac_manager.get_connections(
                user=user,
                required_permissions=[permissions.Connection.READ.value],
            )
            return {conn.id: conn.name for conn in conns}

    def create(self, user: User, data: dict, raise_is_valid=False):
        with transaction.atomic():
            self.rbac_manager.require_global_permissions(
                user, [permissions.Global.CREATE_CONNECTION.value]
            )

            serializer = ConnectionSerializer(data=data)
            if not serializer.is_valid(raise_exception=raise_is_valid):
                raise SerializerValidationError(serializer)

            kind = serializer.data["kind"]
            if kind == "clickhouse":
                data_serializer_cls = ClickhouseConnectionSerializer
            elif kind == "docker":
                data_serializer_cls = DockerConnectionSerializer
            elif kind == "kubernetes":
                data_serializer_cls = KubernetesConnectionSerializer
            elif kind == "starrocks":
                data_serializer_cls = StarrocksConnectionSerializer
            data_serializer = data_serializer_cls(data=serializer.data["data"])
            if not data_serializer.is_valid(raise_exception=raise_is_valid):
                raise SerializerValidationError(data_serializer)
            else:
                conn = Connection.objects.create(**serializer.data)
                self.rbac_manager.grant_role(
                    model_class=Connection,
                    object_instance=conn,
                    role=ConnectionRole.OWNER.value,
                    user=user,
                )
                return ConnectionCreateResponseSerializer(conn).data

    def update(self, user: User, pk: int, data: dict, raise_is_valid=False):
        with transaction.atomic():
            self.rbac_manager.require_permissions(
                user=user,
                model_class=Connection,
                pk=pk,
                required_permissions=[permissions.Connection.EDIT.value],
            )

            serializer = ConnectionSerializer(data=data)
            if not serializer.is_valid(raise_exception=raise_is_valid):
                raise SerializerValidationError(serializer)

            conn = Connection.objects.get(pk=pk)
            if conn.kind == "clickhouse":
                data_serializer_cls = ClickhouseConnectionSerializer
            elif conn.kind == "docker":
                data_serializer_cls = DockerConnectionSerializer
            elif conn.kind == "kubernetes":
                data_serializer_cls = KubernetesConnectionSerializer
            elif conn.kind == "starrocks":
                data_serializer_cls = StarrocksConnectionSerializer
            data_serializer = data_serializer_cls(data=serializer.data["data"])

            if not data_serializer.is_valid(raise_exception=raise_is_valid):
                raise SerializerValidationError(data_serializer)
            else:
                for key, value in serializer.validated_data.items():
                    if key != "slug":
                        setattr(conn, key, value)
                conn.save()
                return ConnectionUpdateResponseSerializer(conn).data

    def delete(self, user: User, pk: int):
        with transaction.atomic():
            self.rbac_manager.require_permissions(
                user=user,
                model_class=Connection,
                pk=pk,
                required_permissions=[permissions.Connection.DELETE.value],
            )

            # Check if connection is being used by any sources
            source_count = Source.objects.filter(conn_id=pk).count()
            if source_count > 0:
                raise ConnectionInUseError(connection_id=pk, source_count=source_count)

            Connection.objects.get(pk=pk).delete()

    def get_role_bindings(self, user: User, pk: int):
        with transaction.atomic():
            # Only users with GRANT permission can see role bindings
            self.rbac_manager.require_connection_permissions(
                user=user,
                connection_id=pk,
                required_permissions=[permissions.Connection.GRANT.value],
            )
            from telescope.models import ConnectionRoleBinding
            from telescope.serializers.connection import ConnectionRoleBindingSerializer

            bindings = ConnectionRoleBinding.objects.filter(connection__pk=pk)
            return ConnectionRoleBindingSerializer(bindings, many=True).data

    def grant_role(
        self,
        user: User,
        pk: int,
        role: str,
        target_user: Optional[User] = None,
        target_group: Optional[Group] = None,
    ) -> Tuple:
        with transaction.atomic():
            self.rbac_manager.require_connection_permissions(
                user=user,
                connection_id=pk,
                required_permissions=[permissions.Connection.GRANT.value],
            )
            return self.rbac_manager.grant_connection_role(
                connection=Connection.objects.get(pk=pk),
                role=role,
                user=target_user,
                group=target_group,
            )

    def revoke_role(
        self,
        user: User,
        pk: int,
        role: str,
        target_user: Optional[User] = None,
        target_group: Optional[Group] = None,
    ) -> bool:
        with transaction.atomic():
            self.rbac_manager.require_connection_permissions(
                user=user,
                connection_id=pk,
                required_permissions=[permissions.Connection.GRANT.value],
            )
            return self.rbac_manager.revoke_connection_role(
                connection=Connection.objects.get(pk=pk),
                role=role,
                user=target_user,
                group=target_group,
            )
