import re

import pytest
from django.core.exceptions import PermissionDenied
from django.test import override_settings
from django.conf import settings

from telescope.models import Dashboard
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope.services.dashboard import DashboardService
from telescope.services.exceptions import SerializerValidationError

from tests.data import get_dashboard_data

rbac_manager = RBACManager()
service = DashboardService()


def payload(dashboard, **changes):
    data = {
        "name": dashboard.name,
        "description": dashboard.description,
        "shared": dashboard.shared,
        "data": dashboard.data,
        "version": dashboard.version,
    }
    data.update(changes)
    return data


def share(dashboard):
    dashboard.shared = True
    dashboard.save()


@pytest.mark.django_db
def test_owner_has_all_permissions(test_user, dashboard):
    result = service.get(test_user, dashboard.slug)
    assert result["permissions"] == ["read", "edit", "delete"]
    assert result["owner"] == {
        "id": test_user.id,
        "username": "test_user",
        "first_name": "",
        "last_name": "",
    }
    assert result["data"]["tiles"][0]["id"] == "t1"


@pytest.mark.django_db
def test_superuser_has_all_permissions(root_user, dashboard):
    assert service.get(root_user, dashboard.slug)["permissions"] == [
        "read",
        "edit",
        "delete",
    ]
    result = service.update(root_user, dashboard.slug, payload(dashboard, name="X"))
    assert result["name"] == "X"
    assert result["updated_by"]["username"] == "test_root"
    service.delete(root_user, dashboard.slug)
    assert not Dashboard.objects.filter(slug=dashboard.slug).exists()


@pytest.mark.django_db
def test_private_dashboard_hidden_from_others(hacker_user, dashboard):
    with pytest.raises(Dashboard.DoesNotExist, match="Dashboard not found"):
        service.get(hacker_user, dashboard.slug)
    with pytest.raises(Dashboard.DoesNotExist, match="Dashboard not found"):
        service.update(hacker_user, dashboard.slug, payload(dashboard))
    with pytest.raises(Dashboard.DoesNotExist, match="Dashboard not found"):
        service.delete(hacker_user, dashboard.slug)
    assert service.list(hacker_user) == []


@pytest.mark.django_db
def test_missing_dashboard(test_user):
    with pytest.raises(Dashboard.DoesNotExist, match="Dashboard not found"):
        service.get(test_user, "nope-000000")


@pytest.mark.django_db
def test_shared_dashboard_is_read_only_for_others(hacker_user, dashboard):
    share(dashboard)
    assert service.get(hacker_user, dashboard.slug)["permissions"] == ["read"]
    with pytest.raises(PermissionDenied):
        service.update(hacker_user, dashboard.slug, payload(dashboard, name="pwn"))
    with pytest.raises(PermissionDenied):
        service.delete(hacker_user, dashboard.slug)
    dashboard.refresh_from_db()
    assert dashboard.name == "Test Dashboard"
    assert [d["slug"] for d in service.list(hacker_user)] == [dashboard.slug]


@pytest.mark.django_db
def test_list(test_user, hacker_user, root_user, dashboard):
    Dashboard.objects.create(
        slug="b-shared", name="B shared", owner=hacker_user, shared=True, data={}
    )
    Dashboard.objects.create(
        slug="a-private", name="A private", owner=hacker_user, data={}
    )
    result = service.list(test_user)
    assert [d["slug"] for d in result] == ["b-shared", dashboard.slug]
    assert "data" not in result[1]
    assert result[1]["tiles_count"] == 2
    assert result[0]["permissions"] == ["read"]
    assert [d["slug"] for d in service.list(root_user)] == [
        "a-private",
        "b-shared",
        dashboard.slug,
    ]


@pytest.mark.django_db
def test_create(test_user, clickhouse_source):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    result = service.create(
        test_user,
        {
            "name": "Prod overview",
            "description": "",
            "shared": False,
            "data": get_dashboard_data(),
        },
    )
    assert re.fullmatch(r"prod-overview-[0-9a-f]{6}", result["slug"])
    assert result["version"] == 1
    assert result["owner"]["username"] == "test_user"
    assert result["updated_by"]["username"] == "test_user"
    assert result["permissions"] == ["read", "edit", "delete"]


@pytest.mark.django_db
def test_create_needs_source_use(test_user, clickhouse_source):
    data = {"name": "D", "description": "", "shared": False}
    with pytest.raises(SerializerValidationError) as err:
        service.create(test_user, data | {"data": get_dashboard_data()})
    assert err.value.serializer.errors["data"]["tiles"][0]["chart"]["source"] == [
        "source clickhouse not found"
    ]
    assert not Dashboard.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("missing", ["name", "description", "shared", "data"])
