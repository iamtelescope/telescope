import pytest

from telescope.models import Connection
from telescope.services.exceptions import SerializerValidationError
from telescope.serializers.connection import (
    ConnectionSerializer,
    ClickhouseConnectionSerializer,
    KubernetesConnectionSerializer,
)
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()
from telescope.rbac.roles import GlobalRole

from tests.data import (
    get_docker_connection_data,
    get_clickhouse_connection_data,
    get_kubernetes_connection_data,
)


@pytest.mark.django_db
def test_create_docker_connection(test_user, connection_service):
    rbac_manager.grant_global_role(
        role=GlobalRole.CONNECTION_MANAGER.value, user=test_user
    )
    data = get_docker_connection_data()
    result = connection_service.create(user=test_user, data=data)
    assert "id" in result
    assert result["id"] > 0

    # Verify connection was created
    conn = Connection.objects.get(pk=result["id"])
    assert conn.kind == "docker"
    assert conn.name == "Docker Connection"
    assert conn.data["address"] == "unix:///var/run/docker.sock"


@pytest.mark.django_db
def test_create_clickhouse_connection(test_user, connection_service):
    rbac_manager.grant_global_role(
        role=GlobalRole.CONNECTION_MANAGER.value, user=test_user
    )
    data = get_clickhouse_connection_data()
    result = connection_service.create(user=test_user, data=data)
    assert "id" in result
    assert result["id"] > 0

    # Verify connection was created
    conn = Connection.objects.get(pk=result["id"])
    assert conn.kind == "clickhouse"
    assert conn.name == "ClickHouse Connection"
    assert conn.data["host"] == "localhost"
    assert conn.data["port"] == 9440


@pytest.mark.django_db
def test_create_connection_with_invalid_kind(root_user, connection_service):
    data = get_docker_connection_data()
    data["kind"] = "invalid_kind"
    with pytest.raises(SerializerValidationError) as err:
        connection_service.create(user=root_user, data=data)
    assert isinstance(err.value.serializer, ConnectionSerializer)
    assert "kind" in err.value.serializer.errors


@pytest.mark.django_db
def test_create_connection_with_missing_name(root_user, connection_service):
    data = get_docker_connection_data()
    del data["name"]
    with pytest.raises(SerializerValidationError) as err:
        connection_service.create(user=root_user, data=data)
    assert isinstance(err.value.serializer, ConnectionSerializer)
    assert "name" in err.value.serializer.errors


@pytest.mark.django_db
def test_create_connection_with_invalid_docker_data(root_user, connection_service):
    data = get_docker_connection_data()
    del data["data"]["address"]
    with pytest.raises(SerializerValidationError) as err:
        connection_service.create(user=root_user, data=data)
    # The error should be from the DockerConnectionSerializer


@pytest.mark.django_db
def test_create_connection_with_invalid_clickhouse_data(root_user, connection_service):
    data = get_clickhouse_connection_data()
    del data["data"]["host"]
    with pytest.raises(SerializerValidationError) as err:
        connection_service.create(user=root_user, data=data)
    assert isinstance(err.value.serializer, ClickhouseConnectionSerializer)


@pytest.mark.django_db
def test_create_kubernetes_connection(test_user, connection_service):
    rbac_manager.grant_global_role(
        role=GlobalRole.CONNECTION_MANAGER.value, user=test_user
    )
    data = get_kubernetes_connection_data()
    result = connection_service.create(user=test_user, data=data)
    assert "id" in result
    assert result["id"] > 0

    conn = Connection.objects.get(pk=result["id"])
    assert conn.kind == "kubernetes"
    assert conn.name == "Kubernetes Connection"
    assert "kubeconfig" in conn.data
    assert "kubeconfig_hash" in conn.data
    assert "kubeconfig_is_local" in conn.data
    assert conn.data["kubeconfig_is_local"] is False


@pytest.mark.django_db
def test_create_connection_with_invalid_kubernetes_data(root_user, connection_service):
    data = get_kubernetes_connection_data()
    del data["data"]["kubeconfig"]
    with pytest.raises(SerializerValidationError) as err:
        connection_service.create(user=root_user, data=data)
    assert isinstance(err.value.serializer, KubernetesConnectionSerializer)
