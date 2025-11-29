import pytest

from unittest.mock import patch, MagicMock

from django.core.exceptions import PermissionDenied

from telescope.constants import VIEW_SCOPE_PERSONAL, VIEW_SCOPE_SOURCE
from telescope.models import SavedView
from telescope.services.source import SourceSavedViewService
from telescope.rbac.roles import SourceRole
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()
from telescope.services.exceptions import SerializerValidationError


class DummyException(Exception):
    pass


@pytest.mark.django_db
def test_create_personal_view_success(test_user, docker_source):
    rbac_manager.grant_source_role(
        docker_source, SourceRole.VIEWER.value, user=test_user
    )

    data = {
        "scope": "personal",
        "name": "My View",
        "description": "desc",
        "shared": False,
        "data": {"fields": ""},
    }

    service = SourceSavedViewService(slug=docker_source.slug)
    result = service.create(user=test_user, slug=docker_source.slug, data=data)

    assert result["name"] == "My View"
    assert result["scope"] == "personal"
    assert result["user"]["username"] == test_user.username
    assert SavedView.objects.filter(name="My View").exists()


@pytest.mark.django_db
def test_create_source_view_with_edit_permission(test_user, docker_source):
    rbac_manager.grant_source_role(
        docker_source, SourceRole.EDITOR.value, user=test_user
    )

    data = {
        "scope": VIEW_SCOPE_SOURCE,
        "name": "Source-wide View",
        "description": "some desc",
        "shared": True,
        "data": {"graph_group_by": "level"},
    }

    service = SourceSavedViewService(slug=docker_source.slug)
    result = service.create(user=test_user, slug=docker_source.slug, data=data)

    assert result["name"] == "Source-wide View"
    assert result["scope"] == VIEW_SCOPE_SOURCE
    assert result["shared"] is True
    assert SavedView.objects.filter(name="Source-wide View").exists()


@pytest.mark.django_db
def test_create_source_view_without_edit_permission(test_user, docker_source):
    data = {
        "scope": VIEW_SCOPE_SOURCE,
        "name": "No Access View",
        "description": "should fail",
        "shared": False,
        "data": {},
    }

    service = SourceSavedViewService(slug=docker_source.slug)
    with pytest.raises(PermissionDenied):
        service.create(user=test_user, slug=docker_source.slug, data=data)


@pytest.mark.django_db
def test_create_personal_view_kubernetes_source(test_user, kubernetes_source):
    rbac_manager.grant_source_role(
        kubernetes_source, SourceRole.VIEWER.value, user=test_user
    )

    data = {
        "scope": "personal",
        "name": "My Kubernetes View",
        "description": "kubernetes desc",
        "shared": False,
        "data": {"fields": "pod_name,message"},
    }

    service = SourceSavedViewService(slug=kubernetes_source.slug)
    result = service.create(user=test_user, slug=kubernetes_source.slug, data=data)

    assert result["name"] == "My Kubernetes View"
    assert result["scope"] == "personal"
    assert result["user"]["username"] == test_user.username
    assert SavedView.objects.filter(name="My Kubernetes View").exists()


@pytest.mark.django_db
def test_create_source_view_kubernetes_with_edit_permission(test_user, kubernetes_source):
    rbac_manager.grant_source_role(
        kubernetes_source, SourceRole.EDITOR.value, user=test_user
    )

    data = {
        "scope": VIEW_SCOPE_SOURCE,
        "name": "Kubernetes Source-wide View",
        "description": "kubernetes source view",
        "shared": True,
        "data": {"graph_group_by": "pod_name"},
    }

    service = SourceSavedViewService(slug=kubernetes_source.slug)
    result = service.create(user=test_user, slug=kubernetes_source.slug, data=data)

    assert result["name"] == "Kubernetes Source-wide View"
    assert result["scope"] == VIEW_SCOPE_SOURCE
    assert result["shared"] is True
    assert SavedView.objects.filter(name="Kubernetes Source-wide View").exists()


@pytest.mark.django_db
def test_create_view_invalid_payload_serializer_fails(test_user, docker_source):
    data = {
        "scope": VIEW_SCOPE_PERSONAL,
        "name": "",
        "description": "some",
        "shared": False,
        "data": {},
    }
    rbac_manager.grant_source_role(
        docker_source, SourceRole.VIEWER.value, user=test_user
    )
    service = SourceSavedViewService(slug=docker_source.slug)

    with patch(
        "telescope.services.source.NewSourceSavedViewSerializer"
    ) as mock_serializer_cls:
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        mock_serializer.errors = {"name": ["This field is required."]}
        mock_serializer_cls.return_value = mock_serializer

        with pytest.raises(SerializerValidationError) as exc_info:
            service.create(user=test_user, slug=docker_source.slug, data=data)

        assert "name" in str(exc_info.value.serializer.errors)


@pytest.mark.django_db
def test_create_propagates_arbitrary_exception(test_user, docker_source):
    data = {
        "scope": "personal",
        "name": "x",
        "description": "",
        "shared": False,
        "data": {},
    }
    rbac_manager.grant_source_role(
        docker_source, SourceRole.VIEWER.value, user=test_user
    )
    with patch(
        "telescope.services.source.SourceSavedViewScopeSerializer.is_valid",
        side_effect=DummyException("fail"),
    ):
        service = SourceSavedViewService(slug=docker_source.slug)
        with pytest.raises(DummyException, match="fail"):
            service.create(user=test_user, slug=docker_source.slug, data=data)
