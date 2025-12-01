"""
Comprehensive permission tests for Source CRUD operations.
Tests that permissions are properly enforced at the service layer.
"""

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from telescope.models import Source, SourceRoleBinding
from telescope.services.source import SourceService
from telescope.rbac.roles import SourceRole, GlobalRole, ConnectionRole
from telescope.rbac.manager import RBACManager
from tests.data import get_docker_source_data, get_kubernetes_source_data

rbac_manager = RBACManager()
source_srv = SourceService()


@pytest.mark.django_db
def test_create_source_without_global_permission(docker_connection):
    """User without CREATE_SOURCE global permission cannot create sources"""
    user = User.objects.create_user(username="no_perm_user", password="pass")

    # Grant USE on connection but no global permission
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.USER.value, user=user
    )

    data = get_docker_source_data("test-source")
    data["connection"] = {"connection_id": docker_connection.id}

    with pytest.raises(PermissionDenied):
        source_srv.create(user=user, data=data)


@pytest.mark.django_db
def test_create_source_without_connection_use_permission(docker_connection):
    """User without USE permission on connection cannot create source"""
    user = User.objects.create_user(username="no_use_user", password="pass")

    # Grant only CREATE_SOURCE global permission, not ADMIN (which includes USE_CONNECTION)
    rbac_manager.grant_global_role(role=GlobalRole.SOURCE_MANAGER.value, user=user)
    # VIEWER role has READ but no USE permission
    rbac_manager.grant_connection_role(
        connection=docker_connection, role=ConnectionRole.VIEWER.value, user=user
    )

    data = get_docker_source_data("test-source")
    data["connection"] = {"connection_id": docker_connection.id}

    with pytest.raises(PermissionDenied):
        source_srv.create(user=user, data=data)


@pytest.mark.django_db
def test_create_source_with_correct_permissions(docker_connection):
    """User with CREATE_SOURCE global and connection USE can create sources"""
    user = User.objects.create_user(username="creator", password="pass")

    # Grant both required permissions
    rbac_manager.grant_global_role(role=GlobalRole.ADMIN.value, user=user)
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.USER.value,  # USER has USE permission
        user=user,
    )

    data = get_docker_source_data("test-source")
    data["connection"] = {"connection_id": docker_connection.id}

    result = source_srv.create(user=user, data=data)
    assert result["slug"] == "test-source"

    # Verify creator gets OWNER role
    assert SourceRoleBinding.objects.filter(
        user=user, source__slug="test-source", role=SourceRole.OWNER.value
    ).exists()


@pytest.mark.django_db
def test_get_source_without_permission(docker_source):
    """User without READ permission cannot get source details"""
    user = User.objects.create_user(username="no_read_user", password="pass")

    with pytest.raises(Source.DoesNotExist):
        source_srv.get(user=user, slug=docker_source.slug)


@pytest.mark.django_db
def test_get_source_with_viewer_permission(docker_source):
    """User with VIEWER permission can get source details"""
    user = User.objects.create_user(username="viewer", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.VIEWER.value, user=user
    )

    result = source_srv.get(user=user, slug=docker_source.slug)
    assert result["slug"] == docker_source.slug
    assert result["name"] == docker_source.name
    # VIEWER should not see connection data
    assert "conn" not in result


@pytest.mark.django_db
def test_get_source_with_editor_permission(docker_source):
    """User with EDITOR permission gets source"""
    user = User.objects.create_user(username="editor", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.EDITOR.value, user=user
    )

    result = source_srv.get(user=user, slug=docker_source.slug)
    assert result["slug"] == docker_source.slug
    assert "conn" not in result
    assert result["connection_id"] == docker_source.conn_id


@pytest.mark.django_db
def test_get_source_with_user_permission(docker_source):
    """User with USER permission can get source (has READ)"""
    user = User.objects.create_user(username="user", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.USER.value, user=user
    )

    result = source_srv.get(user=user, slug=docker_source.slug)
    assert result["slug"] == docker_source.slug


@pytest.mark.django_db
def test_list_sources_without_permission(docker_source):
    """User without READ permission sees no sources"""
    user = User.objects.create_user(username="no_list_user", password="pass")

    result = source_srv.list(user=user)
    assert len(result) == 0


