"""Every tool allows and denies exactly what API v2 (or /ui/v1 for traces) does, per role."""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from telescope.models import APIToken, Dashboard
from telescope.rbac.manager import RBACManager
from telescope_api2.tests.conftest import chart_body, search_body
from telescope_api2.tests.test_rbac_matrix import (  # noqa: F401
    RAW_ROLES,
    ROLES,
    USE_ROLES,
    dashboard_body,
    rolled_back,
    ui_outcome,
    v2_outcome,
    visible,
    world,
)
from telescope_mcp.tests.conftest import call_tool, session_client
from tests.data import get_dashboard_data

rbac_manager = RBACManager()
TILE = {"id": "mcp1", "chart": {"display": "text", "text": "hi"}}


def mcp_args(body):
    """search/chart tool arguments from an API v2 request body."""
    return {k: v for k, v in body.items() if k not in ("context_columns",)}


def cases(dashboards, alerts):
    """(name, tool, arguments, reference client, method, path, body)."""
    out = [
        ("sources", "list_sources", {}, "v2", "get", "api/v1/sources", None),
        (
            "describe",
            "describe_source",
            {"source": "clickhouse"},
            "v2",
            "get",
            "api/v1/sources/clickhouse",
            None,
        ),
        ("dash list", "list_dashboards", {}, "v2", "get", "api/v1/dashboards", None),
        ("alert list", "list_alerts", {}, "v2", "get", "api/v1/alerts", None),
        (
            "trace",
            "get_trace",
            {"source": "clickhouse", "trace_id": "abc"},
            "ui",
            "post",
            "ui/v1/otel/clickhouse/trace",
            {"trace_id": "abc"},
        ),
    ]
    for name, extra in [("search", {}), ("search raw", {"raw_query": "1 = 1"})]:
        body = search_body(**extra)
        args = {"source": "clickhouse", **mcp_args(body)}
        out.append(
            (
                name,
                "search",
                args,
                "v2",
                "post",
                "api/v1/sources/clickhouse/search",
                body,
            )
        )
    for name, extra in [("chart", {}), ("chart raw", {"raw_query": "1 = 1"})]:
        body = chart_body(**extra)
        args = {"source": "clickhouse", **body}
        out.append(
            (name, "chart", args, "v2", "post", "api/v1/sources/clickhouse/chart", body)
        )
    for d in dashboards:
        path = f"api/v1/dashboards/{d.slug}"
        out += [
            (
                f"dash get {d.name}",
                "get_dashboard",
                {"dashboard": d.slug},
                "v2",
                "get",
                path,
                None,
            ),
            (
                f"tile upsert {d.name}",
                "upsert_tile",
                {"dashboard": d.slug, "tile": TILE},
                "v2",
                "patch",
                path,
                dashboard_body(version=1),
            ),
        ]
    return out


def mcp_outcome(result):
    error, data = result
    return ("denied", None) if error else ("ok", data)


@pytest.mark.django_db
@pytest.mark.parametrize("role", ROLES)
def test_tools_match_api_rbac(role, world, fake_ch, clickhouse_source):
    dashboards, _, alerts = world
    user = User.objects.create(username=f"u-{role}", is_superuser=role == "superuser")
    if role not in (None, "superuser"):
        rbac_manager.grant_source_role(clickhouse_source, role, user=user)
    own = Dashboard.objects.create(
        slug="d-own", name="own", owner=user, updated_by=user, data=get_dashboard_data()
    )
    token = APIToken.create(user, "t").token
    v2 = APIClient(raise_request_exception=False)
    v2.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    mcp = APIClient()
    mcp.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    refs = {"v2": v2, "ui": session_client(user)}
    mismatches, allowed = [], set()
    stub = {"trace_id": "abc", "found": False}
    with patch("telescope_mcp.tools.fetch_trace", return_value=stub), patch(
        "telescope_otel.trace_views.fetch_trace", return_value=stub
    ):
        for name, tool, args, ref, method, path, body in cases(
            dashboards + [own], alerts
        ):
            ref_res = rolled_back(
                lambda: getattr(refs[ref], method)(f"/{path}", body, format="json")
            )
            ref_state, ref_data = (ui_outcome if ref == "ui" else v2_outcome)(ref_res)
            state, data = mcp_outcome(rolled_back(lambda: call_tool(mcp, tool, args)))
            same = state == ref_state
            if same and state == "ok" and tool.startswith("list_"):
                same = visible(data) == visible(ref_data)
            if same and state == "ok" and tool == "get_dashboard":
                same = data == ref_data
            if not same:
                mismatches.append((name, ref_state, state, str(data)[:200]))
            if state == "ok":
                allowed.add(name)
    assert mismatches == []
    assert "dash get shared" in allowed
    assert ("dash get private" in allowed) == (role == "superuser")
    assert "tile upsert own" in allowed
    assert ("tile upsert shared" in allowed) == (role == "superuser")
    assert ("search" in allowed) == ("trace" in allowed) == (role in USE_ROLES)
    assert ("chart raw" in allowed) == (role in RAW_ROLES)
    assert ("describe" in allowed) == (role is not None)
