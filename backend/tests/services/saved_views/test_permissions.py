"""
Comprehensive permission tests for SavedView operations.
Tests all permission levels and edge cases.
"""

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from telescope.constants import VIEW_SCOPE_PERSONAL, VIEW_SCOPE_SOURCE
from telescope.models import SavedView, Source
from telescope.services.source import SourceSavedViewService
from telescope.rbac.roles import SourceRole
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()


@pytest.mark.django_db
def test_create_personal_view_no_source_access(docker_source):
    """User with NO permissions on source cannot create personal view"""
    user_no_access = User.objects.create_user(username="no_access", password="pass")

    data = {
        "scope": VIEW_SCOPE_PERSONAL,
        "name": "My View",
        "description": "desc",
        "shared": False,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=docker_source.slug)
    with pytest.raises(PermissionDenied):
        service.create(user=user_no_access, slug=docker_source.slug, data=data)


@pytest.mark.django_db
def test_create_personal_view_with_use_permission_only(test_user, docker_source):
    """User with only USE permission cannot create personal view (needs READ)"""
    rbac_manager.grant_source_role(docker_source, SourceRole.USER.value, user=test_user)

    data = {
        "scope": VIEW_SCOPE_PERSONAL,
        "name": "My View",
        "description": "desc",
        "shared": False,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=docker_source.slug)
    # USER role has both USE and READ, so this should work
    result = service.create(user=test_user, slug=docker_source.slug, data=data)
    assert result["name"] == "My View"


@pytest.mark.django_db
def test_create_source_view_with_owner_permission(test_user, docker_source):
    """User with OWNER permission can create source-scope view"""
    rbac_manager.grant_source_role(
        docker_source, SourceRole.OWNER.value, user=test_user
    )

    data = {
        "scope": VIEW_SCOPE_SOURCE,
        "name": "Owner View",
        "description": "desc",
        "shared": True,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=docker_source.slug)
    result = service.create(user=test_user, slug=docker_source.slug, data=data)
    assert result["name"] == "Owner View"
    assert result["scope"] == VIEW_SCOPE_SOURCE


@pytest.mark.django_db
def test_create_source_view_with_viewer_permission(test_user, docker_source):
    """User with VIEWER permission cannot create source-scope view (needs EDIT)"""
    rbac_manager.grant_source_role(
        docker_source, SourceRole.VIEWER.value, user=test_user
    )

    data = {
        "scope": VIEW_SCOPE_SOURCE,
        "name": "Viewer Attempt",
        "description": "should fail",
        "shared": True,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=docker_source.slug)
    with pytest.raises(PermissionDenied):
        service.create(user=test_user, slug=docker_source.slug, data=data)


@pytest.mark.django_db
def test_delete_personal_view_owner_no_source_access(personal_saved_view):
    """Owner of personal view cannot delete it without READ permission on source"""
    # personal_saved_view.user owns the view but has no permissions on source

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)
    with pytest.raises(Source.DoesNotExist):
        service.delete(
            user=personal_saved_view.user, view_slug=personal_saved_view.slug
        )


@pytest.mark.django_db
def test_delete_source_view_with_owner_permission(source_saved_view, test_user):
    """User with OWNER permission can delete source-scope view"""
    rbac_manager.grant_source_role(
        source=source_saved_view.source,
        role=SourceRole.OWNER.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=source_saved_view.source.slug)
    service.delete(user=test_user, view_slug=source_saved_view.slug)

    assert not SavedView.objects.filter(pk=source_saved_view.pk).exists()


@pytest.mark.django_db
def test_delete_any_view_no_permissions(personal_saved_view):
    """User with no permissions cannot delete any view"""
    user_no_access = User.objects.create_user(username="no_access", password="pass")

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)
    with pytest.raises(Source.DoesNotExist):
        service.delete(user=user_no_access, view_slug=personal_saved_view.slug)


@pytest.mark.django_db
def test_update_personal_view_owner_no_source_access(personal_saved_view, test_user):
    """Owner of personal view cannot update it without READ permission on source"""
    data = {
        "scope": VIEW_SCOPE_PERSONAL,
        "name": "Updated Name",
        "description": "updated",
        "shared": False,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)
    with pytest.raises(PermissionDenied):
        service.update(user=test_user, slug=personal_saved_view.slug, data=data)


@pytest.mark.django_db
def test_update_source_view_with_edit_permission(source_saved_view, test_user):
    """User with EDIT permission can update source-scope view"""
    rbac_manager.grant_source_role(
        source=source_saved_view.source,
        role=SourceRole.EDITOR.value,
        user=test_user,
    )

    data = {
        "scope": VIEW_SCOPE_SOURCE,
        "name": "Updated Source View",
        "description": "updated",
        "shared": True,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=source_saved_view.source.slug)
    result = service.update(user=test_user, slug=source_saved_view.slug, data=data)

    assert result["name"] == "Updated Source View"


@pytest.mark.django_db
def test_update_source_view_with_owner_permission(source_saved_view, test_user):
    """User with OWNER permission can update source-scope view"""
    rbac_manager.grant_source_role(
        source=source_saved_view.source,
        role=SourceRole.OWNER.value,
        user=test_user,
    )

    data = {
        "scope": VIEW_SCOPE_SOURCE,
        "name": "Owner Updated View",
        "description": "updated by owner",
        "shared": True,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=source_saved_view.source.slug)
    result = service.update(user=test_user, slug=source_saved_view.slug, data=data)

    assert result["name"] == "Owner Updated View"


