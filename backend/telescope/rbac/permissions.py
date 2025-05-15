from enum import Enum


class Global(Enum):
    CREATE_SOURCE = "global_create_source"
    READ_SOURCE = "global_read_source"
    EDIT_SOURCE = "global_edit_source"
    GRANT_SOURCE = "global_grant_source"
    RAW_QUERY_SOURCE = "global_raw_query_source"
    USE_SOURCE = "global_use_source"
    DELETE_SOURCE = "global_delete_source"

    MANAGE_SOURCES = "manage_sources"
    MANAGE_RBAC = "manage_rbac"


class Source(Enum):
    USE = "use"
    READ = "read"
    EDIT = "edit"
    GRANT = "grant"
    DELETE = "delete"
    RAW_QUERY = "raw_query"


class SavedView(Enum):
    READ = "read"
    EDIT = "edit"


GLOBAL_TO_SOURCE = {
    Global.READ_SOURCE.value: Source.READ.value,
    Global.EDIT_SOURCE.value: Source.EDIT.value,
    Global.GRANT_SOURCE.value: Source.GRANT.value,
    Global.DELETE_SOURCE.value: Source.DELETE.value,
    Global.RAW_QUERY_SOURCE.value: Source.RAW_QUERY.value,
    Global.USE_SOURCE.value: Source.USE.value,
}
