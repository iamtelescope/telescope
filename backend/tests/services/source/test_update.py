import pytest

from django.core.exceptions import PermissionDenied

from telescope.models import Source
from tests.data import get_docker_source_data


@pytest.mark.django_db
def test_update_source_without_permissions(test_user, service):
    with pytest.raises(PermissionDenied):
        service.update(user=test_user, slug="some_test_slug", data={})


@pytest.mark.django_db
def test_update_source_invalid_kind(test_user, service):
    slug = "test_unknown_slug"
    Source.objects.create(
        slug=slug,
        fields={},
        modifiers={},
        default_chosen_fields={},
        connection={},
        context_fields={},
        support_raw_query=False,
    )
    with pytest.raises(PermissionDenied):
        service.update(user=test_user, slug=slug, data={})


@pytest.mark.django_db
def test_update_source_with_permissions(root_user, service, docker_source):
    data = get_docker_source_data(docker_source.slug)
    data["connection"]["address"] = "new_address"
    data["name"] = "new_name"
    data["fields"]["container_name"]["display_name"] = "new_container_name"
    service.update(user=root_user, slug=docker_source.slug, data=data)

    source = Source.objects.get(slug=docker_source.slug)
    assert source.name == "new_name"
    assert source.fields["container_name"]["display_name"] == "new_container_name"
    assert source.connection["address"] == "new_address"
