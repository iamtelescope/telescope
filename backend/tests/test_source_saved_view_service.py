import pytest

from unittest.mock import patch, MagicMock

from django.core.exceptions import PermissionDenied

from telescope.constants import VIEW_SCOPE_PERSONAL, VIEW_SCOPE_SOURCE
from telescope.models import Source, SavedView
from telescope.services.source import SourceSavedViewService
from telescope.rbac.roles import SourceRole
from telescope.rbac.helpers import grant_source_role
from telescope.services.exceptions import SerializerValidationError


class DummyException(Exception):
    pass


@pytest.mark.django_db
def test_get_personal_saved_view(personal_saved_view, test_user):
    grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.USER.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)
    result = service.get(user=test_user, view_slug=personal_saved_view.slug)

    assert result["slug"] == personal_saved_view.slug
    assert result["name"] == personal_saved_view.name
    assert result["scope"] == "personal"
    assert result["user"]["username"] == test_user.username


@pytest.mark.django_db
def test_get_personal_saved_view_no_source_access(personal_saved_view, test_user):
    service = SourceSavedViewService(slug=personal_saved_view.source.slug)

    with pytest.raises(Source.DoesNotExist):
        service.get(user=test_user, view_slug=personal_saved_view.slug)


@pytest.mark.django_db
def test_get_personal_saved_view_no_access(test_user, docker_source):
    grant_source_role(
        source=docker_source,
        role=SourceRole.USER.value,
        user=test_user,
    )
    service = SourceSavedViewService(slug=docker_source.slug)

    with pytest.raises(SavedView.DoesNotExist):
        service.get(user=test_user, view_slug="view does not exist")


@pytest.mark.django_db
def test_get_view_propagates_arbitrary_exception(test_user):
    with patch(
        "telescope.services.source.get_source_saved_view",
        side_effect=DummyException("boom"),
    ):
        service = SourceSavedViewService(slug="whatever")

        with pytest.raises(DummyException, match="boom"):
            service.get(user=test_user, view_slug="irrelevant")


@pytest.mark.django_db
def test_list_saved_views_returns_all_visible_views(
    test_user,
    docker_source,
    personal_saved_view,
    shared_personal_saved_view,
    source_saved_view,
    personal_root_saved_view,
    personal_root_shared_saved_view,
):
    grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=docker_source.slug)
    views = service.list(user=test_user)

    view_slugs = {v["slug"] for v in views}

    assert personal_saved_view.slug in view_slugs
    assert shared_personal_saved_view.slug in view_slugs
    assert source_saved_view.slug in view_slugs
    assert personal_root_shared_saved_view.slug in view_slugs
    assert personal_root_saved_view.slug not in view_slugs


@pytest.mark.django_db
def test_list_saved_views_emtpy(test_user, clickhouse_source):
    grant_source_role(
        source=clickhouse_source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )
    service = SourceSavedViewService(slug=clickhouse_source.slug)

    views = service.list(user=test_user)
    assert len(views) == 0


@pytest.mark.django_db
def test_list_saved_views_no_access_to_source(test_user, docker_source):
    service = SourceSavedViewService(slug=docker_source.slug)

    with pytest.raises(Source.DoesNotExist):
        service.list(user=test_user)


@pytest.mark.django_db
def test_list_saved_views_propagates_exception(test_user):
    with patch(
        "telescope.services.source.get_source_saved_views",
        side_effect=DummyException("list failed"),
    ):
        service = SourceSavedViewService(slug="any")

        with pytest.raises(DummyException, match="list failed"):
            service.list(user=test_user)


@pytest.mark.django_db
def test_delete_personal_saved_view_by_owner(personal_saved_view, test_user):
    grant_source_role(
        source=personal_saved_view.source,
        role=SourceRole.VIEWER.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=personal_saved_view.source.slug)
    service.delete(user=test_user, view_slug=personal_saved_view.slug)

    assert not SavedView.objects.filter(pk=personal_saved_view.pk).exists()


@pytest.mark.django_db
def test_delete_source_saved_view_with_edit_permission(source_saved_view, test_user):
    grant_source_role(
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
    grant_source_role(
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
        "telescope.services.source.get_source_saved_view",
        return_value=personal_saved_view,
    ):
        service = SourceSavedViewService(slug=personal_saved_view.source.slug)

        with pytest.raises(PermissionDenied):
            service.delete(user=hacker_user, view_slug=personal_saved_view.slug)


@pytest.mark.django_db
def test_delete_source_saved_view_without_edit_permission(source_saved_view, test_user):
    grant_source_role(
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
        "telescope.services.source.get_source_saved_view",
        side_effect=DummyException("boom"),
    ):
        service = SourceSavedViewService(slug="irrelevant")

        with pytest.raises(DummyException, match="boom"):
            service.delete(user=test_user, view_slug="anything")


@pytest.mark.django_db
def test_create_personal_view_success(test_user, docker_source):
    grant_source_role(docker_source, SourceRole.VIEWER.value, user=test_user)

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
    from telescope.rbac.roles import SourceRole
    from telescope.rbac.helpers import grant_source_role
    from telescope.services.source import SourceSavedViewService
    from telescope.models import SavedView

    grant_source_role(docker_source, SourceRole.EDITOR.value, user=test_user)

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
def test_create_view_invalid_payload_serializer_fails(test_user, docker_source):
    data = {
        "scope": VIEW_SCOPE_PERSONAL,
        "name": "",
        "description": "some",
        "shared": False,
        "data": {},
    }
    grant_source_role(docker_source, SourceRole.VIEWER.value, user=test_user)
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
    grant_source_role(docker_source, SourceRole.VIEWER.value, user=test_user)
    with patch(
        "telescope.services.source.SourceSavedViewScopeSerializer.is_valid",
        side_effect=DummyException("fail"),
    ):
        service = SourceSavedViewService(slug=docker_source.slug)
        with pytest.raises(DummyException, match="fail"):
            service.create(user=test_user, slug=docker_source.slug, data=data)


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
