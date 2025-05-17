import pytest

from django.core.exceptions import PermissionDenied


@pytest.mark.django_db
def test_delete_source_without_permissions(test_user, service, docker_source):
    with pytest.raises(PermissionDenied):
        service.delete(user=test_user, slug=docker_source.slug)


@pytest.mark.django_db
def test_delete_source_that_not_exist(test_user, service):
    with pytest.raises(PermissionDenied):
        service.delete(user=test_user, slug="some_test_slug_that_does_not_exist")
