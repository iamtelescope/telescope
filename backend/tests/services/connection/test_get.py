import pytest

from telescope.models import Connection
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()
from telescope.rbac.roles import ConnectionRole


@pytest.mark.django_db
def test_get_connection(test_user, connection_service, docker_connection):
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.VIEWER.value, user=test_user
    )
    data = connection_service.get(user=test_user, pk=docker_connection.id)
    assert data["id"] == docker_connection.id
    assert data["kind"] == docker_connection.kind
    assert data["name"] == docker_connection.name
    assert data["data"]["address"] == docker_connection.data["address"]


@pytest.mark.django_db
def test_get_connection_with_superuser(
    root_user, connection_service, docker_connection
):
    data = connection_service.get(user=root_user, pk=docker_connection.id)
    assert data["id"] == docker_connection.id
    assert data["kind"] == docker_connection.kind
    assert data["name"] == docker_connection.name
    assert data["data"]["address"] == docker_connection.data["address"]


@pytest.mark.django_db
def test_get_clickhouse_connection(
    test_user, connection_service, clickhouse_connection
):
    rbac_manager.grant_connection_role(
        connection=clickhouse_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    data = connection_service.get(user=test_user, pk=clickhouse_connection.id)
    assert data["id"] == clickhouse_connection.id
    assert data["kind"] == clickhouse_connection.kind
    assert data["name"] == clickhouse_connection.name
    assert data["data"]["host"] == clickhouse_connection.data["host"]
    assert data["data"]["port"] == clickhouse_connection.data["port"]


@pytest.mark.django_db
def test_get_nonexistent_connection(root_user, connection_service):
    with pytest.raises(Connection.DoesNotExist):
        connection_service.get(user=root_user, pk=99999)


@pytest.mark.django_db
def test_get_kubernetes_connection(
    test_user, connection_service, kubernetes_connection
):
    rbac_manager.grant_connection_role(
        connection=kubernetes_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    data = connection_service.get(user=test_user, pk=kubernetes_connection.id)
    assert data["id"] == kubernetes_connection.id
    assert data["kind"] == kubernetes_connection.kind
    assert data["name"] == kubernetes_connection.name
    assert "kubeconfig" in data["data"]
    assert "kubeconfig_hash" in data["data"]
    assert "kubeconfig_is_local" in data["data"]
    assert data["data"]["kubeconfig_is_local"] is False


@pytest.mark.django_db
def test_get_kubernetes_connection_with_superuser(
    root_user, connection_service, kubernetes_connection
):
    data = connection_service.get(user=root_user, pk=kubernetes_connection.id)
    assert data["id"] == kubernetes_connection.id
    assert data["kind"] == kubernetes_connection.kind
    assert data["name"] == kubernetes_connection.name
    assert "kubeconfig" in data["data"]
    assert "kubeconfig_hash" in data["data"]
    assert "kubeconfig_is_local" in data["data"]
