import pytest

from unittest.mock import patch

from django.core.exceptions import PermissionDenied

from telescope.models import SavedView
from telescope.services.source import SourceSavedViewService
from telescope.rbac.roles import SourceRole
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()


class DummyException(Exception):
    pass


@pytest.mark.django_db
def test_delete_personal_saved_view_by_owner(personal_saved_view, test_user):
    rbac_manager.grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)
    service.delete(user=test_user, view_slug=personal_saved_view.slug)

    assert not SavedView.objects.filter(pk=personal_saved_view.pk).exists()


@pytest.mark.django_db
def test_delete_source_saved_view_with_edit_permission(source_saved_view, test_user):
    rbac_manager.grant_source_role(
        source=source_saved_view.source,
        role=SourceRole.EDITOR.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=source_saved_view.source.slug)
    service.delete(user=test_user, view_slug=source_saved_view.slug)

    assert not SavedView.objects.filter(pk=source_saved_view.pk).exists()


@pytest.mark.django_db
def test_delete_personal_saved_view_not_owner_cant_find_view(
    hacker_user, shared_personal_saved_view
):
    rbac_manager.grant_source_role(
        source=shared_personal_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=hacker_user,
    )

    service = SourceSavedViewService(slug=shared_personal_saved_view.source.slug)
    with pytest.raises(SavedView.DoesNotExist):
        service.delete(user=hacker_user, view_slug=shared_personal_saved_view.slug)


@pytest.mark.django_db
def test_delete_personal_saved_view_not_owner__mocked_get(
    personal_saved_view, test_user, hacker_user
):
    with patch(
        "telescope.rbac.manager.RBACManager.get_source_saved_view",
        return_value=personal_saved_view,
    ):
        service = SourceSavedViewService(slug=personal_saved_view.source.slug)

        with pytest.raises(PermissionDenied):
            service.delete(user=hacker_user, view_slug=personal_saved_view.slug)


@pytest.mark.django_db
def test_delete_source_saved_view_without_edit_permission(source_saved_view, test_user):
    rbac_manager.grant_source_role(
        source=source_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=source_saved_view.source.slug)
    with pytest.raises(PermissionDenied):
        service.delete(user=test_user, view_slug=source_saved_view.slug)


@pytest.mark.django_db
def test_delete_saved_view_propagates_exception(test_user):
    with patch(
        "telescope.rbac.manager.RBACManager.get_source_saved_view",
        side_effect=DummyException("boom"),
    ):
        service = SourceSavedViewService(slug="irrelevant")

        with pytest.raises(DummyException, match="boom"):
            service.delete(user=test_user, view_slug="anything")
