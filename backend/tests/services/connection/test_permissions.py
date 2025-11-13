"""
Comprehensive permission tests for Connection CRUD operations.
Tests that permissions are properly enforced at the service layer.
"""

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from telescope.models import Connection, ConnectionRoleBinding
from telescope.services.connection import ConnectionService
from telescope.rbac.roles import ConnectionRole, GlobalRole
from telescope.rbac.manager import RBACManager
from tests.data import get_docker_connection_data, get_clickhouse_connection_data, get_kubernetes_connection_data

rbac_manager = RBACManager()
connection_srv = ConnectionService()


@pytest.mark.django_db
def test_create_connection_without_global_permission():
    """User without CREATE_CONNECTION global permission cannot create connections"""
    user = User.objects.create_user(username="no_perm_user", password="pass")

    data = get_docker_connection_data()

    with pytest.raises(PermissionDenied):
        connection_srv.create(user=user, data=data)


@pytest.mark.django_db
def test_create_connection_with_wrong_global_permission():
    """User with wrong global permission cannot create connections"""
    user = User.objects.create_user(username="wrong_perm_user", password="pass")
    # Grant a different global role that doesn't include CREATE_CONNECTION
    rbac_manager.grant_global_role(role=GlobalRole.SOURCE_MANAGER.value, user=user)

    data = get_docker_connection_data()

    with pytest.raises(PermissionDenied):
        connection_srv.create(user=user, data=data)


@pytest.mark.django_db
def test_create_connection_with_correct_permission():
    """User with CONNECTION_MANAGER role can create connections"""
    user = User.objects.create_user(username="conn_manager", password="pass")
    rbac_manager.grant_global_role(role=GlobalRole.CONNECTION_MANAGER.value, user=user)

    data = get_docker_connection_data()
    result = connection_srv.create(user=user, data=data)

    assert "id" in result
    assert Connection.objects.filter(pk=result["id"]).exists()

    # Verify creator gets OWNER role
    assert ConnectionRoleBinding.objects.filter(
        user=user, connection_id=result["id"], role=ConnectionRole.OWNER.value
    ).exists()


@pytest.mark.django_db
def test_create_connection_with_admin_permission():
    """User with ADMIN role can create connections"""
    user = User.objects.create_user(username="admin_user", password="pass")
    rbac_manager.grant_global_role(role=GlobalRole.ADMIN.value, user=user)

    data = get_clickhouse_connection_data()
    result = connection_srv.create(user=user, data=data)

    assert "id" in result
    assert Connection.objects.filter(pk=result["id"]).exists()


@pytest.mark.django_db
def test_create_kubernetes_connection_with_correct_permission():
    """User with CONNECTION_MANAGER role can create kubernetes connections"""
    user = User.objects.create_user(username="k8s_conn_manager", password="pass")
    rbac_manager.grant_global_role(role=GlobalRole.CONNECTION_MANAGER.value, user=user)

    data = get_kubernetes_connection_data()
    result = connection_srv.create(user=user, data=data)

    assert "id" in result
    assert Connection.objects.filter(pk=result["id"]).exists()

    # Verify creator gets OWNER role
    assert ConnectionRoleBinding.objects.filter(
        user=user, connection_id=result["id"], role=ConnectionRole.OWNER.value
    ).exists()


@pytest.mark.django_db
def test_get_connection_without_permission(docker_connection):
    """User without READ permission cannot get connection details"""
    user = User.objects.create_user(username="no_read_user", password="pass")

    with pytest.raises((PermissionDenied, Connection.DoesNotExist)):
        connection_srv.get(user=user, pk=docker_connection.pk)


@pytest.mark.django_db
def test_get_connection_with_viewer_permission(docker_connection):
    """User with VIEWER permission can get connection details"""
    user = User.objects.create_user(username="viewer", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.VIEWER.value, user=user
    )

    result = connection_srv.get(user=user, pk=docker_connection.pk)
    assert result["id"] == docker_connection.pk
    assert result["name"] == docker_connection.name