@pytest.mark.django_db
def test_list_sources_with_partial_permission(docker_source, clickhouse_source):
    """User sees only sources they have READ permission for"""
    user = User.objects.create_user(username="partial_user", password="pass")
    # Grant permission only on docker_source
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.VIEWER.value, user=user
    )

    result = source_srv.list(user=user)
    assert len(result) == 1
    assert result[0]["slug"] == docker_source.slug


@pytest.mark.django_db
def test_list_sources_with_different_roles(docker_source, clickhouse_source):
    """User with different roles sees all sources they have access to"""
    user = User.objects.create_user(username="multi_role_user", password="pass")

    # Different roles on different sources
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.OWNER.value, user=user
    )
    rbac_manager.grant_source_role(
        source=clickhouse_source, role=SourceRole.USER.value, user=user
    )

    result = source_srv.list(user=user)
    assert len(result) == 2
    slugs = {s["slug"] for s in result}
    assert docker_source.slug in slugs
    assert clickhouse_source.slug in slugs


@pytest.mark.django_db
def test_update_source_without_permission(docker_source):
    """User without EDIT permission cannot update source"""
    user = User.objects.create_user(username="no_edit_user", password="pass")

    data = {
        "name": "Updated Name",
        "description": "Updated",
        "fields": docker_source.fields,
    }

    with pytest.raises(PermissionDenied):
        source_srv.update(user=user, slug=docker_source.slug, data=data)


@pytest.mark.django_db
def test_update_source_with_viewer_permission(docker_source):
    """User with VIEWER permission cannot update source"""
    user = User.objects.create_user(username="viewer_no_edit", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.VIEWER.value, user=user
    )

    data = {
        "name": "Updated Name",
        "description": "Updated",
        "fields": docker_source.fields,
    }

    with pytest.raises(PermissionDenied):
        source_srv.update(user=user, slug=docker_source.slug, data=data)


@pytest.mark.django_db
def test_update_source_with_user_permission(docker_source):
    """User with USER permission cannot update source (no EDIT)"""
    user = User.objects.create_user(username="user_no_edit", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.USER.value, user=user
    )

    data = {
        "name": "Updated Name",
        "description": "Updated",
        "fields": docker_source.fields,
    }

    with pytest.raises(PermissionDenied):
        source_srv.update(user=user, slug=docker_source.slug, data=data)


@pytest.mark.django_db
def test_update_source_with_editor_permission(docker_source):
    """User with EDITOR permission can update source"""
    user = User.objects.create_user(username="editor", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.EDITOR.value, user=user
    )

    # Get complete source data for update
    data = get_docker_source_data(docker_source.slug)
    data["name"] = "Updated by Editor"
    data["description"] = "Editor update"

    result = source_srv.update(user=user, slug=docker_source.slug, data=data)
    assert "slug" in result

    # Verify update
    updated = Source.objects.get(slug=docker_source.slug)
    assert updated.name == "Updated by Editor"


@pytest.mark.django_db
def test_update_source_with_owner_permission(docker_source):
    """User with OWNER permission can update source"""
    user = User.objects.create_user(username="owner", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.OWNER.value, user=user
    )

    # Get complete source data for update
    data = get_docker_source_data(docker_source.slug)
    data["name"] = "Updated by Owner"
    data["description"] = "Owner update"

    result = source_srv.update(user=user, slug=docker_source.slug, data=data)
    assert "slug" in result

    # Verify update
    updated = Source.objects.get(slug=docker_source.slug)
    assert updated.name == "Updated by Owner"


@pytest.mark.django_db
def test_delete_source_without_permission(docker_source):
    """User without DELETE permission cannot delete source"""
    user = User.objects.create_user(username="no_delete_user", password="pass")

    with pytest.raises(PermissionDenied):
        source_srv.delete(user=user, slug=docker_source.slug)

    # Verify not deleted
    assert Source.objects.filter(slug=docker_source.slug).exists()


@pytest.mark.django_db
def test_delete_source_with_viewer_permission(docker_source):
    """User with VIEWER permission cannot delete source"""
    user = User.objects.create_user(username="viewer_no_delete", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.VIEWER.value, user=user
    )

    with pytest.raises(PermissionDenied):
        source_srv.delete(user=user, slug=docker_source.slug)

    # Verify not deleted
    assert Source.objects.filter(slug=docker_source.slug).exists()


