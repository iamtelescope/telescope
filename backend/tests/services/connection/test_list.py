import pytest

from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()
from telescope.rbac.roles import ConnectionRole


@pytest.mark.django_db
def test_list_connections_empty(test_user, connection_service):
    data = connection_service.list(user=test_user)
    assert len(data) == 0


@pytest.mark.django_db
def test_list_connections(
    test_user,
    connection_service,
    docker_connection,
    clickhouse_connection,
    kubernetes_connection,
):
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.VIEWER.value, user=test_user
    )
    rbac_manager.grant_connection_role(
        connection=clickhouse_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    rbac_manager.grant_connection_role(
        connection=kubernetes_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    data = connection_service.list(user=test_user)
    assert len(data) == 3

    # Find docker connection in results
    docker_conn = next((c for c in data if c["kind"] == "docker"), None)
    assert docker_conn is not None
    assert docker_conn["id"] == docker_connection.id
    assert docker_conn["name"] == docker_connection.name

    # Find clickhouse connection in results
    ch_conn = next((c for c in data if c["kind"] == "clickhouse"), None)
    assert ch_conn is not None
    assert ch_conn["id"] == clickhouse_connection.id
    assert ch_conn["name"] == clickhouse_connection.name

    # Find kubernetes connection in results
    k8s_conn = next((c for c in data if c["kind"] == "kubernetes"), None)
    assert k8s_conn is not None
    assert k8s_conn["id"] == kubernetes_connection.id
    assert k8s_conn["name"] == kubernetes_connection.name


@pytest.mark.django_db
def test_list_connections_with_superuser(
    root_user, connection_service, docker_connection, kubernetes_connection
):
    data = connection_service.list(user=root_user)
    assert len(data) == 2
    assert data[0]["id"] == docker_connection.id
    assert data[0]["kind"] == "docker"
    assert data[1]["id"] == kubernetes_connection.id
    assert data[1]["kind"] == "kubernetes"


@pytest.mark.django_db
def test_list_connections_does_not_return_data_field(
    test_user,
    connection_service,
    docker_connection,
    clickhouse_connection,
    kubernetes_connection,
):
    """Test that list does not return sensitive connection data"""
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.VIEWER.value, user=test_user
    )
    rbac_manager.grant_connection_role(
        connection=clickhouse_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    rbac_manager.grant_connection_role(
        connection=kubernetes_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    data = connection_service.list(user=test_user)
    assert len(data) == 3

    # Check that 'data' field is NOT present in any connection
    for conn in data:
        assert (
            "data" not in conn
        ), "List should not return 'data' field with sensitive information"

        # Verify other fields are present
        assert "id" in conn
        assert "kind" in conn
        assert "name" in conn
        assert "description" in conn


@pytest.mark.django_db
def test_list_connections_excludes_sensitive_data(
    root_user, connection_service, clickhouse_connection, kubernetes_connection
):
    """Test that list does not expose sensitive connection credentials"""
    data = connection_service.list(user=root_user)

    ch_conn = next((c for c in data if c["kind"] == "clickhouse"), None)
    assert ch_conn is not None

    k8s_conn = next((c for c in data if c["kind"] == "kubernetes"), None)
    assert k8s_conn is not None

    # Verify sensitive data is NOT exposed for clickhouse
    assert "data" not in ch_conn
    # If data was present, it would contain: host, port, password, ssl, etc.
    # Ensure none of these sensitive fields leak into the response directly
    assert "password" not in ch_conn
    assert "host" not in ch_conn
    assert "address" not in ch_conn

    # Verify sensitive data is NOT exposed for kubernetes
    assert "data" not in k8s_conn
    # If data was present, it would contain: kubeconfig, namespace, etc.
    # Ensure none of these sensitive fields leak into the response directly
    assert "kubeconfig" not in k8s_conn
    assert "namespace" not in k8s_conn
