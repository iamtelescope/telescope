from enum import Enum

from telescope.rbac import permissions


class GlobalRole(Enum):
    ADMIN = "admin"


class SourceRole(Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    USER = "user"
    SQLUSER = "sqluser"


ROLES = {
    "global": {
        GlobalRole.ADMIN.value: [
            permissions.Global.MANAGE_RBAC.value,
            permissions.Global.MANAGE_SOURCES.value,
            permissions.Global.CREATE_SOURCE.value,
            permissions.Global.READ_SOURCE.value,
            permissions.Global.EDIT_SOURCE.value,
            permissions.Global.GRANT_SOURCE.value,
            permissions.Global.SQL_SOURCE.value,
            permissions.Global.USE_SOURCE.value,
            permissions.Global.DELETE_SOURCE.value,
        ],
    },
    "source": {
        SourceRole.OWNER.value: [
            permissions.Source.READ.value,
            permissions.Source.EDIT.value,
            permissions.Source.DELETE.value,
            permissions.Source.USE.value,
            permissions.Source.GRANT.value,
            permissions.Source.SQL.value,
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
        SourceRole.SQLUSER.value: [
            permissions.Source.READ.value,
            permissions.Source.USE.value,
            permissions.Source.SQL.value,
        ],
    },
}


def resolve_permissions(*roles, kind):
    permissions = set()
    for role in roles:
        for name in ROLES[kind][role]:
            permissions.add(name)
    return permissions
