import logging
from typing import List, Dict, Optional, Union, TypeVar, Type

from django.db.models import Q, Model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.contrib.auth.models import User, Group


from telescope.rbac.roles import ROLES
from telescope.rbac import permissions
from telescope.models import (
    GlobalRoleBinding,
    SourceRoleBinding,
    ConnectionRoleBinding,
    Source,
    Connection,
    SavedView,
)
from telescope.constants import (
    VIEW_SCOPE_PERSONAL,
    VIEW_SCOPE_SOURCE,
    VIEW_KIND_USER,
    VIEW_KIND_SHARED,
    VIEW_KIND_SOURCE,
)

logger = logging.getLogger("telescope.rbac.manager")

# TypeVar for better type hints
ModelType = TypeVar("ModelType", Source, Connection)

SOURCE_CONFIG = {
    "pk_key": "slug",
    "role_binding_class": SourceRoleBinding,
    "role_binding_field": "source",
    "global_read_permission": permissions.Global.READ_SOURCE.value,
    "global_to_local_mapping": permissions.GLOBAL_TO_SOURCE,
    "roles_kind": "source",
}

CONNECTION_CONFIG = {
    "pk_key": "pk",
    "role_binding_class": ConnectionRoleBinding,
    "role_binding_field": "connection",
    "global_read_permission": permissions.Global.READ_CONNECTION.value,
    "global_to_local_mapping": permissions.GLOBAL_TO_CONNECTION,
    "roles_kind": "connection",
}

SUPPORTED_MODELS = {
    Source: SOURCE_CONFIG,
    Connection: CONNECTION_CONFIG,
}


