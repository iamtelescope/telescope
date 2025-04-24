import pytest

from django.contrib.auth.models import User

from telescope.models import Source
from tests.data import get_docker_source_data, get_clickhouse_source_data


@pytest.fixture
def root_user(db):
    return User.objects.create(
        username="test_root", password="test_root", is_superuser=True
    )


@pytest.fixture
def test_user(db):
    return User.objects.create(
        username="test_user",
        password="test_user",
    )


@pytest.fixture
def docker_source(db):
    data = get_docker_source_data("docker")
    del data["kind"]
    return Source.create(
        kind="docker",
        data=data,
    )


@pytest.fixture
def clickhouse_source(db):
    data = get_clickhouse_source_data("clickhouse")
    del data["kind"]
    return Source.create(
        kind="clickhouse",
        data=data,
    )
