import pytest

from telescope.models import Connection
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()
from telescope.rbac.roles import ConnectionRole


@pytest.mark.django_db
def test_delete_connection(test_user, connection_service, docker_connection):
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.OWNER.value, user=test_user
    )
    connection_id = docker_connection.id
    connection_service.delete(user=test_user, pk=connection_id)

    # Verify connection was deleted
    assert not Connection.objects.filter(pk=connection_id).exists()


@pytest.mark.django_db
def test_delete_connection_with_superuser(
    root_user, connection_service, docker_connection
):
    connection_id = docker_connection.id
    connection_service.delete(user=root_user, pk=connection_id)

    # Verify connection was deleted
    assert not Connection.objects.filter(pk=connection_id).exists()


@pytest.mark.django_db
def test_delete_nonexistent_connection(root_user, connection_service):
    with pytest.raises(Connection.DoesNotExist):
        connection_service.delete(user=root_user, pk=99999)
