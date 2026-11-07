"""Acceptance 1: every v2 endpoint allows and denies exactly what /ui/v1 does, per role."""

from django.contrib.auth.models import User
from django.db import transaction

import pytest

from telescope.models import Dashboard, SavedView
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope_alerts.models import Alert
from tests.data import get_dashboard_data, get_saved_view_data

from telescope_api2.tests.conftest import (
    chart_body,
    search_body,
    session_client,
    token_client,
)

rbac_manager = RBACManager()
ROLES = [None, "superuser"] + [r.value for r in SourceRole]
USE_ROLES = {"superuser", "owner", "user", "raw_query_user"}
RAW_ROLES = {"superuser", "owner", "raw_query_user"}


def dashboard_body(**changes):
    body = {"name": "D", "description": "", "shared": False}
    body.update(data=get_dashboard_data(), **changes)
    return body


def view_body(scope="personal"):
    body = {"name": "V", "description": "", "shared": False, "scope": scope}
    return {**body, "data": get_saved_view_data()}


def alert_body():
    return {
        "name": "A",
        "kind": "search",
        "source": "clickhouse",
        "query": "",
        "series": {"agg": "count"},
        "interval": "5m",
        "threshold_type": "above",
        "threshold": 1,
    }


@pytest.fixture
def world(root_user, test_user, ch_source):
    clickhouse_source = ch_source
    """Objects owned by root and by test_user, some shared, on one ClickHouse source."""
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    dashboards = [
        Dashboard.objects.create(
            slug=f"d-{n}",
            name=n,
            owner=owner,
            updated_by=owner,
            shared=shared,
            data=get_dashboard_data(),
        )
        for n, owner, shared in [
            ("private", root_user, False),
            ("shared", root_user, True),
            ("mine", test_user, False),
        ]
    ]
    views = [
        SavedView.objects.create(
            slug=f"v-{n}",
            name=n,
            description="",
            scope=scope,
            source=clickhouse_source,
            user=owner,
            shared=shared,
            data=get_saved_view_data(),
        )
        for n, owner, scope, shared in [
            ("source", root_user, "source", False),
            ("private", root_user, "personal", False),
            ("shared", test_user, "personal", True),
        ]
    ]
    alerts = [
        Alert.objects.create(
            name=f"a{owner.pk}",
            owner=owner,
            kind="search",
            source_slug="clickhouse",
            series={"agg": "count"},
            interval="5m",
            threshold_type="above",
            threshold=1,
        )
        for owner in [root_user, test_user]
    ]
    return dashboards, views, alerts