@pytest.mark.django_db
def test_delete_source_with_user_permission(docker_source):
    """User with USER permission cannot delete source"""
    user = User.objects.create_user(username="user_no_delete", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.USER.value, user=user
    )

    with pytest.raises(PermissionDenied):
        source_srv.delete(user=user, slug=docker_source.slug)

    # Verify not deleted
    assert Source.objects.filter(slug=docker_source.slug).exists()


@pytest.mark.django_db
def test_delete_source_with_editor_permission(docker_source):
    """User with EDITOR permission can delete source"""
    user = User.objects.create_user(username="editor_delete", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.EDITOR.value, user=user
    )

    source_srv.delete(user=user, slug=docker_source.slug)

    # Verify deleted
    assert not Source.objects.filter(slug=docker_source.slug).exists()


@pytest.mark.django_db
def test_delete_source_with_owner_permission(docker_source):
    """User with OWNER permission can delete source"""
    user = User.objects.create_user(username="owner_delete", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.OWNER.value, user=user
    )

    source_srv.delete(user=user, slug=docker_source.slug)

    # Verify deleted
    assert not Source.objects.filter(slug=docker_source.slug).exists()


@pytest.mark.django_db
def test_owner_has_all_permissions(docker_source):
    """OWNER role includes all permissions"""
    user = User.objects.create_user(username="owner_all", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.OWNER.value, user=user
    )

    # Can READ
    read_result = source_srv.get(user=user, slug=docker_source.slug)
    assert read_result["slug"] == docker_source.slug

    # Can EDIT
    update_data = get_docker_source_data(docker_source.slug)
    update_data["name"] = "Owner Updated"
    update_data["description"] = "test"
    update_result = source_srv.update(
        user=user, slug=docker_source.slug, data=update_data
    )
    assert "slug" in update_result

    # Can get role bindings (GRANT)
    bindings = source_srv.get_role_bindings(user=user, slug=docker_source.slug)
    assert isinstance(bindings, list)

    # Can DELETE (tested last)
    source_srv.delete(user=user, slug=docker_source.slug)
    assert not Source.objects.filter(slug=docker_source.slug).exists()


@pytest.mark.django_db
def test_raw_query_user_permissions(docker_source):
    """RAW_QUERY_USER has specific permissions"""
    user = User.objects.create_user(username="raw_query", password="pass")
    rbac_manager.grant_source_role(
        source=docker_source, role=SourceRole.RAW_QUERY_USER.value, user=user
    )

    # Can READ
    read_result = source_srv.get(user=user, slug=docker_source.slug)
    assert read_result["slug"] == docker_source.slug

    # Cannot EDIT
    update_data = {
        "name": "Raw Query Update",
        "description": "test",
        "fields": docker_source.fields,
    }
    with pytest.raises(PermissionDenied):
        source_srv.update(user=user, slug=docker_source.slug, data=update_data)

    # Cannot DELETE
    with pytest.raises(PermissionDenied):
        source_srv.delete(user=user, slug=docker_source.slug)

    # Cannot get role bindings (no GRANT)
    with pytest.raises(PermissionDenied):
        source_srv.get_role_bindings(user=user, slug=docker_source.slug)


@pytest.mark.django_db
def test_permission_levels_hierarchy(docker_connection):
    """Test that permission levels work as expected: OWNER > EDITOR > USER > VIEWER"""
    docker_source = Source.objects.create(
        slug="perm-test",
        name="Permission Test",
        kind="docker",
        description="",
        time_field="time",
        date_field="",
        uniq_field="",
        severity_field="",
        fields={
            "time": {
                "type": "datetime",
                "display_name": "",
                "autocomplete": False,
                "suggest": True,
                "jsonstring": False,
                "group_by": False,
                "values": [],
            }
        },
        modifiers=[],
        default_chosen_fields="container_short_id, stream, message",
        support_raw_query=False,
        context_fields=[],
        conn=docker_connection,
        data={"address": "unix:///var/run/docker.sock"},
    )

    # Create users with different roles
    owner = User.objects.create_user(username="owner", password="pass")
    editor = User.objects.create_user(username="editor", password="pass")
    user_role = User.objects.create_user(username="user", password="pass")
    viewer = User.objects.create_user(username="viewer", password="pass")

    rbac_manager.grant_source_role(docker_source, SourceRole.OWNER.value, owner)
    rbac_manager.grant_source_role(docker_source, SourceRole.EDITOR.value, editor)
    rbac_manager.grant_source_role(docker_source, SourceRole.USER.value, user_role)
    rbac_manager.grant_source_role(docker_source, SourceRole.VIEWER.value, viewer)

    # All can READ
    for u in [owner, editor, user_role, viewer]:
        result = source_srv.get(user=u, slug=docker_source.slug)
        assert result["slug"] == docker_source.slug

    # Only OWNER and EDITOR can EDIT
    # Use the complete docker source data for updates
    from tests.data import get_docker_source_data

    for u in [owner, editor]:
        update_data = get_docker_source_data(docker_source.slug)
        update_data["name"] = f"Updated by {u.username}"
        update_data["description"] = "test update"
        result = source_srv.update(user=u, slug=docker_source.slug, data=update_data)
        assert "slug" in result

    for u in [user_role, viewer]:
        update_data = get_docker_source_data(docker_source.slug)
        update_data["name"] = "Should fail"
        with pytest.raises(PermissionDenied):
            source_srv.update(user=u, slug=docker_source.slug, data=update_data)

    # Only OWNER has GRANT
    bindings = source_srv.get_role_bindings(user=owner, slug=docker_source.slug)
    assert isinstance(bindings, list)

    for u in [editor, user_role, viewer]:
        with pytest.raises(PermissionDenied):
            source_srv.get_role_bindings(user=u, slug=docker_source.slug)


