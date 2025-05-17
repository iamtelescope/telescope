import pytest

from unittest.mock import patch, MagicMock

from django.core.exceptions import PermissionDenied

from telescope.constants import VIEW_SCOPE_PERSONAL, VIEW_SCOPE_SOURCE
from telescope.models import SavedView
from telescope.services.source import SourceSavedViewService
from telescope.rbac.roles import SourceRole
from telescope.rbac.helpers import grant_source_role
from telescope.services.exceptions import SerializerValidationError


class DummyException(Exception):
    pass


@pytest.mark.django_db
def test_update_personal_view_by_owner(personal_saved_view, test_user):
    grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )

    update_data = {
        "name": "newname",
        "scope": personal_saved_view.scope,
        "description": "updated description",
        "shared": True,
        "data": personal_saved_view.data,
    }

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)

    result = service.update(
        user=test_user, slug=personal_saved_view.slug, data=update_data
    )

    assert result["description"] == "updated description"
    assert result["shared"] is True

    updated = SavedView.objects.get(pk=personal_saved_view.pk)
    assert updated.description == "updated description"
    assert updated.name == "newname"
    assert updated.shared is True


@pytest.mark.django_db
def test_update_personal_view_not_owner_permission_denied(
    hacker_user, personal_saved_view
):
    grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=hacker_user,
    )

    update_data = {
        "name": "not-allowed",
        "scope": "personal",
        "description": "should fail",
        "shared": False,
        "data": personal_saved_view.data,
    }

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)

    with pytest.raises(PermissionDenied):
        service.update(
            user=hacker_user, slug=personal_saved_view.slug, data=update_data
        )


@pytest.mark.django_db
def test_update_personal_view_not_owner_permission_denied(
    personal_saved_view, hacker_user
):
    grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=hacker_user,
    )

    update_data = {
        "name": "not-allowed",
        "scope": "personal",
        "description": "should fail",
        "shared": False,
        "data": personal_saved_view.data,
    }

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)

    with pytest.raises(PermissionDenied):
        service.update(
            user=hacker_user, slug=personal_saved_view.slug, data=update_data
        )


@pytest.mark.django_db
def test_update_source_view_without_edit_permission(source_saved_view, test_user):
    grant_source_role(
        source=source_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )

    update_data = {
        "name": "x",
        "scope": "source",
        "description": "should fail",
        "shared": True,
        "data": source_saved_view.data,
    }

    service = SourceSavedViewService(slug=source_saved_view.source.slug)

    with pytest.raises(PermissionDenied):
        service.update(user=test_user, slug=source_saved_view.slug, data=update_data)


@pytest.mark.django_db
def test_update_view_invalid_payload_raises_validation_error(
    personal_saved_view, test_user
):
    grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )

    update_data = {
        "scope": VIEW_SCOPE_PERSONAL,
        "description": "desc",
        "shared": True,
        "data": personal_saved_view.data,
    }

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)

    with patch(
        "telescope.services.source.UpdateSourceSavedViewSerializer"
    ) as mock_serializer_cls:
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = False
        mock_serializer.errors = {"name": ["This field is required."]}
        mock_serializer_cls.return_value = mock_serializer

        with pytest.raises(SerializerValidationError) as exc_info:
            service.update(
                user=test_user, slug=personal_saved_view.slug, data=update_data
            )

        assert "name" in str(exc_info.value.serializer.errors)


@pytest.mark.django_db
def test_update_view_propagates_arbitrary_exception(personal_saved_view, test_user):
    update_data = {
        "name": personal_saved_view.name,
        "scope": personal_saved_view.scope,
        "description": personal_saved_view.description,
        "shared": personal_saved_view.shared,
        "data": personal_saved_view.data,
    }

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)

    with patch(
        "telescope.services.source.SavedView.objects.get",
        side_effect=DummyException("fail"),
    ):
        with pytest.raises(DummyException, match="fail"):
            service.update(
                user=test_user, slug=personal_saved_view.slug, data=update_data
            )