def cases(dashboards, views, alerts):
    """(name, ui method, ui path, v2 method, v2 path, body) for every v2 operation."""
    out = [
        ("dash list", "get", "ui/v1/dashboards", "get", "api/v1/dashboards", None),
        (
            "dash create",
            "post",
            "ui/v1/dashboards",
            "post",
            "api/v1/dashboards",
            dashboard_body(),
        ),
        ("alert list", "get", "ui/v1/alerts", "get", "api/v1/alerts", None),
        ("alert create", "post", "ui/v1/alerts", "post", "api/v1/alerts", alert_body()),
        (
            "view list",
            "get",
            "ui/v1/sources/clickhouse/savedViews",
            "get",
            "api/v1/saved-views?source=clickhouse",
            None,
        ),
        (
            "search",
            "post",
            "ui/v1/sources/clickhouse/data",
            "post",
            "api/v1/sources/clickhouse/search",
            search_body(),
        ),
        (
            "search raw",
            "post",
            "ui/v1/sources/clickhouse/data",
            "post",
            "api/v1/sources/clickhouse/search",
            search_body(raw_query="1 = 1"),
        ),
        (
            "chart",
            "post",
            "ui/v1/sources/clickhouse/chartData",
            "post",
            "api/v1/sources/clickhouse/chart",
            chart_body(),
        ),
        (
            "chart raw",
            "post",
            "ui/v1/sources/clickhouse/chartData",
            "post",
            "api/v1/sources/clickhouse/chart",
            chart_body(raw_query="1 = 1"),
        ),
    ]
    for scope in ["personal", "source"]:
        out.append(
            (
                f"view create {scope}",
                "post",
                "ui/v1/sources/clickhouse/savedViews",
                "post",
                "api/v1/saved-views",
                {**view_body(scope), "source": "clickhouse"},
            )
        )
    for d in dashboards:
        ui, v2 = f"ui/v1/dashboards/{d.slug}", f"api/v1/dashboards/{d.slug}"
        out += [
            (f"dash get {d.name}", "get", ui, "get", v2, None),
            (
                f"dash patch {d.name}",
                "patch",
                ui,
                "patch",
                v2,
                dashboard_body(version=1),
            ),
            (f"dash delete {d.name}", "delete", ui, "delete", v2, None),
        ]
    for v in views:
        ui = f"ui/v1/sources/clickhouse/savedViews/{v.slug}"
        v2 = f"api/v1/saved-views/clickhouse/{v.slug}"
        out += [
            (f"view get {v.name}", "get", ui, "get", v2, None),
            (f"view patch {v.name}", "patch", ui, "patch", v2, view_body(v.scope)),
            (f"view delete {v.name}", "delete", ui, "delete", v2, None),
        ]
    for a in alerts:
        ui, v2 = f"ui/v1/alerts/{a.pk}", f"api/v1/alerts/{a.pk}"
        out += [
            (f"alert get {a.name}", "get", ui, "get", v2, None),
            (f"alert patch {a.name}", "patch", ui, "patch", v2, alert_body()),
            (f"alert delete {a.name}", "delete", ui, "delete", v2, None),
        ]
    return out


def rolled_back(call):
    with transaction.atomic():
        response = call()
        transaction.set_rollback(True)
    return response


def ui_outcome(response):
    if response.status_code >= 400:
        return "denied", None
    body = response.json()
    if not body["result"] or body["validation"]["result"] is False:
        return "denied", None
    return "ok", body["data"]


def v2_outcome(response):
    if response.status_code >= 400:
        return "denied", None
    return "ok", response.json() if response.content else None


def visible(data):
    # Lists are compared by the keys of what each side shows.
    items = data["data"] if isinstance(data, dict) and "data" in data else data
    if isinstance(items, list):
        return sorted(str(i.get("slug") or i.get("id")) for i in items)
    return None


@pytest.mark.django_db
@pytest.mark.parametrize("role", ROLES)
def test_v2_matches_ui_rbac(role, world, fake_ch, clickhouse_source):
    user = User.objects.create(username=f"u-{role}", is_superuser=role == "superuser")
    if role not in (None, "superuser"):
        rbac_manager.grant_source_role(clickhouse_source, role, user=user)
    ui, v2 = session_client(user), token_client(user)
    mismatches, allowed = [], set()
    for name, ui_method, ui_path, v2_method, v2_path, body in cases(*world):
        ui_res = rolled_back(
            lambda: getattr(ui, ui_method)(f"/{ui_path}", body, format="json")
        )
        v2_res = rolled_back(
            lambda: getattr(v2, v2_method)(f"/{v2_path}", body, format="json")
        )
        (ui_state, ui_data), (v2_state, v2_data) = ui_outcome(ui_res), v2_outcome(
            v2_res
        )
        if ui_state != v2_state or (
            ui_state == "ok" and visible(ui_data) != visible(v2_data)
        ):
            mismatches.append((name, ui_state, v2_state, v2_res.content[:200]))
        if v2_state == "ok":
            allowed.add(name)
    assert mismatches == []
    # The matrix is not trivial: each role is allowed some things and denied others.
    assert "dash get shared" in allowed
    assert ("dash get private" in allowed) == (role == "superuser")
    assert ("search" in allowed) == (role in USE_ROLES)
    assert ("chart raw" in allowed) == (role in RAW_ROLES)
