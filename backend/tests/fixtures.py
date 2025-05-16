import pytest

from django.contrib.auth.models import User

from telescope.models import Source, SavedView
from telescope.rbac.helpers import grant_source_role
from telescope.rbac.roles import SourceRole
from tests.data import (
    get_docker_source_data,
    get_clickhouse_source_data,
    get_saved_view_data,
)


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
def docker_source():
    data = get_docker_source_data("docker")
    del data["kind"]
    return Source.create(
        kind="docker",
        data=data,
    )


@pytest.fixture
def clickhouse_source():
    data = get_clickhouse_source_data("clickhouse")
    del data["kind"]
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
