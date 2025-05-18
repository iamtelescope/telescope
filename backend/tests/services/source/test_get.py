import pytest

from telescope.rbac.roles import SourceRole
from telescope.rbac.helpers import grant_source_role
from telescope.models import Source


@pytest.mark.django_db
def test_get_source(test_user, service, docker_source):
    with pytest.raises(Source.DoesNotExist):
        service.get(user=test_user, slug=docker_source.slug)

    grant_source_role(
        source=docker_source, role=SourceRole.VIEWER.value, user=test_user
    )
    data = service.get(user=test_user, slug=docker_source.slug)
    assert data["slug"] == docker_source.slug
    assert "connection" not in data

    grant_source_role(
        source=docker_source, role=SourceRole.EDITOR.value, user=test_user
    )
    data = service.get(user=test_user, slug=docker_source.slug)
    assert data["slug"] == docker_source.slug
    assert "address" in data["connection"]


@pytest.mark.django_db
def test_get_source_with_full_permissions(root_user, service, docker_source):
    data = service.get(user=root_user, slug=docker_source.slug)
    assert data["slug"] == docker_source.slug
    assert "address" in data["connection"]