@pytest.mark.django_db
def test_change_scope_personal_to_source_without_edit(personal_saved_view, test_user):
    """Changing scope from personal to source requires EDIT permission"""
    # Grant only READ permission
    rbac_manager.grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )

    data = {
        "scope": VIEW_SCOPE_SOURCE,  # Trying to change to source scope
        "name": "Escalated View",
        "description": "trying to escalate",
        "shared": True,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)
    with pytest.raises(PermissionDenied):
        service.update(user=test_user, slug=personal_saved_view.slug, data=data)


@pytest.mark.django_db
def test_change_scope_personal_to_source_with_edit(personal_saved_view, test_user):
    """Changing scope from personal to source allowed with EDIT permission"""
    # Grant EDIT permission
    rbac_manager.grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.EDITOR.value,
        user=test_user,
    )

    data = {
        "scope": VIEW_SCOPE_SOURCE,  # Changing to source scope
        "name": "Promoted View",
        "description": "promoted to source",
        "shared": True,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)
    result = service.update(user=test_user, slug=personal_saved_view.slug, data=data)

    assert result["scope"] == VIEW_SCOPE_SOURCE


@pytest.mark.django_db
def test_get_view_with_editor_permission(source_saved_view, test_user):
    """User with EDITOR permission can get source view"""
    rbac_manager.grant_source_role(
        source=source_saved_view.source,
        role=SourceRole.EDITOR.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=source_saved_view.source.slug)
    result = service.get(user=test_user, view_slug=source_saved_view.slug)

    assert result["slug"] == source_saved_view.slug


@pytest.mark.django_db
def test_get_view_with_owner_permission(source_saved_view, test_user):
    """User with OWNER permission can get source view"""
    rbac_manager.grant_source_role(
        source=source_saved_view.source,
        role=SourceRole.OWNER.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=source_saved_view.source.slug)
    result = service.get(user=test_user, view_slug=source_saved_view.slug)

    assert result["slug"] == source_saved_view.slug


@pytest.mark.django_db
def test_list_views_with_use_permission(docker_source, test_user):
    """User with USE permission can list views (USER role includes READ)"""
    rbac_manager.grant_source_role(docker_source, SourceRole.USER.value, user=test_user)

    # Create a source view
    SavedView.objects.create(
        slug="test-view",
        name="Test View",
        scope=VIEW_SCOPE_SOURCE,
        source=docker_source,
        user=test_user,
        updated_by=test_user,
        shared=True,
        data={},
    )

    service = SourceSavedViewService(slug=docker_source.slug)
    results = service.list(user=test_user)

    assert len(results) > 0


@pytest.mark.django_db
def test_list_views_with_edit_permission(docker_source, test_user):
    """User with EDIT permission can list all views"""
    rbac_manager.grant_source_role(
        docker_source, SourceRole.EDITOR.value, user=test_user
    )

    # Create views
    SavedView.objects.create(
        slug="source-view",
        name="Source View",
        scope=VIEW_SCOPE_SOURCE,
        source=docker_source,
        user=test_user,
        updated_by=test_user,
        shared=True,
        data={},
    )

    SavedView.objects.create(
        slug="personal-view",
        name="Personal View",
        scope=VIEW_SCOPE_PERSONAL,
        source=docker_source,
        user=test_user,
        updated_by=test_user,
        shared=False,
        data={},
    )

    service = SourceSavedViewService(slug=docker_source.slug)
    results = service.list(user=test_user)

    assert len(results) >= 2
    names = [r["name"] for r in results]
    assert "Source View" in names
    assert "Personal View" in names


@pytest.mark.django_db
def test_list_views_with_owner_permission(docker_source, test_user):
    """User with OWNER permission can list all views"""
    rbac_manager.grant_source_role(
        docker_source, SourceRole.OWNER.value, user=test_user
    )

    # Create a view
    SavedView.objects.create(
        slug="owner-view",
        name="Owner View",
        scope=VIEW_SCOPE_SOURCE,
        source=docker_source,
        user=test_user,
        updated_by=test_user,
        shared=True,
        data={},
    )

    service = SourceSavedViewService(slug=docker_source.slug)
    results = service.list(user=test_user)

    assert len(results) > 0
    assert any(r["name"] == "Owner View" for r in results)


@pytest.mark.django_db
def test_permission_hierarchy_owner_can_do_everything(docker_source, test_user):
    """OWNER permission includes all lower permissions"""
    rbac_manager.grant_source_role(
        docker_source, SourceRole.OWNER.value, user=test_user
    )

    service = SourceSavedViewService(slug=docker_source.slug)

    # Can create personal view (needs READ)
    personal_data = {
        "scope": VIEW_SCOPE_PERSONAL,
        "name": "Owner Personal",
        "description": "",
        "shared": False,
        "data": {},
    }
    personal_result = service.create(
        user=test_user, slug=docker_source.slug, data=personal_data
    )
    assert personal_result["name"] == "Owner Personal"

    # Can create source view (needs EDIT)
    source_data = {
        "scope": VIEW_SCOPE_SOURCE,
        "name": "Owner Source",
        "description": "",
        "shared": True,
        "data": {},
    }
    source_result = service.create(
        user=test_user, slug=docker_source.slug, data=source_data
    )
    assert source_result["name"] == "Owner Source"

    # Can list views (needs READ)
    list_results = service.list(user=test_user)
    assert len(list_results) >= 2

    # Can delete source view (needs EDIT)
    service.delete(user=test_user, view_slug=source_result["slug"])

    # Verify deleted
    updated_list = service.list(user=test_user)
    assert not any(v["slug"] == source_result["slug"] for v in updated_list)
