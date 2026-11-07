import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from telescope.models import Connection
from telescope.rbac.manager import RBACManager
from tests.fixtures import *  # noqa: F401,F403
from tests.integration.conftest import ch_settings, ch_settings_dict  # noqa: F401

T0 = 1762423200000


def pytest_collection_modifyitems(config, items):
    if ch_settings():
        return
    skip = pytest.mark.skip(
        reason="TELESCOPE_TEST_CH_HOST / TELESCOPE_TEST_CH_PORT not set"
    )
    for item in items:
        if "clickhouse" in item.keywords and "telescope_rawsql" in str(item.fspath):
            item.add_marker(skip)


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def query(client, pk, sql, **body):
    body = {"from": str(T0), "to": str(T0 + 3600000), "sql": sql, **body}
    return client.post(f"/ui/v1/rawsql/connections/{pk}/query", body, format="json")


@pytest.fixture
def ch_connection(ch_settings_dict):
    return Connection.objects.create(
        kind="clickhouse",
        name="local",
        data={
            "host": ch_settings_dict["host"],
            "port": ch_settings_dict["port"],
            "user": ch_settings_dict["username"],
            "password": ch_settings_dict["password"],
            "ssl": False,
            "verify": False,
        },
    )


@pytest.fixture
def sql_user(db):
    return User.objects.create(username="sql_user", password="x")


def grant(connection, user, role="raw_sql_user"):
    RBACManager().grant_connection_role(connection, role, user=user)
    return user