class RBACManager:
    @staticmethod
    def _get_model_config(model_class):
        if model_class not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_class}")
        return SUPPORTED_MODELS[model_class]

    @staticmethod
    def _roles_to_permissions(roles: List[str], kind: str) -> set:
        result = set()
        for role in roles:
            if role in ROLES[kind]:
                for name in ROLES[kind][role]:
                    result.add(name)
        return result

    def _get_user_global_permissions(self, user: User, groups=None) -> set:
        groups = groups if groups is not None else user.groups.all()
        if not user.is_superuser:
            roles = (
                GlobalRoleBinding.objects.filter(Q(group__in=groups) | Q(user=user))
                .values_list("role", flat=True)
                .distinct()
            )
        else:
            roles = ROLES["global"].keys()
        return self._roles_to_permissions(roles, kind="global")

    def _get_objects(
        self,
        model_class: Type[ModelType],
        user: User,
        pk: Optional[Union[int, str]] = None,
        filters: Optional[Dict] = None,
        required_permissions: Optional[List[str]] = None,
        fetch_connection: bool = False,
    ) -> Union[List[ModelType], ModelType]:
        filters = filters or {}
        config = self._get_model_config(model_class)

        _global_filter = {}
        _filter = {}

        for key, value in filters.items():
            _global_filter[key] = value
            _filter[f"{config['role_binding_field']}__{key}"] = value

        if pk:
            _global_filter[config["pk_key"]] = pk
            _filter[f"{config['role_binding_field']}__{config['pk_key']}"] = pk

        objects = []
        objects_map = {}

        global_user_permissions = self._get_user_global_permissions(user)

        if config["global_read_permission"] in global_user_permissions:
            global_object_permissions = set()
            for perm in global_user_permissions:
                local_perm = config["global_to_local_mapping"].get(perm)
                if local_perm:
                    global_object_permissions.add(local_perm)

            object_queryset = model_class.objects.filter(**_global_filter)
            if fetch_connection and model_class == Source:
                object_queryset = object_queryset.select_related("conn")

            for obj in object_queryset:
                obj.add_perms(global_object_permissions)
                objects_map[obj.pk] = {"object": obj, "roles": []}

        binding_queryset = config["role_binding_class"].objects.select_related(
            config["role_binding_field"]
        )
        if fetch_connection and model_class == Source:
            binding_queryset = binding_queryset.select_related(
                f"{config['role_binding_field']}__conn"
            )

        bindings = binding_queryset.filter(
            (Q(user=user) | Q(group__in=user.groups.all())) & Q(**_filter)
        )

        for binding in bindings:
            obj = getattr(binding, config["role_binding_field"])
            if obj.pk not in objects_map:
                objects_map[obj.pk] = {
                    "object": obj,
                    "roles": [binding.role],
                }
            else:
                objects_map[obj.pk]["roles"].append(binding.role)

        for _, data in objects_map.items():
            if data["roles"]:
                data["object"].add_perms(
                    self._roles_to_permissions(data["roles"], kind=config["roles_kind"])
                )
            objects.append(data["object"])

        if required_permissions:
            objects = list(
                filter(
                    lambda obj: all(
                        [perm in obj.permissions for perm in required_permissions]
                    ),
                    objects,
                )
            )

        if pk is not None:
            if not objects:
                raise model_class.DoesNotExist(f"object with pk {pk} does not exist or you have no permissions to read it")
            elif len(objects) > 1:
                raise model_class.MultipleObjectsReturned(
                    f"returned more than one {model_class.__name__} -- it returned {len(objects)}!"
                )
            return objects[0]
        return objects

    def require_permissions(
        self,
        user: User,
        model_class: Union[Source, Connection],
        pk: Union[int, str],
        required_permissions: List[str],
        raise_exception: bool = True,
    ) -> bool:
        config = self._get_model_config(model_class)
        groups = user.groups.all()

        global_user_permissions = self._get_user_global_permissions(user, groups=groups)

        global_local_permissions = set()
        for perm in global_user_permissions:
            local_perm = config["global_to_local_mapping"].get(perm)
            if local_perm:
                global_local_permissions.add(local_perm)

        if all([perm in global_local_permissions for perm in required_permissions]):
            return True

        filter_kwargs = {f"{config['role_binding_field']}__{config["pk_key"]}": pk}

        bindings = config["role_binding_class"].objects.filter(
            (Q(user=user) | Q(group__in=groups)) & Q(**filter_kwargs)
        )

        existing_permissions = self._roles_to_permissions(
            [b.role for b in bindings], kind=config["roles_kind"]
        )

        if all([perm in existing_permissions for perm in required_permissions]):
            return True
        else:
            if raise_exception:
                raise PermissionDenied("Insufficient permissions")
            else:
                return False

    def get_sources(
        self,
        user: User,
        source_filter: Optional[Dict] = None,
        required_permissions: Optional[List[str]] = None,
        fetch_connection: bool = False,
    ) -> List[Source]:
        return self._get_objects(
            Source,
            user,
            filters=source_filter,
            required_permissions=required_permissions,
            fetch_connection=fetch_connection,
        )

    def get_source(
        self,
        user: User,
        source_slug: str,
        required_permissions: Optional[List[str]] = None,
        fetch_connection: bool = False,
    ) -> Source:
        return self._get_objects(
            Source,
            user,
            pk=source_slug,
            required_permissions=required_permissions,
            fetch_connection=fetch_connection,
        )

    def get_connections(
        self,
        user: User,
        connection_filter: Optional[Dict] = None,
        required_permissions: Optional[List[str]] = None,
    ) -> List[Connection]:
        return self._get_objects(
            Connection,
            user,
            filters=connection_filter,
            required_permissions=required_permissions,
        )

    def get_connection(
        self,
        user: User,
        connection_id: int,
        required_permissions: Optional[List[str]] = None,
    ) -> Connection:
        return self._get_objects(
            Connection,
            user,
            pk=connection_id,
            required_permissions=required_permissions,
        )

    def grant_role(
        self,
        model_class: Union[Source, Connection],
        object_instance: Union[Source, Connection],
        role: str,
        user: Optional[User] = None,
        group: Optional[Group] = None,
    ) -> tuple:
        config = self._get_model_config(model_class)

        if role not in ROLES[config["roles_kind"]]:
            raise ValueError(f"unknown {config['roles_kind']} role: {role}")

        if user is None and group is None:
            raise ValueError("either user or group should be provided")

        filter_kwargs = {
            "role": role,
            "user": user,
            "group": group,
            config["role_binding_field"]: object_instance,
        }

        binding = None
        created = False

        if not config["role_binding_class"].objects.filter(**filter_kwargs).exists():
            created = True
            binding = config["role_binding_class"].objects.create(**filter_kwargs)

        return binding, created

    def revoke_role(
        self,
        model_class: Union[Source, Connection],
        object_instance: Union[Source, Connection],
        role: str,
        user: Optional[User] = None,
        group: Optional[Group] = None,
    ) -> bool:
        config = self._get_model_config(model_class)

        if role not in ROLES[config["roles_kind"]]:
            raise ValueError(f"unknown {config['roles_kind']} role: {role}")

        if user is None and group is None:
            raise ValueError("either user or group should be provided")

        filter_kwargs = {
            "role": role,
            "user": user,
            "group": group,
            config["role_binding_field"]: object_instance,
        }

        deleted = False
        with transaction.atomic():
            binding = config["role_binding_class"].objects.filter(**filter_kwargs)
            if binding.exists():
                binding.delete()
                deleted = True

        return deleted

    # Global role management
    def grant_global_role(
        self, role: str, user: Optional[User] = None, group: Optional[Group] = None
    ):
        if role not in ROLES["global"]:
            raise ValueError(f"unknown global role: {role}")

        if user is None and group is None:
            raise ValueError("either user or group should be provided")

        if not GlobalRoleBinding.objects.filter(
            user=user, group=group, role=role
        ).exists():
            GlobalRoleBinding.objects.create(user=user, group=group, role=role)

    def revoke_global_role(
        self, role: str, user: Optional[User] = None, group: Optional[Group] = None
    ):
        if role not in ROLES["global"]:
            raise ValueError(f"unknown global role: {role}")

        if user is None and group is None:
            raise ValueError("either user or group should be provided")

        GlobalRoleBinding.objects.filter(user=user, group=group, role=role).delete()

    def require_global_permissions(self, user: User, required_permissions: List[str]):
        user_permissions = self._get_user_global_permissions(user)
        for permission in required_permissions:
            if permission not in user_permissions:
                logger.debug(
                    "user %s has no global permission: %s", user.username, permission
                )
                raise PermissionDenied("Insufficient permissions")

    def get_user_global_permissions(self, user: User, groups=None) -> set:
        return self._get_user_global_permissions(user, groups)

    # Convenience wrappers for source/connection roles
    def grant_source_role(
        self,
        source: Source,
        role: str,
        user: Optional[User] = None,
        group: Optional[Group] = None,
    ):
        return self.grant_role(Source, source, role, user, group)

    def revoke_source_role(
        self,
        source: Source,
        role: str,
        user: Optional[User] = None,
        group: Optional[Group] = None,
    ):
        return self.revoke_role(Source, source, role, user, group)

    def grant_connection_role(
        self,
        connection: Connection,
        role: str,
        user: Optional[User] = None,
        group: Optional[Group] = None,
    ):
        return self.grant_role(Connection, connection, role, user, group)

    def revoke_connection_role(
        self,
        connection: Connection,
        role: str,
        user: Optional[User] = None,
        group: Optional[Group] = None,
    ):
        return self.revoke_role(Connection, connection, role, user, group)

    # Convenience methods for permission checks
    def require_source_permissions(
        self,
        user: User,
        source_slug: str,
        required_permissions: List[str],
        raise_exception: bool = True,
    ) -> bool:
        return self.require_permissions(
            user, Source, source_slug, required_permissions, raise_exception
        )

    def require_connection_permissions(
        self,
        user: User,
        connection_id: int,
        required_permissions: List[str],
        raise_exception: bool = True,
    ) -> bool:
        return self.require_permissions(
            user, Connection, connection_id, required_permissions, raise_exception
        )

    def user_has_source_permissions(
        self, user: User, source_slug: str, required_permissions: List[str]
    ) -> bool:
        return self.require_source_permissions(
            user, source_slug, required_permissions, raise_exception=False
        )

    def user_has_connection_permissions(
        self, user: User, connection_id: int, required_permissions: List[str]
    ) -> bool:
        return self.require_connection_permissions(
            user, connection_id, required_permissions, raise_exception=False
        )

    # Saved view management
    def calculate_view_permissions(
        self, user: User, source: Source, view: SavedView
    ) -> set:
        if view.source_id != source.pk:
            raise ValueError("view does not belong to source")

        view_permissions = set()
        if view.is_personal_scope():
            if view.user == user:
                view_permissions.add(permissions.SavedView.READ.value)
                view_permissions.add(permissions.SavedView.EDIT.value)
            else:
                if view.shared:
                    view_permissions.add(permissions.SavedView.READ.value)
        else:
            if permissions.Source.READ.value in source.permissions:
                view_permissions.add(permissions.SavedView.READ.value)
            if permissions.Source.EDIT.value in source.permissions:
                view_permissions.add(permissions.SavedView.EDIT.value)

        return view_permissions

    def require_saved_view_ownership(self, user: User, view: SavedView):
        if view.user != user:
            raise PermissionDenied("Insufficient permissions")

    def get_saved_view_kind(self, user: User, view: SavedView) -> str:
        if view.scope == VIEW_SCOPE_SOURCE:
            return VIEW_KIND_SOURCE
        else:
            if view.user == user:
                return VIEW_KIND_USER
            else:
                return VIEW_KIND_SHARED

    def get_source_saved_views(
        self, user: User, source_slug: str, required_permissions: List[str]
    ) -> List[SavedView]:
        source = self.get_source(user, source_slug, required_permissions)
        views = []
        for view in SavedView.objects.filter(
            Q(source=source, user=user, scope=VIEW_SCOPE_PERSONAL)
            | Q(source=source, scope=VIEW_SCOPE_SOURCE)
            | Q(source=source, scope=VIEW_SCOPE_PERSONAL, shared=True),
        ):
            view.add_perms(self.calculate_view_permissions(user, source, view))
            view.set_kind(self.get_saved_view_kind(user, view))
            views.append(view)
        return views

    def get_source_saved_view(
        self,
        user: User,
        source_slug: str,
        view_slug: str,
        required_permissions: List[str],
    ) -> SavedView:
        source = self.get_source(user, source_slug, required_permissions)
        try:
            view = SavedView.objects.get(
                Q(slug=view_slug, source=source, user=user, scope=VIEW_SCOPE_PERSONAL)
                | Q(slug=view_slug, source=source, scope=VIEW_SCOPE_SOURCE)
                | Q(slug=view_slug, source=source, scope=VIEW_SCOPE_PERSONAL, shared=True)
            )
        except SavedView.DoesNotExist:
            raise SavedView.DoesNotExist(
                f"Saved view '{view_slug}' does not exist or you don't have permission to access it"
            )
        view.add_perms(self.calculate_view_permissions(user, source, view))
        view.set_kind(self.get_saved_view_kind(user, view))
        return view
