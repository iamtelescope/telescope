import pytest

from django.core.exceptions import PermissionDenied

from telescope.models import Source
from tests.data import get_docker_source_data, get_kubernetes_source_data


@pytest.mark.django_db
def test_update_source_without_permissions(test_user, service):
    with pytest.raises(PermissionDenied):
        service.update(user=test_user, slug="some_test_slug", data={})


@pytest.mark.django_db
def test_update_source_invalid_kind(test_user, service, docker_connection):
    slug = "test_unknown_slug"
    Source.objects.create(
        slug=slug,
        fields={},
        modifiers={},
        default_chosen_fields={},
        conn=docker_connection,
        context_fields={},
        support_raw_query=False,
    )
    with pytest.raises(PermissionDenied):
        service.update(user=test_user, slug=slug, data={})


@pytest.mark.django_db
def test_update_source_with_permissions(root_user, service, docker_source):
    data = get_docker_source_data(docker_source.slug)
    # Remove connection data - source updates don't modify connections
    del data["connection"]
    # Remove slug - it's used as identifier, not part of update payload
    del data["slug"]
    data["name"] = "new_name"
    data["fields"]["container_name"]["display_name"] = "new_container_name"

    service.update(user=root_user, slug=docker_source.slug, data=data)

    source = Source.objects.get(slug=docker_source.slug)
    assert source.name == "new_name"
    assert source.fields["container_name"]["display_name"] == "new_container_name"
    # Connection remains unchanged
    assert source.conn.data["address"] == "unix:///var/run/docker.sock"


@pytest.mark.django_db
def test_update_source_execute_query_on_open_field(root_user, service, docker_source):
    # Test that execute_query_on_open field can be updated

    # Update to False
    data = get_docker_source_data(docker_source.slug)
    del data["connection"]
    data["execute_query_on_open"] = False
    service.update(user=root_user, slug=docker_source.slug, data=data)
    source = Source.objects.get(slug=docker_source.slug)
    assert source.execute_query_on_open is False

    # Update to True
    data2 = get_docker_source_data(docker_source.slug)
    del data2["connection"]
    data2["execute_query_on_open"] = True
    service.update(user=root_user, slug=docker_source.slug, data=data2)
    source = Source.objects.get(slug=docker_source.slug)
    assert source.execute_query_on_open is True


@pytest.mark.django_db
def test_update_kubernetes_source_without_permissions(
    test_user, service, kubernetes_source
):
    with pytest.raises(PermissionDenied):
        service.update(user=test_user, slug=kubernetes_source.slug, data={})


@pytest.mark.django_db
def test_update_kubernetes_source_invalid_kind(
    test_user, service, kubernetes_connection
):
    slug = "test_unknown_k8s_slug"
    Source.objects.create(
        slug=slug,
        fields={},
        modifiers={},
        default_chosen_fields={},
        conn=kubernetes_connection,
        context_fields={},
        support_raw_query=False,
    )
    with pytest.raises(PermissionDenied):
        service.update(user=test_user, slug=slug, data={})


@pytest.mark.django_db
def test_update_kubernetes_source_with_permissions(
    root_user, service, kubernetes_source
):
    data = get_kubernetes_source_data(kubernetes_source.slug)
    # Remove connection data - source updates don't modify connections
    del data["connection"]
    data["name"] = "new_k8s_name"
    data["fields"]["namespace"]["display_name"] = "new_namespace_name"
    service.update(user=root_user, slug=kubernetes_source.slug, data=data)

    source = Source.objects.get(slug=kubernetes_source.slug)
    assert source.name == "new_k8s_name"
    assert source.fields["namespace"]["display_name"] == "new_namespace_name"
