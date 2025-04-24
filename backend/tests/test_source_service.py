import pytest

from django.core.exceptions import PermissionDenied

from telescope.rbac.roles import GlobalRole, SourceRole
from telescope.rbac.helpers import grant_global_role, grant_source_role
from telescope.models import Source, SourceRoleBinding
from telescope.services.exceptions import SerializerValidationError
from telescope.services.source import SourceService
from telescope.serializers.source import SourceKindSerializer, NewDockerSourceSerializer

from tests.data import get_docker_source_data


@pytest.fixture
def service():
    return SourceService()


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
def test_delete_source_without_permissions(test_user, service, docker_source):
    with pytest.raises(PermissionDenied):
        service.delete(user=test_user, slug=docker_source.slug)


@pytest.mark.django_db
def test_delete_source_that_not_exist(test_user, service):
    with pytest.raises(PermissionDenied):
        service.delete(user=test_user, slug="some_test_slug_that_does_not_exist")


@pytest.mark.django_db
def test_list_source_with_full_permissions(root_user, service, docker_source):
    service.delete(user=root_user, slug=docker_source.slug)
    with pytest.raises(Source.DoesNotExist):
        Source.objects.get(slug=docker_source.slug)


@pytest.mark.django_db
def test_create_source_without_permissions(test_user, service):
    with pytest.raises(PermissionDenied):
        service.create(user=test_user, data=None)


@pytest.mark.django_db
def test_create_source_with_permissions(test_user, service):
    grant_global_role(role=GlobalRole.ADMIN.value, user=test_user)
    slug = "testdocker"
    data = service.create(user=test_user, data=get_docker_source_data(slug))
    assert data == {"slug": slug}
    assert SourceRoleBinding.objects.filter(
        user=test_user, source__slug=slug, role=SourceRole.OWNER.value
    ).exists()
    assert Source.objects.get(slug=slug).support_raw_query is False
    with pytest.raises(SerializerValidationError) as err:
        service.create(user=test_user, data=get_docker_source_data(slug))
    assert isinstance(err.value.serializer, NewDockerSourceSerializer)
    assert (
        str(err.value.serializer.errors["slug"][0])
        == "Source with that slug already exist"
    )


@pytest.mark.django_db
def test_create_source_with_invalid_kind(root_user, service):
    slug = "testdocker"
    data = get_docker_source_data(slug)
    data["kind"] = "invalid_kind"
    with pytest.raises(SerializerValidationError) as err:
        service.create(user=root_user, data=data)
    assert isinstance(err.value.serializer, SourceKindSerializer)
    assert str(err.value.serializer.errors["kind"][0]).startswith(
        "Only these kinds are supported:"
    )


@pytest.mark.django_db
def test_create_source_with_invalid_data(root_user, service):
    slug = "testdocker"
    data = get_docker_source_data(slug)
    del data["name"]
    with pytest.raises(SerializerValidationError) as err:
        service.create(user=root_user, data=data)
    assert isinstance(err.value.serializer, NewDockerSourceSerializer)
    assert str(err.value.serializer.errors["name"][0]) == "This field is required."


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
