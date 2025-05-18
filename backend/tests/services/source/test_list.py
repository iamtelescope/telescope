import pytest

from telescope.models import Source
from telescope.rbac.roles import SourceRole
from telescope.rbac.helpers import grant_source_role


@pytest.mark.django_db
def test_list_source(test_user, service, docker_source):
    data = service.list(user=test_user)
    assert isinstance(data, list)
    assert len(data) == 0

    grant_source_role(
        source=docker_source, role=SourceRole.VIEWER.value, user=test_user
    )
    data = service.list(user=test_user)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["slug"] == docker_source.slug
    assert "connection" not in data


@pytest.mark.django_db
def test_list_source_with_full_permissions(root_user, service, docker_source):
    data = service.list(user=root_user)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["slug"] == docker_source.slug
    assert "connection" not in data[0]


@pytest.mark.django_db
def test_list_source_with_full_permissions(root_user, service, docker_source):
    service.delete(user=root_user, slug=docker_source.slug)
    with pytest.raises(Source.DoesNotExist):
        Source.objects.get(slug=docker_source.slug)
