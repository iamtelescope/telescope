import logging

from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.contrib.auth.models import User

from telescope.constants import (
    VIEW_SCOPE_PERSONAL,
    VIEW_SCOPE_SOURCE,
    VIEW_KIND_USER,
    VIEW_KIND_SHARED,
    VIEW_KIND_SOURCE,
)
from telescope.rbac.roles import ROLES
from telescope.rbac import permissions
from telescope.models import GlobalRoleBinding, SourceRoleBinding, Source, SavedView

logger = logging.getLogger("telescope.rbac.helpers")


def roles_to_permissions(roles, kind):
    result = set()
    for role in roles:
        for name in ROLES[kind][role]:
            result.add(name)
    return result


def get_user_global_permissions(user, groups=None):
    groups = groups if groups is not None else user.groups.all()
    if not user.is_superuser:
        roles = (
            GlobalRoleBinding.objects.filter(Q(group__in=groups) | Q(user=user))
            .values_list("role", flat=True)
            .distinct()
        )
    else:
        roles = ROLES["global"].keys()
    return roles_to_permissions(roles, kind="global")


def global_permissions_to_source_permissions(global_perms):
    result = set()
    for perm in global_perms:
        source_perm = permissions.GLOBAL_TO_SOURCE.get(perm)
        if source_perm:
            result.add(source_perm)
    return result


def grant_global_role(role, user=None, group=None):
    if role not in ROLES["global"]:
        raise ValueError(f"unknown global role: {role}")

    if user is None and group is None:
        raise ValueError("either user or group should be proivded")

    if not GlobalRoleBinding.objects.filter(user=user, group=group, role=role).exists():
        GlobalRoleBinding.objects.create(user=user, group=group, role=role)


def revoke_global_role(role, user=None, group=None):
    if role not in ROLES["global"]:
        raise ValueError(f"unknown global role: {role}")

    if user is None and group is None:
        raise ValueError("either user or group should be proivded")

    GlobalRoleBinding.objects.filter(user=user, group=group, role=role).delete()


def grant_source_role(source, role, user=None, group=None):
    if role not in ROLES["source"]:
        raise ValueError(f"unknown source role: {role}")

    if user is None and group is None:
        raise ValueError("either user or group should be proivded")

    created = False
    binding = None

    if not SourceRoleBinding.objects.filter(
        user=user, group=group, source=source, role=role
    ).exists():
        created = True
        binding = SourceRoleBinding.objects.create(
            user=user, group=group, source=source, role=role
        )
    return binding, created


def revoke_source_role(source, role, user=None, group=None):
    if role not in ROLES["source"]:
        raise ValueError(f"unknown source role: {role}")

    if user is None and group is None:
        raise ValueError("either user or group should be proivded")

    deleted = False
    with transaction.atomic():
        binding = SourceRoleBinding.objects.filter(
            user=user, group=group, source=source, role=role
        )
        if binding.exists():
            binding.delete()
            deleted = True
    return deleted


def require_global_permissions(
    user,
    required_permissions,
):
    user_permissions = get_user_global_permissions(user)
    for permission in required_permissions:
        if permission not in user_permissions:
            logger.debug(
                "use %s has no global permission: %s", user.username, permission
            )
            raise PermissionDenied("Insufficient permissions")


def require_source_permissions(
    user, source_slug, required_permissions, raise_exception=True
):
    groups = user.groups.all()
    global_user_permissions = get_user_global_permissions(user, groups=groups)
    global_source_permissions = global_permissions_to_source_permissions(
        global_user_permissions
    )

    if all([perm in global_source_permissions for perm in required_permissions]):
        return True

    bindings = SourceRoleBinding.objects.filter(
        (Q(user=user) | Q(group__in=groups)), source__slug=source_slug
    )
    existing_permissions = roles_to_permissions(
        [b.role for b in bindings], kind="source"
    )

    if all([perm in existing_permissions for perm in required_permissions]):
        return True
    else:
        if raise_exception:
            raise PermissionDenied("Insufficient permissions")
        else:
            return False


