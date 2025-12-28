import pytest

from unittest.mock import patch


from telescope.models import Source, SavedView
from telescope.services.source import SourceSavedViewService
from telescope.rbac.roles import SourceRole
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()


class DummyException(Exception):
    pass


@pytest.mark.django_db
def test_get_personal_saved_view(personal_saved_view, test_user):
    rbac_manager.grant_source_role(
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
    rbac_manager.grant_source_role(
        source=docker_source,
        role=SourceRole.USER.value,
        user=test_user,
    )
    service = SourceSavedViewService(slug=docker_source.slug)

    with pytest.raises(SavedView.DoesNotExist):
        service.get(user=test_user, view_slug="view does not exist")


@pytest.mark.django_db
def test_get_kubernetes_personal_saved_view(
    kubernetes_personal_saved_view, test_user, kubernetes_source
):
    rbac_manager.grant_source_role(
        source=kubernetes_personal_saved_view.source,
        role=SourceRole.USER.value,
        user=test_user,
    )

    service = SourceSavedViewService(slug=kubernetes_source.slug)
    result = service.get(user=test_user, view_slug=kubernetes_personal_saved_view.slug)

    assert result["slug"] == kubernetes_personal_saved_view.slug
    assert result["name"] == kubernetes_personal_saved_view.name
    assert result["scope"] == "personal"
    assert result["user"]["username"] == test_user.username


@pytest.mark.django_db
def test_get_kubernetes_source_saved_view(
    kubernetes_source_saved_view, root_user, kubernetes_source
):
    service = SourceSavedViewService(slug=kubernetes_source.slug)
    result = service.get(user=root_user, view_slug=kubernetes_source_saved_view.slug)

    assert result["slug"] == kubernetes_source_saved_view.slug
    assert result["name"] == kubernetes_source_saved_view.name
    assert result["scope"] == "source"
    assert result["user"]["username"] == root_user.username


@pytest.mark.django_db
def test_get_view_propagates_arbitrary_exception(test_user):
    with patch(
        "telescope.rbac.manager.RBACManager.get_source_saved_view",
        side_effect=DummyException("boom"),
    ):
        service = SourceSavedViewService(slug="whatever")

        with pytest.raises(DummyException, match="boom"):
            service.get(user=test_user, view_slug="irrelevant")