@pytest.mark.django_db
def test_get_connection_with_user_permission(docker_connection):
    """User with USER permission can get connection details (has READ)"""
    user = User.objects.create_user(username="user", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.USER.value, user=user
    )

    result = connection_srv.get(user=user, pk=docker_connection.pk)
    assert result["id"] == docker_connection.pk


@pytest.mark.django_db
def test_get_nonexistent_connection():
    """Getting non-existent connection raises appropriate error"""
    user = User.objects.create_user(username="admin", password="pass")
    rbac_manager.grant_global_role(role=GlobalRole.ADMIN.value, user=user)

    with pytest.raises(Connection.DoesNotExist):
        connection_srv.get(user=user, pk=99999)


@pytest.mark.django_db
def test_list_connections_without_permission(docker_connection, clickhouse_connection):
    """User without READ permission sees no connections"""
    user = User.objects.create_user(username="no_list_user", password="pass")

    result = connection_srv.list(user=user)
    assert len(result) == 0


@pytest.mark.django_db
def test_list_connections_with_partial_permission(
    docker_connection, clickhouse_connection, kubernetes_connection
):
    """User sees only connections they have READ permission for"""
    user = User.objects.create_user(username="partial_user", password="pass")
    # Grant permission only on docker_connection
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.VIEWER.value, user=user
    )

    result = connection_srv.list(user=user)
    assert len(result) == 1
    assert result[0]["id"] == docker_connection.pk


@pytest.mark.django_db
def test_list_usable_connections(docker_connection, clickhouse_connection, kubernetes_connection):
    """list_usable returns only connections with USE permission"""
    user = User.objects.create_user(username="use_user", password="pass")
    # Grant USER role on docker (has USE), VIEWER on clickhouse and kubernetes (no USE)
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.USER.value, user=user
    )
    rbac_manager.grant_connection_role(
        connection=clickhouse_connection, role=ConnectionRole.VIEWER.value, user=user
    )
    rbac_manager.grant_connection_role(
        connection=kubernetes_connection, role=ConnectionRole.VIEWER.value, user=user
    )

    result = connection_srv.list_usable(user=user)
    assert len(result) == 1
    assert result[0]["id"] == docker_connection.pk


@pytest.mark.django_db
def test_update_connection_without_permission(docker_connection):
    """User without EDIT permission cannot update connection"""
    user = User.objects.create_user(username="no_edit_user", password="pass")

    data = {
        "kind": "docker",
        "name": "Updated Name",
        "description": "Updated",
        "data": docker_connection.data,
    }

    with pytest.raises(PermissionDenied):
        connection_srv.update(user=user, pk=docker_connection.pk, data=data)


@pytest.mark.django_db
def test_update_connection_with_viewer_permission(docker_connection):
    """User with VIEWER permission cannot update connection (no EDIT)"""
    user = User.objects.create_user(username="viewer_no_edit", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.VIEWER.value, user=user
    )

    data = {
        "kind": "docker",
        "name": "Updated Name",
        "description": "Updated",
        "data": docker_connection.data,
    }

    with pytest.raises(PermissionDenied):
        connection_srv.update(user=user, pk=docker_connection.pk, data=data)


@pytest.mark.django_db
def test_update_connection_with_editor_permission(docker_connection):
    """User with EDITOR permission can update connection"""
    user = User.objects.create_user(username="editor", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.EDITOR.value, user=user
    )

    data = {
        "kind": "docker",
        "name": "Updated by Editor",
        "description": "Editor update",
        "data": docker_connection.data,
    }

    result = connection_srv.update(user=user, pk=docker_connection.pk, data=data)
    assert "id" in result

    # Verify update
    updated = Connection.objects.get(pk=docker_connection.pk)
    assert updated.name == "Updated by Editor"


@pytest.mark.django_db
def test_update_connection_with_owner_permission(docker_connection):
    """User with OWNER permission can update connection"""
    user = User.objects.create_user(username="owner", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.OWNER.value, user=user
    )

    data = {
        "kind": "docker",
        "name": "Updated by Owner",
        "description": "Owner update",
        "data": docker_connection.data,
    }

    result = connection_srv.update(user=user, pk=docker_connection.pk, data=data)
    assert "id" in result

    # Verify update
    updated = Connection.objects.get(pk=docker_connection.pk)
    assert updated.name == "Updated by Owner"


