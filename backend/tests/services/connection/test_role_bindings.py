import pytest

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied

from telescope.rbac.roles import ConnectionRole
from telescope.rbac.manager import RBACManager
from telescope.services.connection import ConnectionService

rbac_manager = RBACManager()
connection_srv = ConnectionService()
from telescope.models import ConnectionRoleBinding


@pytest.mark.django_db
def test_grant_connection_role_to_user(test_user, docker_connection):
    binding, created = rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    assert created is True
    assert binding is not None
    assert ConnectionRoleBinding.objects.filter(
        user=test_user,
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
    ).exists()


@pytest.mark.django_db
def test_grant_connection_role_to_user_twice(test_user, docker_connection):
    # First grant
    binding1, created1 = rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    assert created1 is True

    # Second grant (should not create duplicate)
    binding2, created2 = rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    assert created2 is False
    assert binding2 is None


@pytest.mark.django_db
def test_grant_connection_role_to_group(docker_connection):
    group = Group.objects.create(name="test_group")

    binding, created = rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.EDITOR.value,
        group=group,
    )
    assert created is True
    assert binding is not None
    assert ConnectionRoleBinding.objects.filter(
        group=group,
        connection=docker_connection,
        role=ConnectionRole.EDITOR.value,
    ).exists()


@pytest.mark.django_db
def test_revoke_connection_role_from_user(test_user, docker_connection):
    # First grant a role
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )

    # Then revoke it
    deleted = rbac_manager.revoke_connection_role(
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    assert deleted is True
    assert not ConnectionRoleBinding.objects.filter(
        user=test_user,
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
    ).exists()


@pytest.mark.django_db
def test_revoke_connection_role_that_does_not_exist(test_user, docker_connection):
    # Try to revoke a role that was never granted
    deleted = rbac_manager.revoke_connection_role(
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    assert deleted is False


@pytest.mark.django_db
def test_revoke_connection_role_from_group(docker_connection):
    group = Group.objects.create(name="test_group")

    # First grant a role
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.EDITOR.value,
        group=group,
    )

    # Then revoke it
    deleted = rbac_manager.revoke_connection_role(
        connection=docker_connection,
        role=ConnectionRole.EDITOR.value,
        group=group,
    )
    assert deleted is True
    assert not ConnectionRoleBinding.objects.filter(
        group=group,
        connection=docker_connection,
        role=ConnectionRole.EDITOR.value,
    ).exists()


@pytest.mark.django_db
def test_multiple_roles_for_same_user(test_user, docker_connection):
    # Grant multiple roles to the same user
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
        user=test_user,
    )
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.EDITOR.value,
        user=test_user,
    )

    # Verify both bindings exist
    bindings = ConnectionRoleBinding.objects.filter(
        user=test_user, connection=docker_connection
    )
    assert bindings.count() == 2
    roles = set(b.role for b in bindings)
    assert ConnectionRole.VIEWER.value in roles
    assert ConnectionRole.EDITOR.value in roles


@pytest.mark.django_db
def test_grant_invalid_role(test_user, docker_connection):
    # Try to grant an invalid role
    with pytest.raises(ValueError, match="unknown connection role"):
        rbac_manager.grant_connection_role(
            connection=docker_connection,
            role="invalid_role",
            user=test_user,
        )


@pytest.mark.django_db
def test_grant_role_without_user_or_group(docker_connection):
    # Try to grant a role without specifying user or group
    with pytest.raises(ValueError, match="either user or group should be provided"):
        rbac_manager.grant_connection_role(
            connection=docker_connection,
            role=ConnectionRole.VIEWER.value,
        )


@pytest.mark.django_db
def test_get_role_bindings_with_grant_permission(docker_connection):
    # Create a user with OWNER role (has GRANT permission)
    owner = User.objects.create_user(username="owner", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.OWNER.value,
        user=owner,
    )

    # Create another user with VIEWER role
    viewer = User.objects.create_user(username="viewer", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
        user=viewer,
    )

    # Owner should be able to get role bindings
    bindings = connection_srv.get_role_bindings(user=owner, pk=docker_connection.pk)
    assert len(bindings) == 2

    # Check that both bindings are returned
    usernames = {b["user"]["username"] for b in bindings if b["user"]}
    assert "owner" in usernames
    assert "viewer" in usernames


@pytest.mark.django_db
def test_get_role_bindings_without_grant_permission(docker_connection):
    # Create a user with VIEWER role (does NOT have GRANT permission)
    viewer = User.objects.create_user(username="viewer_no_grant", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.VIEWER.value,
        user=viewer,
    )

    # Viewer should NOT be able to get role bindings
    with pytest.raises(PermissionDenied):
        connection_srv.get_role_bindings(user=viewer, pk=docker_connection.pk)


@pytest.mark.django_db
def test_get_role_bindings_with_editor_role(docker_connection):
    # Create a user with EDITOR role (does NOT have GRANT permission)
    editor = User.objects.create_user(username="editor_no_grant", password="pass")
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.EDITOR.value,
        user=editor,
    )

    # Editor should NOT be able to get role bindings (only OWNER has GRANT)
    with pytest.raises(PermissionDenied):
        connection_srv.get_role_bindings(user=editor, pk=docker_connection.pk)


@pytest.mark.django_db
def test_get_role_bindings_no_access_at_all(docker_connection):
    # Create a user with no roles on this connection
    no_access_user = User.objects.create_user(username="no_access", password="pass")

    # User with no access should NOT be able to get role bindings
    with pytest.raises(PermissionDenied):
        connection_srv.get_role_bindings(user=no_access_user, pk=docker_connection.pk)