@pytest.mark.django_db
def test_create_kubernetes_source_without_global_permission(kubernetes_connection):
    """User without CREATE_SOURCE global permission cannot create kubernetes sources"""
    user = User.objects.create_user(username="no_perm_k8s_user", password="pass")

    # Grant USE on connection but no global permission
    rbac_manager.grant_connection_role(
        connection=kubernetes_connection, role=ConnectionRole.USER.value, user=user
    )

    data = get_kubernetes_source_data("test-k8s-source")
    data["connection"] = {"connection_id": kubernetes_connection.id}

    with pytest.raises(PermissionDenied):
        source_srv.create(user=user, data=data)


@pytest.mark.django_db
def test_create_kubernetes_source_without_connection_use_permission(kubernetes_connection):
    """User without USE permission on kubernetes connection cannot create source"""
    user = User.objects.create_user(username="no_use_k8s_user", password="pass")

    # Grant only CREATE_SOURCE global permission, not ADMIN (which includes USE_CONNECTION)
    rbac_manager.grant_global_role(role=GlobalRole.SOURCE_MANAGER.value, user=user)
    # VIEWER role has READ but no USE permission
    rbac_manager.grant_connection_role(
        connection=kubernetes_connection, role=ConnectionRole.VIEWER.value, user=user
    )

    data = get_kubernetes_source_data("test-k8s-source")
    data["connection"] = {"connection_id": kubernetes_connection.id}

    with pytest.raises(PermissionDenied):
        source_srv.create(user=user, data=data)


@pytest.mark.django_db
def test_create_kubernetes_source_with_correct_permissions(kubernetes_connection):
    """User with CREATE_SOURCE global and kubernetes connection USE can create sources"""
    user = User.objects.create_user(username="k8s_creator", password="pass")

    # Grant both required permissions
    rbac_manager.grant_global_role(role=GlobalRole.ADMIN.value, user=user)
    rbac_manager.grant_connection_role(
        connection=kubernetes_connection,
        role=ConnectionRole.USER.value,  # USER has USE permission
        user=user,
    )

    data = get_kubernetes_source_data("test-k8s-source")
    data["connection"] = {"connection_id": kubernetes_connection.id}

    result = source_srv.create(user=user, data=data)
    assert result["slug"] == "test-k8s-source"

    # Verify creator gets OWNER role
    assert SourceRoleBinding.objects.filter(
        user=user, source__slug="test-k8s-source", role=SourceRole.OWNER.value
    ).exists()


@pytest.mark.django_db
def test_get_kubernetes_source_without_permission(kubernetes_source):
    """User without READ permission cannot get kubernetes source details"""
    user = User.objects.create_user(username="no_read_k8s_user", password="pass")

    with pytest.raises(Source.DoesNotExist):
        source_srv.get(user=user, slug=kubernetes_source.slug)


