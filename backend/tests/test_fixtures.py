import pytest

from django.contrib.auth.models import User

from telescope.models import Source, SourceField


@pytest.mark.django_db
def test_root_user_exist(root_user):
    assert isinstance(root_user, User)
    assert root_user.username == "test_root"
    assert root_user.is_superuser is True
    assert User.objects.filter(username="test_root").exists()


@pytest.mark.django_db
def test_user_exist(test_user):
    assert isinstance(test_user, User)
    assert test_user.username == "test_user"
    assert test_user.is_superuser is False
    assert User.objects.filter(username="test_user").exists()


@pytest.mark.django_db
def test_docker_source_fixture(docker_source):
    assert isinstance(docker_source, Source)
    assert docker_source.kind == "docker"
    assert docker_source.support_raw_query is False
    assert "container" in docker_source.context_fields
    assert docker_source.fields["time"]["type"] == "datetime"
    assert docker_source.fields["time"]["autocomplete"] is False
    assert docker_source.fields["time"]["suggest"] is True
    assert docker_source.fields["message"]["type"] == "string"
    assert docker_source.fields["message"]["display_name"] == "IsMessage"
    assert docker_source.fields["message"]["autocomplete"] is True
    assert docker_source.fields["message"]["jsonstring"] is True
    assert isinstance(docker_source.permissions, set)
    for key, value in docker_source._fields.items():
        assert isinstance(key, str)
        assert isinstance(value, SourceField)


@pytest.mark.django_db
def test_clickhouse_source_fixture(clickhouse_source):
    assert isinstance(clickhouse_source, Source)
    assert clickhouse_source.kind == "clickhouse"
    assert clickhouse_source.support_raw_query is True
    assert clickhouse_source.context_fields == {}
    assert clickhouse_source.fields["event_time"]["type"] == "DateTime64(3)"
    assert clickhouse_source.fields["event_time"]["autocomplete"] is False
    assert clickhouse_source.fields["event_time"]["suggest"] is True
    assert clickhouse_source.fields["message"]["type"] == "String"
    assert clickhouse_source.fields["message"]["display_name"] == "IsMessage"
    assert clickhouse_source.fields["message"]["autocomplete"] is True
    assert clickhouse_source.fields["message"]["jsonstring"] is True
    assert isinstance(clickhouse_source.permissions, set)
    for key, value in clickhouse_source._fields.items():
        assert isinstance(key, str)
        assert isinstance(value, SourceField)
