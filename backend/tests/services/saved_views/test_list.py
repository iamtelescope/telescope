import pytest

from unittest.mock import patch

from telescope.models import Source
from telescope.services.source import SourceSavedViewService
from telescope.rbac.roles import SourceRole
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()


class DummyException(Exception):
    pass


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
    rbac_manager.grant_source_role(
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
    rbac_manager.grant_source_role(
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
        "telescope.rbac.manager.RBACManager.get_source_saved_views",
        side_effect=DummyException("list failed"),
    ):
        service = SourceSavedViewService(slug="any")

        with pytest.raises(DummyException, match="list failed"):
            service.list(user=test_user)