def user_has_source_permissions(user, source_slug, required_permissions):
    return require_source_permissions(
        user, source_slug, required_permissions, raise_exception=False
    )


def get_sources(user, source_slug=None, source_filter=None, required_permissions=None):
    source_filter = source_filter or {}
    _global_filter = {}
    _filter = {}

    for key, value in source_filter.items():
        _global_filter[key] = value
        _filter[f"source__{key}"] = value

    if source_slug:
        _global_filter["slug"] = source_slug
        _filter["source__slug"] = source_slug

    sources = []
    sources_map = {}

    global_user_permissions = get_user_global_permissions(user)

    if permissions.Global.READ_SOURCE.value in global_user_permissions:
        global_source_permissions = global_permissions_to_source_permissions(
            global_user_permissions
        )
        for source in Source.objects.filter(**_global_filter):
            source.add_perms(global_source_permissions)
            sources_map[source.pk] = {"source": source, "roles": []}

    bindings = SourceRoleBinding.objects.select_related("source").filter(
        (Q(user=user) | Q(group__in=user.groups.all())) & Q(**_filter)
    )

    for binding in bindings:
        if binding.source.pk not in sources_map:
            sources_map[binding.source.pk] = {
                "source": binding.source,
                "roles": [binding.role],
            }
        else:
            sources_map[binding.source.pk]["roles"].append(binding.role)

    for _, data in sources_map.items():
        data["source"].add_perms(roles_to_permissions(data["roles"], kind="source"))
        sources.append(data["source"])

    if required_permissions:
        sources = list(
            filter(
                lambda source: all(
                    [name in source.permissions for name in required_permissions]
                ),
                sources,
            )
        )

    if source_slug and not sources:
        raise Source.DoesNotExist(f"object with pk {source_slug} does not exist")
    elif source_slug and len(sources) > 1:
        raise Source.MultipleObjectsReturned(
            f"returned mor than one Source -- it returned {len(sources)}!"
        )
    elif source_slug and len(sources) == 1:
        return sources[0]
    else:
        return sources


def calculate_view_permissions(user, source, view):
    # should never happens
    if view.source_id != source.pk:
        raise ValueError

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


def require_saved_view_ownership(user: User, view: SavedView):
    if view.user != user:
        raise PermissionDenied("Insufficient permissions")


def get_source(user, slug, required_permissions):
    return get_sources(
        user, source_slug=slug, required_permissions=required_permissions
    )


def get_saved_view_kind(user, view):
    if view.scope == VIEW_SCOPE_SOURCE:
        return VIEW_KIND_SOURCE
    else:
        if view.user == user:
            return VIEW_KIND_USER
        else:
            return VIEW_KIND_SHARED


def get_source_saved_views(user, source_slug, required_permissions):
    source = get_source(user, source_slug, required_permissions)
    views = []
    for view in SavedView.objects.filter(
        Q(source=source, user=user, scope=VIEW_SCOPE_PERSONAL)
        | Q(source=source, scope=VIEW_SCOPE_SOURCE)
        | Q(source=source, scope=VIEW_SCOPE_PERSONAL, shared=True),
    ):
        view.add_perms(calculate_view_permissions(user, source, view))
        view.set_kind(get_saved_view_kind(user, view))
        views.append(view)
    return views


def get_source_saved_view(user, source_slug, view_slug, required_permissions):
    source = get_source(user, source_slug, required_permissions)
    view = SavedView.objects.get(
        Q(slug=view_slug, source=source, user=user, scope=VIEW_SCOPE_PERSONAL)
        | Q(slug=view_slug, source=source, scope=VIEW_SCOPE_SOURCE)
    )
    view.add_perms(calculate_view_permissions(user, source, view))
    view.set_kind(get_saved_view_kind(user, view))
    return view
