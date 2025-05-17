import pytest

from django.core.exceptions import PermissionDenied

from telescope.rbac.roles import GlobalRole, SourceRole
from telescope.rbac.helpers import grant_global_role, grant_source_role
from telescope.models import Source, SourceRoleBinding
from telescope.services.exceptions import SerializerValidationError
from telescope.serializers.source import SourceKindSerializer, NewDockerSourceSerializer

from tests.data import get_docker_source_data


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
