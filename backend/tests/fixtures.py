import pytest

from django.contrib.auth.models import User

from telescope.models import Source, SavedView, Connection
from telescope.services.source import SourceService
from telescope.services.connection import ConnectionService

from tests.data import (
    get_docker_source_data,
    get_clickhouse_source_data,
    get_kubernetes_source_data,
    get_saved_view_data,
    get_docker_connection_data,
    get_clickhouse_connection_data,
    get_kubernetes_connection_data,
)


@pytest.fixture
def service():
    return SourceService()


@pytest.fixture
def root_user():
    return User.objects.create(
        username="test_root", password="test_root", is_superuser=True
    )


@pytest.fixture
def test_user():
    return User.objects.create(
        username="test_user",
        password="test_user",
    )


@pytest.fixture
def hacker_user():
    return User.objects.create(username="test_hacker", password="test_hacker")


@pytest.fixture
def docker_source(docker_connection):
    data = get_docker_source_data("docker")
    del data["kind"]
    del data["connection"]  # Remove old connection field
    data["conn"] = docker_connection  # Add new conn ForeignKey
    return Source.create(
        kind="docker",
        data=data,
    )


@pytest.fixture
def clickhouse_source(clickhouse_connection):
    data = get_clickhouse_source_data("clickhouse")
    del data["kind"]
    del data["connection"]  # Remove old connection field
    data["conn"] = clickhouse_connection  # Add new conn ForeignKey
    return Source.create(
        kind="clickhouse",
        data=data,
    )


@pytest.fixture
def personal_saved_view(test_user, docker_source):
    return SavedView.objects.create(
        slug="test-view-personal",
        name="Test View Personal",
        description="test view description",
        scope="personal",
        source=docker_source,
        user=test_user,
        shared=False,
        data=get_saved_view_data(),
    )


@pytest.fixture
def shared_personal_saved_view(test_user, docker_source):
    return SavedView.objects.create(
        slug="test-view-personal-shared",
        name="Test View Personal Shared",
        description="test view description",
        scope="personal",
        source=docker_source,
        user=test_user,
        shared=True,
        data=get_saved_view_data(),
    )


@pytest.fixture
def source_saved_view(root_user, docker_source):
    return SavedView.objects.create(
        slug="test-view-source-scoped",
        name="Test View Source Scoped",
        description="test view description",
        scope="source",
        source=docker_source,
        user=root_user,
        shared=False,
        data=get_saved_view_data(),
    )


@pytest.fixture
def personal_root_saved_view(root_user, docker_source):
    return SavedView.objects.create(
        slug="test-view-personal-root",
        name="Test View Personal Root",
        description="test view description",
        scope="personal",
        source=docker_source,
        user=root_user,
        shared=False,
        data=get_saved_view_data(),
    )


@pytest.fixture
def personal_root_shared_saved_view(root_user, docker_source):
    return SavedView.objects.create(
        slug="test-view-personal-root-shared",
        name="Test View Personal Root Shared",
        description="test view description",
        scope="personal",
        source=docker_source,
        user=root_user,
        shared=True,
        data=get_saved_view_data(),
    )


@pytest.fixture
def kubernetes_personal_saved_view(test_user, kubernetes_source):
    return SavedView.objects.create(
        slug="test-view-kubernetes-personal",
        name="Test View Kubernetes Personal",
        description="test view description",
        scope="personal",
        source=kubernetes_source,
        user=test_user,
        shared=False,
        data=get_saved_view_data(),
    )


@pytest.fixture
def kubernetes_source_saved_view(root_user, kubernetes_source):
    return SavedView.objects.create(
        slug="test-view-kubernetes-source",
        name="Test View Kubernetes Source",
        description="test view description",
        scope="source",
        source=kubernetes_source,
        user=root_user,
        shared=False,
        data=get_saved_view_data(),
    )


@pytest.fixture
def connection_service():
    return ConnectionService()


@pytest.fixture
def docker_connection():
    data = get_docker_connection_data()
    return Connection.objects.create(**data)


@pytest.fixture
def clickhouse_connection():
    data = get_clickhouse_connection_data()
    return Connection.objects.create(**data)


@pytest.fixture
def kubernetes_source(kubernetes_connection):
    data = get_kubernetes_source_data("kubernetes")
    del data["kind"]
    del data["connection"]
    data["conn"] = kubernetes_connection 
    return Source.create(
        kind="kubernetes",
        data=data,
    )


@pytest.fixture
def kubernetes_connection():
    data = get_kubernetes_connection_data()
    return Connection.objects.create(**data)
