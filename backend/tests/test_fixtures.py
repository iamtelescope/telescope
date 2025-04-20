import pytest

from django.contrib.auth.models import User

from telescope.models import Source, SourceField


@pytest.mark.django_db
def test_user_exist(user):
    assert isinstance(user, User)
    assert user.username == "test"
    assert User.objects.filter(username="test").exists()


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
