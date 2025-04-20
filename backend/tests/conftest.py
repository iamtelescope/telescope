import pytest

from django.contrib.auth.models import User

from telescope.models import Source


@pytest.fixture
def user(db):
    return User.objects.create(username="test", password="test")


@pytest.fixture
def docker_source(db):
    return Source.create(
        kind="docker",
        data={
            "slug": "docker",
            "name": "Docker",
            "description": "docker test source",
            "time_field": "time",
            "uniq_field": "",
            "severity_field": "",
            "fields": {
                "time": {
                    "display_name": "",
                    "autocomplete": False,
                    "suggest": True,
                    "type": "datetime",
                    "jsonstring": False,
                    "group_by": False,
                    "values": [],
                },
                "message": {
                    "display_name": "IsMessage",
                    "autocomplete": True,
                    "suggest": True,
                    "type": "string",
                    "jsonstring": True,
                    "group_by": False,
                    "values": [],
                },
            },
            "table": "",
            "default_chosen_fields": ["messsage"],
            "connection": {"address": "docker.sock"},
        },
        username="test",
    )
