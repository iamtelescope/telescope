import pytest

from django.core.exceptions import PermissionDenied

from telescope.rbac.roles import GlobalRole, SourceRole
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()
from telescope.models import Source, SourceRoleBinding
from telescope.services.exceptions import SerializerValidationError
from telescope.serializers.source import SourceKindSerializer, NewDockerSourceSerializer

from tests.data import get_docker_source_data


@pytest.mark.django_db
def test_create_source_without_permissions(test_user, service):
    with pytest.raises(PermissionDenied):
        service.create(user=test_user, data=None)


@pytest.mark.django_db
def test_create_source_with_permissions(test_user, service, docker_connection):
    from telescope.rbac.roles import ConnectionRole

    rbac_manager.grant_global_role(role=GlobalRole.ADMIN.value, user=test_user)
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.USER.value,
        user=test_user,
    )

    slug = "testdocker"
    source_data = get_docker_source_data(slug)
    source_data["connection"] = {"connection_id": docker_connection.id}

    data = service.create(user=test_user, data=source_data)
    assert data == {"slug": slug}
    assert SourceRoleBinding.objects.filter(
        user=test_user, source__slug=slug, role=SourceRole.OWNER.value
    ).exists()
    assert Source.objects.get(slug=slug).support_raw_query is False

    # Test duplicate creation
    source_data_dup = get_docker_source_data(slug)
    source_data_dup["connection"] = {"connection_id": docker_connection.id}
    with pytest.raises(SerializerValidationError) as err:
        service.create(user=test_user, data=source_data_dup)
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
def test_create_source_with_execute_query_on_open_field(test_user, service, docker_connection):
    from telescope.rbac.roles import ConnectionRole

    rbac_manager.grant_global_role(role=GlobalRole.ADMIN.value, user=test_user)
    rbac_manager.grant_connection_role(
        connection=docker_connection,
        role=ConnectionRole.USER.value,
        user=test_user,
    )

    # Test creating source with execute_query_on_open = False
    slug = "testdocker_no_execute"
    source_data = get_docker_source_data(slug)
    source_data["connection"] = {"connection_id": docker_connection.id}
    source_data["execute_query_on_open"] = False

    data = service.create(user=test_user, data=source_data)
    assert data == {"slug": slug}
    source = Source.objects.get(slug=slug)
    assert source.execute_query_on_open is False

    # Test creating source with execute_query_on_open = True (explicit)
    slug2 = "testdocker_execute"
    source_data2 = get_docker_source_data(slug2)
    source_data2["connection"] = {"connection_id": docker_connection.id}
    source_data2["execute_query_on_open"] = True

    data2 = service.create(user=test_user, data=source_data2)
    assert data2 == {"slug": slug2}
    source2 = Source.objects.get(slug=slug2)
    assert source2.execute_query_on_open is True

    # Test creating source without execute_query_on_open (should default to True)
    slug3 = "testdocker_default"
    source_data3 = get_docker_source_data(slug3)
    source_data3["connection"] = {"connection_id": docker_connection.id}

    data3 = service.create(user=test_user, data=source_data3)
    assert data3 == {"slug": slug3}
    source3 = Source.objects.get(slug=slug3)
    assert source3.execute_query_on_open is True
