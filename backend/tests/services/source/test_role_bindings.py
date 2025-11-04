import pytest

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied

from telescope.rbac.roles import SourceRole
from telescope.rbac.manager import RBACManager
from telescope.services.source import SourceService

rbac_manager = RBACManager()
source_srv = SourceService()
from telescope.models import SourceRoleBinding


@pytest.mark.django_db
def test_grant_source_role_to_user(test_user, docker_source):
    binding, created = rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )
    assert created is True
    assert binding is not None
    assert SourceRoleBinding.objects.filter(
        user=test_user,
        source=docker_source,
        role=SourceRole.VIEWER.value,
    ).exists()


@pytest.mark.django_db
def test_grant_source_role_to_user_twice(test_user, docker_source):
    # First grant
    binding1, created1 = rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )
    assert created1 is True

    # Second grant (should not create duplicate)
    binding2, created2 = rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )
    assert created2 is False
    assert binding2 is None


@pytest.mark.django_db
def test_grant_source_role_to_group(docker_source):
    group = Group.objects.create(name="test_group")

    binding, created = rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.EDITOR.value,
        group=group,
    )
    assert created is True
    assert binding is not None
    assert SourceRoleBinding.objects.filter(
        group=group,
        source=docker_source,
        role=SourceRole.EDITOR.value,
    ).exists()


@pytest.mark.django_db
def test_revoke_source_role_from_user(test_user, docker_source):
    # First grant a role
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )

    # Then revoke it
    deleted = rbac_manager.revoke_source_role(
        source=docker_source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )
    assert deleted is True
    assert not SourceRoleBinding.objects.filter(
        user=test_user,
        source=docker_source,
        role=SourceRole.VIEWER.value,
    ).exists()


@pytest.mark.django_db
def test_revoke_source_role_that_does_not_exist(test_user, docker_source):
    # Try to revoke a role that was never granted
    deleted = rbac_manager.revoke_source_role(
        source=docker_source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )
    assert deleted is False


@pytest.mark.django_db
def test_revoke_source_role_from_group(docker_source):
    group = Group.objects.create(name="test_group")

    # First grant a role
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.EDITOR.value,
        group=group,
    )

    # Then revoke it
    deleted = rbac_manager.revoke_source_role(
        source=docker_source,
        role=SourceRole.EDITOR.value,
        group=group,
    )
    assert deleted is True
    assert not SourceRoleBinding.objects.filter(
        group=group,
        source=docker_source,
        role=SourceRole.EDITOR.value,
    ).exists()


@pytest.mark.django_db
def test_multiple_roles_for_same_user(test_user, docker_source):
    # Grant multiple roles to the same user
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.EDITOR.value,
        user=test_user,
    )

    # Verify both bindings exist
    bindings = SourceRoleBinding.objects.filter(user=test_user, source=docker_source)
    assert bindings.count() == 2
    roles = set(b.role for b in bindings)
    assert SourceRole.VIEWER.value in roles
    assert SourceRole.EDITOR.value in roles


@pytest.mark.django_db
def test_grant_invalid_role(test_user, docker_source):
    # Try to grant an invalid role
    with pytest.raises(ValueError, match="unknown source role"):
        rbac_manager.grant_source_role(
            source=docker_source,
            role="invalid_role",
            user=test_user,
        )


@pytest.mark.django_db
def test_grant_role_without_user_or_group(docker_source):
    # Try to grant a role without specifying user or group
    with pytest.raises(ValueError, match="either user or group should be provided"):
        rbac_manager.grant_source_role(
            source=docker_source,
            role=SourceRole.VIEWER.value,
        )


@pytest.mark.django_db
def test_grant_all_source_roles(test_user, docker_source):
    # Test all available source roles
    roles = [
        SourceRole.OWNER.value,
        SourceRole.EDITOR.value,
        SourceRole.VIEWER.value,
        SourceRole.USER.value,
        SourceRole.RAW_QUERY_USER.value,
    ]

    for role in roles:
        binding, created = rbac_manager.grant_source_role(
            source=docker_source,
            role=role,
            user=test_user,
        )
        assert created is True
        assert binding is not None

    # Verify all bindings exist
    bindings = SourceRoleBinding.objects.filter(user=test_user, source=docker_source)
    assert bindings.count() == len(roles)


@pytest.mark.django_db
def test_get_role_bindings_with_grant_permission(docker_source):
    # Create a user with OWNER role (has GRANT permission)
    owner = User.objects.create_user(username="source_owner", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.OWNER.value,
        user=owner,
    )

    # Create another user with VIEWER role
    viewer = User.objects.create_user(username="source_viewer", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.VIEWER.value,
        user=viewer,
    )

    # Owner should be able to get role bindings
    bindings = source_srv.get_role_bindings(user=owner, slug=docker_source.slug)
    assert len(bindings) == 2

    # Check that both bindings are returned
    usernames = {b["user"]["username"] for b in bindings if b["user"]}
    assert "source_owner" in usernames
    assert "source_viewer" in usernames


@pytest.mark.django_db
def test_get_role_bindings_without_grant_permission(docker_source):
    # Create a user with VIEWER role (does NOT have GRANT permission)
    viewer = User.objects.create_user(
        username="source_viewer_no_grant", password="pass"
    )
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.VIEWER.value,
        user=viewer,
    )

    # Viewer should NOT be able to get role bindings
    with pytest.raises(PermissionDenied):
        source_srv.get_role_bindings(user=viewer, slug=docker_source.slug)


@pytest.mark.django_db
def test_get_role_bindings_with_editor_role(docker_source):
    # Create a user with EDITOR role (does NOT have GRANT permission)
    editor = User.objects.create_user(
        username="source_editor_no_grant", password="pass"
    )
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.EDITOR.value,
        user=editor,
    )

    # Editor should NOT be able to get role bindings (only OWNER has GRANT)
    with pytest.raises(PermissionDenied):
        source_srv.get_role_bindings(user=editor, slug=docker_source.slug)


@pytest.mark.django_db
def test_get_role_bindings_with_user_role(docker_source):
    # Create a user with USER role (does NOT have GRANT permission)
    user = User.objects.create_user(username="source_user_no_grant", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.USER.value,
        user=user,
    )

    # USER role should NOT be able to get role bindings
    with pytest.raises(PermissionDenied):
        source_srv.get_role_bindings(user=user, slug=docker_source.slug)


@pytest.mark.django_db
def test_get_role_bindings_with_raw_query_user_role(docker_source):
    # Create a user with RAW_QUERY_USER role (does NOT have GRANT permission)
    raw_query_user = User.objects.create_user(
        username="source_raw_query", password="pass"
    )
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.RAW_QUERY_USER.value,
        user=raw_query_user,
    )

    # RAW_QUERY_USER should NOT be able to get role bindings
    with pytest.raises(PermissionDenied):
        source_srv.get_role_bindings(user=raw_query_user, slug=docker_source.slug)


@pytest.mark.django_db
def test_get_role_bindings_no_access_at_all(docker_source):
    # Create a user with no roles on this source
    no_access_user = User.objects.create_user(
        username="source_no_access", password="pass"
    )

    # User with no access should NOT be able to get role bindings
    with pytest.raises(PermissionDenied):
        source_srv.get_role_bindings(user=no_access_user, slug=docker_source.slug)
