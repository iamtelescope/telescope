"""Roadmap P5.5: server-side pinned facets and dashboard favorites, per user."""

import pytest
from rest_framework.test import APIClient

from telescope.models import Dashboard
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from tests.fixtures import *  # noqa: F401,F403

from telescope_prefs.models import DashboardFavorite, PinnedFacets

PINS = "ui/v1/prefs/pinned-facets"
FAVS = "ui/v1/prefs/favorites/dashboards"


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def call(client, method, path, body=None):
    response = getattr(client, method)(f"/{path}", body, format="json")
    assert response.status_code == 200, response.content[:300]
    return response.json()


@pytest.fixture
def viewer(test_user, clickhouse_source):
    RBACManager().grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    return test_user


@pytest.mark.django_db
def test_pins_are_null_until_saved_then_per_user(viewer, root_user, clickhouse_source):
    a, b = client_for(viewer), client_for(root_user)
    path = f"{PINS}/{clickhouse_source.slug}"
    assert call(a, "get", path)["data"] == {"facets": None}
    saved = call(a, "post", path, {"facets": ["hostname", "attrs.k", "hostname"]})
    assert saved["data"] == {"facets": ["hostname", "attrs.k"]}
    # A second browser of the same user sees the same pins; another user does not.
    assert call(client_for(viewer), "get", path)["data"]["facets"] == [
        "hostname",
        "attrs.k",
    ]
    assert call(b, "get", path)["data"] == {"facets": None}
    call(a, "post", path, {"facets": []})
    assert call(a, "get", path)["data"] == {"facets": []}
    assert PinnedFacets.objects.count() == 1


@pytest.mark.django_db
def test_pins_need_source_read(hacker_user, clickhouse_source):
    client = client_for(hacker_user)
    path = f"{PINS}/{clickhouse_source.slug}"
    assert call(client, "get", path)["result"] is False
    assert call(client, "post", path, {"facets": ["x"]})["result"] is False
    assert not PinnedFacets.objects.exists()


@pytest.mark.django_db
def test_pins_are_validated(viewer, clickhouse_source):
    client = client_for(viewer)
    path = f"{PINS}/{clickhouse_source.slug}"
    for body in [{}, {"facets": "x"}, {"facets": ["x"] * 101}, {"facets": ["x" * 513]}]:
        response = call(client, "post", path, body)
        assert response["result"] is False
        assert "facets" in response["validation"]["fields"]
    assert not PinnedFacets.objects.exists()


@pytest.mark.django_db
def test_pins_go_with_the_source(viewer, clickhouse_source):
    call(
        client_for(viewer),
        "post",
        f"{PINS}/{clickhouse_source.slug}",
        {"facets": ["a"]},
    )
    clickhouse_source.delete()
    assert not PinnedFacets.objects.exists()


@pytest.mark.django_db
def test_dashboard_favorites(test_user, root_user, dashboard):
    owner, other = client_for(test_user), client_for(root_user)
    assert call(owner, "get", FAVS)["data"] == {"dashboards": []}
    added = call(owner, "post", f"{FAVS}/{dashboard.slug}")
    assert added["data"] == {"dashboards": [dashboard.slug]}
    call(owner, "post", f"{FAVS}/{dashboard.slug}")
    assert DashboardFavorite.objects.count() == 1
    assert call(client_for(test_user), "get", FAVS)["data"]["dashboards"] == [
        dashboard.slug
    ]
    assert call(other, "get", FAVS)["data"] == {"dashboards": []}
    removed = call(owner, "delete", f"{FAVS}/{dashboard.slug}")
    assert removed["data"] == {"dashboards": []}


@pytest.mark.django_db
def test_private_dashboard_cannot_be_favorited_by_others(hacker_user, dashboard):
    client = client_for(hacker_user)
    response = call(client, "post", f"{FAVS}/{dashboard.slug}")
    assert response["result"] is False
    assert not DashboardFavorite.objects.exists()


@pytest.mark.django_db
def test_favorite_hidden_once_dashboard_is_no_longer_visible(
    test_user, hacker_user, dashboard
):
    dashboard.shared = True
    dashboard.save()
    client = client_for(hacker_user)
    call(client, "post", f"{FAVS}/{dashboard.slug}")
    assert call(client, "get", FAVS)["data"]["dashboards"] == [dashboard.slug]
    Dashboard.objects.filter(pk=dashboard.pk).update(shared=False)
    assert call(client, "get", FAVS)["data"]["dashboards"] == []
    dashboard.delete()
    assert not DashboardFavorite.objects.exists()


@pytest.mark.django_db
def test_prefs_need_login(clickhouse_source):
    client = APIClient()
    response = client.get(f"/{PINS}/{clickhouse_source.slug}")
    assert response.status_code == 302
    assert client.get(f"/{FAVS}").status_code == 302
