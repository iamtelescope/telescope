from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from telescope.models import Source
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import ConnectionRole
from telescope_otel.detect import detect
from tests.otel import columns as C

URL = "/ui/v1/otel/detect"
rbac_manager = RBACManager()


def post(user, body):
    client = APIClient()
    client.force_login(user)
    return client.post(URL, body, format="json").json()


def body(conn, table="otel_logs"):
    return {"connection_id": conn.id, "database": "otel", "table": table}


def make_source(slug, conn, signal, database="otel"):
    data = {"database": database, "table": "t"}
    if signal:
        data["otel"] = {"signal": signal, "roles": {}}
    return Source.create(
        kind="clickhouse",
        data={
            "slug": slug,
            "name": slug,
            "description": "",
            "time_column": "Timestamp",
            "date_column": "",
            "severity_column": "",
            "columns": C.source_columns(C.LOGS),
            "default_chosen_columns": ["Timestamp"],
            "conn": conn,
            "data": data,
        },
    )


@pytest.mark.django_db
@patch("telescope_otel.views.read_table", return_value=(C.LOGS, ["otel_logs"]))
def test_detect_logs(read_table, root_user, clickhouse_connection):
    resp = post(root_user, body(clickhouse_connection))
    assert resp["result"], resp
    assert resp["data"] == detect("otel_logs", C.LOGS)
    read_table.assert_called_once()
    assert read_table.call_args.args[1:] == ("otel", "otel_logs")


@pytest.mark.django_db
@patch("telescope_otel.views.read_table", return_value=([("ts", "DateTime")], []))
def test_detect_non_otel(read_table, root_user, clickhouse_connection):
    assert post(root_user, body(clickhouse_connection))["data"] == {"otel": None}


@pytest.mark.django_db
@patch("telescope_otel.views.read_table", return_value=([], []))
def test_detect_missing_table(read_table, root_user, clickhouse_connection):
    resp = post(root_user, body(clickhouse_connection, "nope"))
    assert not resp["result"]
    assert resp["errors"] == ["table otel.nope not found"]


@pytest.mark.django_db
@patch("telescope_otel.views.read_table")
def test_detect_needs_connection_use(read_table, test_user, clickhouse_connection):
    resp = post(test_user, body(clickhouse_connection))
    assert not resp["result"]
    read_table.assert_not_called()
    rbac_manager.grant_connection_role(
        connection=clickhouse_connection, role=ConnectionRole.USER.value, user=test_user
    )
    read_table.return_value = (C.LOGS, [])
    assert (
        post(test_user, body(clickhouse_connection))["data"]["otel"]["signal"] == "logs"
    )


@pytest.mark.django_db
@patch("telescope_otel.views.read_table")
def test_detect_docker_connection_is_not_otel(read_table, root_user, docker_connection):
    resp = post(root_user, body(docker_connection))
    assert resp["data"] == {"otel": None}
    read_table.assert_not_called()


@pytest.mark.django_db
def test_detect_validates_body(root_user):
    resp = post(root_user, {"database": "otel"})
    assert resp["validation"]["result"] is False
    assert set(resp["validation"]["fields"]) == {"connection_id", "table"}


@pytest.mark.django_db
@patch("telescope_otel.views.read_table", return_value=(C.LOGS, []))
def test_links_suggest_readable_sources_on_same_database(
    read_table, root_user, test_user, clickhouse_connection
):
    make_source("b-traces", clickhouse_connection, "traces")
    make_source("a-traces", clickhouse_connection, "traces")
    make_source("other-db", clickhouse_connection, "metrics", database="otel2")
    make_source("logs-too", clickhouse_connection, "logs")
    make_source("plain", clickhouse_connection, None)
    links = post(root_user, body(clickhouse_connection))["data"]["otel"]["links"]
    assert links == {"traces": "a-traces"}

    # Only sources the user can read are suggested.
    rbac_manager.grant_connection_role(
        connection=clickhouse_connection, role=ConnectionRole.USER.value, user=test_user
    )
    assert post(test_user, body(clickhouse_connection))["data"]["otel"]["links"] == {}
