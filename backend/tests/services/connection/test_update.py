import pytest

from telescope.models import Connection
from telescope.services.exceptions import SerializerValidationError
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()
from telescope.rbac.roles import ConnectionRole

from tests.data import (
    get_docker_connection_data,
    get_clickhouse_connection_data,
    get_kubernetes_connection_data,
)


@pytest.mark.django_db
def test_update_docker_connection(test_user, connection_service, docker_connection):
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.EDITOR.value, user=test_user
    )
    data = get_docker_connection_data()
    data["name"] = "Updated Docker Connection"
    data["description"] = "updated description"
    data["data"]["address"] = "tcp://localhost:2375"

    result = connection_service.update(
        user=test_user, pk=docker_connection.id, data=data
    )
    assert result["id"] == docker_connection.id

    # Verify connection was updated
    conn = Connection.objects.get(pk=docker_connection.id)
    assert conn.name == "Updated Docker Connection"
    assert conn.description == "updated description"
    assert conn.data["address"] == "tcp://localhost:2375"


@pytest.mark.django_db
def test_update_clickhouse_connection(
    test_user, connection_service, clickhouse_connection
):
    rbac_manager.grant_connection_role(
        connection=clickhouse_connection,
        role=ConnectionRole.EDITOR.value,
        user=test_user,
    )
    data = get_clickhouse_connection_data()
    data["name"] = "Updated ClickHouse Connection"
    data["data"]["host"] = "newhost.example.com"
    data["data"]["port"] = 9441

    result = connection_service.update(
        user=test_user, pk=clickhouse_connection.id, data=data
    )
    assert result["id"] == clickhouse_connection.id

    # Verify connection was updated
    conn = Connection.objects.get(pk=clickhouse_connection.id)
    assert conn.name == "Updated ClickHouse Connection"
    assert conn.data["host"] == "newhost.example.com"
    assert conn.data["port"] == 9441


@pytest.mark.django_db
def test_update_connection_with_invalid_data(
    test_user, connection_service, docker_connection
):
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.EDITOR.value, user=test_user
    )
    data = get_docker_connection_data()
    data["kind"] = "invalid_kind"

    with pytest.raises(SerializerValidationError):
        connection_service.update(user=test_user, pk=docker_connection.id, data=data)


@pytest.mark.django_db
def test_update_nonexistent_connection(root_user, connection_service):
    data = get_docker_connection_data()
    with pytest.raises(Connection.DoesNotExist):
        connection_service.update(user=root_user, pk=99999, data=data)


@pytest.mark.django_db
def test_update_kubernetes_connection(
    test_user, connection_service, kubernetes_connection
):
    rbac_manager.grant_connection_role(
        connection=kubernetes_connection,
        role=ConnectionRole.EDITOR.value,
        user=test_user,
    )
    data = get_kubernetes_connection_data()
    data["name"] = "Updated Kubernetes Connection"
    data["description"] = "updated description"
    data["data"]["host"] = "https://new-k8s.example.com"

    result = connection_service.update(
        user=test_user, pk=kubernetes_connection.id, data=data
    )
    assert result["id"] == kubernetes_connection.id

    # Verify connection was updated
    conn = Connection.objects.get(pk=kubernetes_connection.id)
    assert conn.name == "Updated Kubernetes Connection"
    assert conn.description == "updated description"
    assert conn.data["host"] == "https://new-k8s.example.com"
