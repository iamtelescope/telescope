from enum import Enum

from telescope.rbac import permissions


class GlobalRole(Enum):
    ADMIN = "admin"
    CONNECTION_MANAGER = "connection_manager"
    SOURCE_MANAGER = "source_manager"


class SourceRole(Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    USER = "user"
    RAW_QUERY_USER = "raw_query_user"


class ConnectionRole(Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    USER = "user"


ROLES = {
    "global": {
        GlobalRole.ADMIN.value: [
            permissions.Global.MANAGE_RBAC.value,
            permissions.Global.CREATE_SOURCE.value,
            permissions.Global.READ_SOURCE.value,
            permissions.Global.EDIT_SOURCE.value,
            permissions.Global.GRANT_SOURCE.value,
            permissions.Global.RAW_QUERY_SOURCE.value,
            permissions.Global.USE_SOURCE.value,
            permissions.Global.DELETE_SOURCE.value,
            permissions.Global.CREATE_CONNECTION.value,
            permissions.Global.READ_CONNECTION.value,
            permissions.Global.EDIT_CONNECTION.value,
            permissions.Global.GRANT_CONNECTION.value,
            permissions.Global.USE_CONNECTION.value,
            permissions.Global.DELETE_CONNECTION.value,
        ],
        GlobalRole.CONNECTION_MANAGER.value: [
            permissions.Global.CREATE_CONNECTION.value,
        ],
        GlobalRole.SOURCE_MANAGER.value: [
            permissions.Global.CREATE_SOURCE.value,
        ],
    },
    "source": {
        SourceRole.OWNER.value: [
            permissions.Source.READ.value,
            permissions.Source.EDIT.value,
            permissions.Source.DELETE.value,
            permissions.Source.USE.value,
            permissions.Source.GRANT.value,
            permissions.Source.RAW_QUERY.value,
        ],
        SourceRole.EDITOR.value: [
            permissions.Source.READ.value,
            permissions.Source.EDIT.value,
            permissions.Source.DELETE.value,
        ],
        SourceRole.VIEWER.value: [
            permissions.Source.READ.value,
        ],
        SourceRole.USER.value: [
            permissions.Source.READ.value,
            permissions.Source.USE.value,
        ],
        SourceRole.RAW_QUERY_USER.value: [
            permissions.Source.READ.value,
            permissions.Source.USE.value,
            permissions.Source.RAW_QUERY.value,
        ],
    },
    "connection": {
        ConnectionRole.OWNER.value: [
            permissions.Connection.READ.value,
            permissions.Connection.EDIT.value,
            permissions.Connection.DELETE.value,
            permissions.Connection.USE.value,
            permissions.Connection.GRANT.value,
        ],
        ConnectionRole.EDITOR.value: [
            permissions.Connection.READ.value,
            permissions.Connection.EDIT.value,
            permissions.Connection.DELETE.value,
        ],
        ConnectionRole.VIEWER.value: [
            permissions.Connection.READ.value,
        ],
        ConnectionRole.USER.value: [
            permissions.Connection.READ.value,
            permissions.Connection.USE.value,
        ],
    },
}


def resolve_permissions(*roles, kind):
    permissions = set()
    for role in roles:
        for name in ROLES[kind][role]:
            permissions.add(name)
    return permissions
