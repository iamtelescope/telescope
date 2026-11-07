"""P1.2 request fields on /data and /graphData: validation, pass-through and the returned cursor."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from telescope.fetchers.response import DataResponse, GraphDataResponse
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole

rbac_manager = RBACManager()
T0 = 1762423200000


def body(**changes):
    data = {
        "columns": "hostname",
        "from": str(T0),
        "to": str(T0 + 3600000),
        "limit": 50,
        "context_columns": {},
    }
    data.update(changes)
    return data


@pytest.fixture
def client(test_user, clickhouse_source):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    client = APIClient()
    client.force_login(test_user)
    return client


def post(client, slug, path, data):
    return client.post(f"/ui/v1/sources/{slug}/{path}", data, format="json").json()


@pytest.mark.django_db
def test_data_passes_before_and_text_and_returns_the_cursor(client, clickhouse_source):
    cursor = {"time": "1762423200000000000", "skip": 2}
    with patch("telescope.fetchers.clickhouse.Fetcher.fetch_data") as fetch:
        fetch.return_value = DataResponse(rows=[], cursor={"time": "5", "skip": 1})
        response = post(
            client,
            clickhouse_source.slug,
            "data",
            body(before=cursor, text="connection refused"),
        )
    assert response["result"] is True, response
    assert response["data"]["cursor"] == {"time": "5", "skip": 1}
    request = fetch.call_args[0][0]
    assert request.before == cursor
    assert request.text == "connection refused"


@pytest.mark.django_db
def test_data_without_new_fields_is_unchanged(client, clickhouse_source):
    with patch("telescope.fetchers.clickhouse.Fetcher.fetch_data") as fetch:
        fetch.return_value = DataResponse(rows=[])
        response = post(client, clickhouse_source.slug, "data", body())
    assert response["result"] is True
    assert response["data"]["cursor"] is None
    request = fetch.call_args[0][0]
    assert request.before is None and request.text == ""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "before,error",
    [
        ({"time": "1 OR 1=1", "skip": 0}, "time: expected an integer"),
        ({"skip": 0}, "expected an object with a time"),
        ("x", "expected an object with a time"),
        ({"time": "1", "skip": -1}, "skip: expected an integer >= 0"),
        ({"time": "1", "skip": "2"}, "skip: expected an integer >= 0"),
    ],
)
def test_bad_cursor_is_a_validation_error(client, clickhouse_source, before, error):
    with patch("telescope.fetchers.clickhouse.Fetcher.fetch_data") as fetch:
        response = post(client, clickhouse_source.slug, "data", body(before=before))
    assert not fetch.called
    assert response["validation"]["result"] is False
    assert response["validation"]["columns"]["before"] == [error]


@pytest.mark.django_db
def test_uniq_source_needs_uniq_in_cursor(client, clickhouse_source):
    clickhouse_source.uniq_column = "hostname"
    clickhouse_source.save()
    response = post(
        client, clickhouse_source.slug, "data", body(before={"time": "1", "skip": 0})
    )
    assert response["validation"]["columns"]["before"] == [
        "uniq: required for this source"
    ]


@pytest.mark.django_db
def test_text_needs_a_body_column(client, clickhouse_source):
    clickhouse_source.columns.pop("message")
    clickhouse_source.save()
    response = post(client, clickhouse_source.slug, "data", body(text="x"))
    assert response["validation"]["columns"]["text"] == ["source has no body column"]


@pytest.mark.django_db
def test_text_and_paging_are_refused_for_docker(test_user, docker_source):
    rbac_manager.grant_source_role(docker_source, SourceRole.USER.value, user=test_user)
    client = APIClient()
    client.force_login(test_user)
    response = post(
        client,
        docker_source.slug,
        "data",
        body(columns="body", text="x", before={"time": "1"}),
    )
    errors = response["validation"]["columns"]
    assert errors["text"] == ["text search is not supported for docker sources"]
    assert errors["before"] == ["paging is not supported for docker sources"]


@pytest.mark.django_db
def test_graph_data_passes_text(client, clickhouse_source):
    with patch("telescope.fetchers.clickhouse.Fetcher.fetch_graph_data") as fetch:
        fetch.return_value = GraphDataResponse(timestamps=[], data={}, total=0)
        response = post(
            client,
            clickhouse_source.slug,
            "graphData",
            {
                "from": str(T0),
                "to": str(T0 + 1000),
                "group_by": "",
                "context_columns": {},
                "text": "x",
            },
        )
    assert response["result"] is True, response
    assert fetch.call_args[0][0].text == "x"
