import pytest

from telescope.rbac.roles import SourceRole
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()
from telescope.models import Source


@pytest.mark.django_db
def test_get_source(test_user, service, docker_source):
    with pytest.raises(Source.DoesNotExist):
        service.get(user=test_user, slug=docker_source.slug)

    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.VIEWER.value, user=test_user
    )
    data = service.get(user=test_user, slug=docker_source.slug)
    assert data["slug"] == docker_source.slug
    assert "connection" not in data
    assert data["connection_id"] == docker_source.conn_id

    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.EDITOR.value, user=test_user
    )
    data = service.get(user=test_user, slug=docker_source.slug)
    assert data["slug"] == docker_source.slug
    assert "conn" not in data
    assert data["connection_id"] == docker_source.conn_id


@pytest.mark.django_db
def test_get_source_with_full_permissions(root_user, service, docker_source):
    data = service.get(user=root_user, slug=docker_source.slug)
    assert data["slug"] == docker_source.slug
    assert "conn" not in data
    assert data["connection_id"] == docker_source.conn_id


@pytest.mark.django_db
def test_get_kubernetes_source(test_user, service, kubernetes_source):
    with pytest.raises(Source.DoesNotExist):
        service.get(user=test_user, slug=kubernetes_source.slug)

    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.VIEWER.value, user=test_user
    )
    data = service.get(user=test_user, slug=kubernetes_source.slug)
    assert data["slug"] == kubernetes_source.slug
    assert "connection" not in data
    assert data["connection_id"] == kubernetes_source.conn_id

    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.EDITOR.value, user=test_user
    )
    data = service.get(user=test_user, slug=kubernetes_source.slug)
    assert data["slug"] == kubernetes_source.slug
    assert "mode" in data["conn"]["data"]
    assert data["connection_id"] == kubernetes_source.conn_id


@pytest.mark.django_db
def test_get_kubernetes_source_with_full_permissions(root_user, service, kubernetes_source):
    data = service.get(user=root_user, slug=kubernetes_source.slug)
    assert data["slug"] == kubernetes_source.slug
    assert "mode" in data["conn"]["data"]
    assert data["connection_id"] == kubernetes_source.conn_id