def test_create_requires_fields(test_user, missing):
    data = {"name": "D", "description": "", "shared": False, "data": {}}
    del data[missing]
    with pytest.raises(SerializerValidationError) as err:
        service.create(test_user, data)
    assert missing in err.value.serializer.errors


@pytest.mark.django_db
def test_create_limit(test_user, dashboard):
    limits = dict(settings.CONFIG["limits"], max_dashboards_per_user=1)
    with override_settings(CONFIG=dict(settings.CONFIG, limits=limits)):
        data = get_dashboard_data()
        data["tiles"] = data["tiles"][1:]
        with pytest.raises(ValueError, match="maximum number of dashboards"):
            service.create(
                test_user,
                {"name": "D", "description": "", "shared": False, "data": data},
            )


@pytest.mark.django_db
def test_update(test_user, dashboard):
    result = service.update(
        test_user, dashboard.slug, payload(dashboard, name="Renamed", shared=True)
    )
    assert result["slug"] == dashboard.slug
    assert result["name"] == "Renamed"
    assert result["shared"] is True
    assert result["version"] == 2
    dashboard.refresh_from_db()
    assert dashboard.version == 2


@pytest.mark.django_db
def test_update_version_conflict(test_user, dashboard):
    service.update(test_user, dashboard.slug, payload(dashboard, name="First"))
    with pytest.raises(SerializerValidationError) as err:
        service.update(test_user, dashboard.slug, payload(dashboard, name="Second"))
    assert err.value.serializer.errors["version"] == [
        "Dashboard was changed elsewhere, reload it"
    ]
    dashboard.refresh_from_db()
    assert dashboard.name == "First"
    assert dashboard.version == 2


@pytest.mark.django_db
def test_update_requires_version(test_user, dashboard):
    data = payload(dashboard)
    del data["version"]
    with pytest.raises(SerializerValidationError) as err:
        service.update(test_user, dashboard.slug, data)
    assert "version" in err.value.serializer.errors


@pytest.mark.django_db
def test_update_keeps_tiles_of_lost_source(test_user, dashboard, docker_source):
    # test_user has no role on the clickhouse source the dashboard already uses.
    data = dict(dashboard.data)
    data["tiles"] = [dict(data["tiles"][0], x=6, w=18), data["tiles"][1]]
    service.update(test_user, dashboard.slug, payload(dashboard, data=data))

    dashboard.refresh_from_db()
    new_tile = dict(data["tiles"][0], id="t2", chart=dict(data["tiles"][0]["chart"]))
    new_tile["chart"]["source"] = docker_source.slug
    new_tile["chart"]["group_by"] = ""
    data["tiles"].append(new_tile)
    with pytest.raises(SerializerValidationError) as err:
        service.update(test_user, dashboard.slug, payload(dashboard, data=data))
    tiles = err.value.serializer.errors["data"]["tiles"]
    assert tiles == {2: {"chart": {"source": ["source docker not found"]}}}


@pytest.mark.django_db
def test_owner_deleted(root_user, test_user, dashboard):
    test_user.delete()
    result = service.get(root_user, dashboard.slug)
    assert result["owner"] is None
    assert result["updated_by"] is None


@pytest.mark.django_db
def test_update_keeps_stored_raw_query(test_user, clickhouse_source, dashboard):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    dashboard.data["tiles"][0]["chart"]["raw_query"] = "1 = 1"
    dashboard.save()
    data = dashboard.data
    data["tiles"][0]["x"] = 1
    result = service.update(test_user, dashboard.slug, payload(dashboard, data=data))
    assert result["data"]["tiles"][0]["chart"]["raw_query"] == "1 = 1"

    dashboard.refresh_from_db()
    data["tiles"][0]["chart"]["raw_query"] = "2 = 2"
    with pytest.raises(SerializerValidationError) as err:
        service.update(test_user, dashboard.slug, payload(dashboard, data=data))
    assert "raw_query" in str(err.value.serializer.errors)


@pytest.mark.django_db
def test_reader_sees_tiles_of_usable_sources(hacker_user, clickhouse_source, dashboard):
    share(dashboard)
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=hacker_user
    )
    result = service.get(hacker_user, dashboard.slug)
    assert result["data"]["tiles"][0]["chart"]["source"] == clickhouse_source.slug
