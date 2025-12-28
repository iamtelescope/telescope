import pytest

from telescope.rbac.manager import RBACManager
from django.core.exceptions import PermissionDenied

rbac_manager = RBACManager()


@pytest.mark.django_db
def test_delete_source_without_permissions(test_user, service, docker_source):
    with pytest.raises(PermissionDenied):
        service.delete(user=test_user, slug=docker_source.slug)


@pytest.mark.django_db
def test_delete_source_that_not_exist(test_user, service):
    with pytest.raises(PermissionDenied):
        service.delete(user=test_user, slug="some_test_slug_that_does_not_exist")


@pytest.mark.django_db
def test_delete_kubernetes_source_without_permissions(
    test_user, service, kubernetes_source
):
    with pytest.raises(PermissionDenied):
        service.delete(user=test_user, slug=kubernetes_source.slug)


@pytest.mark.django_db
def test_delete_kubernetes_source_with_permissions(
    test_user, service, kubernetes_source
):
    from telescope.rbac.roles import SourceRole

    rbac_manager.grant_source_role(
        source=kubernetes_source, role=SourceRole.OWNER.value, user=test_user
    )

    service.delete(user=test_user, slug=kubernetes_source.slug)

    # Verify the source was actually deleted
    from telescope.models import Source

    with pytest.raises(Source.DoesNotExist):
        Source.objects.get(slug=kubernetes_source.slug)