@pytest.mark.django_db
def test_get_kubernetes_source_with_viewer_permission(kubernetes_source):
    """User with VIEWER permission can get kubernetes source details"""
    user = User.objects.create_user(username="k8s_viewer", password="pass")
    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.VIEWER.value, user=user
    )

    result = source_srv.get(user=user, slug=kubernetes_source.slug)
    assert result["slug"] == kubernetes_source.slug
    assert result["name"] == kubernetes_source.name
    # VIEWER should not see connection data
    assert "conn" not in result


@pytest.mark.django_db
def test_get_kubernetes_source_with_editor_permission(kubernetes_source):
    """User with EDITOR permission gets kubernetes source with connection data"""
    user = User.objects.create_user(username="k8s_editor", password="pass")
    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.EDITOR.value, user=user
    )

    result = source_srv.get(user=user, slug=kubernetes_source.slug)
    assert result["slug"] == kubernetes_source.slug
    assert "conn" not in result


@pytest.mark.django_db
def test_update_kubernetes_source_without_permission(kubernetes_source):
    """User without EDIT permission cannot update kubernetes source"""
    user = User.objects.create_user(username="no_edit_k8s_user", password="pass")

    data = {
        "name": "Updated Kubernetes Name",
        "description": "Updated",
        "fields": kubernetes_source.fields,
    }

    with pytest.raises(PermissionDenied):
        source_srv.update(user=user, slug=kubernetes_source.slug, data=data)


@pytest.mark.django_db
def test_update_kubernetes_source_with_viewer_permission(kubernetes_source):
    """User with VIEWER permission cannot update kubernetes source"""
    user = User.objects.create_user(username="k8s_viewer_no_edit", password="pass")
    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.VIEWER.value, user=user
    )

    data = {
        "name": "Updated Kubernetes Name",
        "description": "Updated",
        "fields": kubernetes_source.fields,
    }

    with pytest.raises(PermissionDenied):
        source_srv.update(user=user, slug=kubernetes_source.slug, data=data)


@pytest.mark.django_db
def test_update_kubernetes_source_with_editor_permission(kubernetes_source):
    """User with EDITOR permission can update kubernetes source"""
    user = User.objects.create_user(username="k8s_editor", password="pass")
    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.EDITOR.value, user=user
    )

    # Get complete source data for update
    data = get_kubernetes_source_data(kubernetes_source.slug)
    data["name"] = "Updated by Kubernetes Editor"
    data["description"] = "Kubernetes editor update"

    result = source_srv.update(user=user, slug=kubernetes_source.slug, data=data)
    assert "slug" in result

    # Verify update
    updated = Source.objects.get(slug=kubernetes_source.slug)
    assert updated.name == "Updated by Kubernetes Editor"


@pytest.mark.django_db
def test_delete_kubernetes_source_without_permission(kubernetes_source):
    """User without DELETE permission cannot delete kubernetes source"""
    user = User.objects.create_user(username="no_delete_k8s_user", password="pass")

    with pytest.raises(PermissionDenied):
        source_srv.delete(user=user, slug=kubernetes_source.slug)

    # Verify not deleted
    assert Source.objects.filter(slug=kubernetes_source.slug).exists()


@pytest.mark.django_db
def test_delete_kubernetes_source_with_viewer_permission(kubernetes_source):
    """User with VIEWER permission cannot delete kubernetes source"""
    user = User.objects.create_user(username="k8s_viewer_no_delete", password="pass")
    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.VIEWER.value, user=user
    )

    with pytest.raises(PermissionDenied):
        source_srv.delete(user=user, slug=kubernetes_source.slug)

    # Verify not deleted
    assert Source.objects.filter(slug=kubernetes_source.slug).exists()


@pytest.mark.django_db
def test_delete_kubernetes_source_with_editor_permission(kubernetes_source):
    """User with EDITOR permission can delete kubernetes source"""
    user = User.objects.create_user(username="k8s_editor_delete", password="pass")
    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.EDITOR.value, user=user
    )

    source_srv.delete(user=user, slug=kubernetes_source.slug)

    # Verify deleted
    assert not Source.objects.filter(slug=kubernetes_source.slug).exists()


@pytest.mark.django_db
def test_delete_kubernetes_source_with_owner_permission(kubernetes_source):
    """User with OWNER permission can delete kubernetes source"""
    user = User.objects.create_user(username="k8s_owner_delete", password="pass")
    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.OWNER.value, user=user
    )

    source_srv.delete(user=user, slug=kubernetes_source.slug)

    # Verify deleted
    assert not Source.objects.filter(slug=kubernetes_source.slug).exists()