@pytest.mark.django_db
def test_delete_connection_without_permission(docker_connection):
    """User without DELETE permission cannot delete connection"""
    user = User.objects.create_user(username="no_delete_user", password="pass")

    with pytest.raises(PermissionDenied):
        connection_srv.delete(user=user, pk=docker_connection.pk)

    # Verify not deleted
    assert Connection.objects.filter(pk=docker_connection.pk).exists()


@pytest.mark.django_db
def test_delete_connection_with_viewer_permission(docker_connection):
    """User with VIEWER permission cannot delete connection"""
    user = User.objects.create_user(username="viewer_no_delete", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.VIEWER.value, user=user
    )

    with pytest.raises(PermissionDenied):
        connection_srv.delete(user=user, pk=docker_connection.pk)

    # Verify not deleted
    assert Connection.objects.filter(pk=docker_connection.pk).exists()


@pytest.mark.django_db
def test_delete_connection_with_user_permission(docker_connection):
    """User with USER permission cannot delete connection (no DELETE)"""
    user = User.objects.create_user(username="user_no_delete", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.USER.value, user=user
    )

    with pytest.raises(PermissionDenied):
        connection_srv.delete(user=user, pk=docker_connection.pk)

    # Verify not deleted
    assert Connection.objects.filter(pk=docker_connection.pk).exists()


@pytest.mark.django_db
def test_delete_connection_with_editor_permission(docker_connection):
    """User with EDITOR permission can delete connection"""
    user = User.objects.create_user(username="editor_delete", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.EDITOR.value, user=user
    )

    connection_srv.delete(user=user, pk=docker_connection.pk)

    # Verify deleted
    assert not Connection.objects.filter(pk=docker_connection.pk).exists()


@pytest.mark.django_db
def test_delete_connection_with_owner_permission(docker_connection):
    """User with OWNER permission can delete connection"""
    user = User.objects.create_user(username="owner_delete", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.OWNER.value, user=user
    )

    connection_srv.delete(user=user, pk=docker_connection.pk)

    # Verify deleted
    assert not Connection.objects.filter(pk=docker_connection.pk).exists()


@pytest.mark.django_db
def test_owner_has_all_permissions(docker_connection):
    """OWNER role includes all permissions"""
    user = User.objects.create_user(username="owner_all", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.OWNER.value, user=user
    )

    # Can READ
    read_result = connection_srv.get(user=user, pk=docker_connection.pk)
    assert read_result["id"] == docker_connection.pk

    # Can EDIT
    update_data = {
        "kind": "docker",
        "name": "Owner Updated",
        "description": "test",
        "data": docker_connection.data,
    }
    update_result = connection_srv.update(
        user=user, pk=docker_connection.pk, data=update_data
    )
    assert "id" in update_result

    # Can get role bindings (GRANT)
    bindings = connection_srv.get_role_bindings(user=user, pk=docker_connection.pk)
    assert isinstance(bindings, list)

    # Can DELETE (tested last)
    connection_srv.delete(user=user, pk=docker_connection.pk)
    assert not Connection.objects.filter(pk=docker_connection.pk).exists()


@pytest.mark.django_db
def test_editor_has_limited_permissions(docker_connection):
    """EDITOR role has READ, EDIT, DELETE but not GRANT"""
    user = User.objects.create_user(username="editor_limited", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.EDITOR.value, user=user
    )

    # Can READ
    read_result = connection_srv.get(user=user, pk=docker_connection.pk)
    assert read_result["id"] == docker_connection.pk

    # Can EDIT
    update_data = {
        "kind": "docker",
        "name": "Editor Updated",
        "description": "test",
        "data": docker_connection.data,
    }
    update_result = connection_srv.update(
        user=user, pk=docker_connection.pk, data=update_data
    )
    assert "id" in update_result

    # Cannot GRANT (no GRANT permission)
    with pytest.raises(PermissionDenied):
        connection_srv.get_role_bindings(user=user, pk=docker_connection.pk)

    # Can DELETE
    connection_srv.delete(user=user, pk=docker_connection.pk)
    assert not Connection.objects.filter(pk=docker_connection.pk).exists()
