"""Tags every ClickHouse query with what asked for it, via the `log_comment` setting.
Keys and sanitising follow HyperDX common-utils/src/clickhouse/attribution.ts (MIT)."""

import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from telescope.rbac import permissions
from telescope.rbac.manager import RBACManager

FIELDS = ["surface", "dashboard", "tile", "alert", "source"]
MAX_FIELD_LENGTH = 128
UNSAFE = re.compile(r"[^A-Za-z0-9_.:/@-]")
SEARCH_ACTIONS = {"data", "graphData", "dataAndGraph", "export"}

_tags = ContextVar("telescope_query_attribution", default=None)
_statements = ContextVar("telescope_query_statements", default=None)

rbac_manager = RBACManager()


def _clean(value):
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    return UNSAFE.sub("_", str(value))[:MAX_FIELD_LENGTH] or None


@contextmanager
def attribute(**tags):
    """Adds tags to every query run inside the block; `user` may be an id or a callable."""
    merged = dict(_tags.get() or {})
    merged.update({k: v for k, v in tags.items() if v not in (None, "")})
    token = _tags.set(merged)
    try:
        yield merged
    finally:
        _tags.reset(token)


def for_alert(func):
    """Runs `func(alert, ...)` attributed to the alert, its owner and its tile."""

    @wraps(func)
    def wrapper(alert, *args, **kwargs):
        dashboard = getattr(alert, "dashboard", None)
        with attribute(
            surface="alert",
            alert=alert.pk,
            user=alert.owner_id,
            dashboard=dashboard.slug if dashboard else None,
            tile=getattr(alert, "tile_id", None),
        ):
            return func(alert, *args, **kwargs)

    return wrapper


def log_comment():
    """The JSON for `log_comment`, or None outside any attribution block."""
    tags = _tags.get()
    if not tags:
        return None
    out = {}
    for key in FIELDS:
        value = _clean(tags.get(key))
        if value is not None:
            out[key] = value
    user = tags.get("user")
    user = user() if callable(user) else user
    if user is not None:
        out["user"] = user
    return json.dumps(out, separators=(",", ":"))


def query_settings(settings=None):
    """`settings` plus the log comment of the current block."""
    comment = log_comment()
    if not comment:
        return settings
    return {**(settings or {}), "log_comment": comment}


def record(sql):
    statements = _statements.get()
    if statements is not None:
        statements.append(sql)


@contextmanager
def recording():
    token = _statements.set([])
    try:
        yield _statements.get()
    finally:
        _statements.reset(token)


def debug_sql(user, source_slug):
    """SQL run so far in this request, for users with RAW_QUERY on the source only."""
    statements = _statements.get()
    if not statements or not rbac_manager.user_has_source_permissions(
        user, source_slug, [permissions.Source.RAW_QUERY.value]
    ):
        return None
    return {"sql": list(statements)}


def request_tags(request):
    path = request.path_info
    parts = path.strip("/").split("/")
    source = parts[3] if len(parts) > 3 and parts[2] == "sources" else None
    dashboard = request.GET.get("dashboard")
    if path.startswith("/api/"):
        surface = "api"
    elif dashboard:
        surface = "dashboard"
    elif path.startswith("/ui/v1/alerts"):
        surface = "alert"
    elif source and parts[-1] in SEARCH_ACTIONS:
        surface = "search"
    elif source and parts[-1] == "chartData":
        surface = "chart-preview"
    elif source:
        surface = "metadata"
    else:
        surface = "ui"

    def user():
        # Read at query time, so DRF token auth has already set request.user.
        u = getattr(request, "user", None)
        return u.pk if u is not None and u.is_authenticated else None

    return {
        "surface": surface,
        "source": source,
        "dashboard": dashboard,
        "tile": request.GET.get("tile"),
        "user": user,
    }


class QueryAttributionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with attribute(**request_tags(request)), recording():
            return self.get_response(request)
