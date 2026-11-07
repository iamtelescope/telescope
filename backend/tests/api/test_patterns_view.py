from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole

rbac_manager = RBACManager()
T0 = 1762423200000
RESULT = {"patterns": [], "buckets": [], "step": 1, "total": 0, "sample_size": 0}
FETCH = "telescope.views.source.patterns.fetch_patterns"


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def body(**changes):
    data = {"from": str(T0), "to": str(T0 + 3600000)}
    data.update(changes)
    return data


def post(client, source, data):
    return client.post(
        f"/ui/v1/sources/{source.slug}/patterns", data, format="json"
    ).json()


def grant(user, source):
    rbac_manager.grant_source_role(source, SourceRole.USER.value, user=user)
    return client_for(user)


@pytest.mark.django_db
def test_patterns_pass_request_to_fetcher(test_user, clickhouse_source):
    client = grant(test_user, clickhouse_source)
    with patch(FETCH, return_value=RESULT) as fetch:
        result = post(
            client,
            clickhouse_source,
            body(query="hostname='h1'", text="boom", column="hostname", sample=500),
        )
    assert result["result"] is True and result["data"] == RESULT
    request = fetch.call_args.args[0]
    assert request.source.slug == clickhouse_source.slug
    assert (request.time_from, request.time_to) == (T0, T0 + 3600000)
    assert (request.query, request.text) == ("hostname='h1'", "boom")
    assert (request.column, request.sample) == ("hostname", 500)


@pytest.mark.django_db
def test_patterns_default_to_the_body_column(test_user, clickhouse_source):
    client = grant(test_user, clickhouse_source)
    with patch(FETCH, return_value=RESULT) as fetch:
        post(client, clickhouse_source, body())
    request = fetch.call_args.args[0]
    assert (request.column, request.sample) == ("message", 10_000)


@pytest.mark.django_db
def test_patterns_work_for_docker(test_user, docker_source):
    client = grant(test_user, docker_source)
    with patch(FETCH, return_value=RESULT) as fetch:
        result = post(client, docker_source, body())
    assert result["result"] is True
    assert fetch.call_args.args[0].column == "message"


@pytest.mark.django_db
def test_patterns_work_for_kubernetes(test_user, kubernetes_source):
    client = grant(test_user, kubernetes_source)
    with patch(FETCH, return_value=RESULT) as fetch:
        result = post(client, kubernetes_source, body())
    assert result["result"] is True
    assert fetch.call_args.args[0].column == "body"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "changes, field",
    [
        ({"column": "nope"}, "column"),
        ({"sample": 0}, "sample"),
        ({"sample": 100_001}, "sample"),
        ({"query": "nope=1"}, "query"),
        ({"raw_query": "1=1"}, "non_field_errors"),
    ],
)
def test_patterns_validation(test_user, clickhouse_source, changes, field):
    client = grant(test_user, clickhouse_source)
    with patch(FETCH) as fetch:
        result = post(client, clickhouse_source, body(**changes))
    assert not fetch.called
    assert result["validation"]["result"] is False
    assert field in result["validation"]["columns"]


@pytest.mark.django_db
def test_patterns_need_a_body_column(test_user, clickhouse_source):
    clickhouse_source.columns.pop("message")
    clickhouse_source.save()
    client = grant(test_user, clickhouse_source)
    with patch(FETCH) as fetch:
        result = post(client, clickhouse_source, body())
    assert not fetch.called
    assert result["validation"]["columns"]["column"] == ["source has no body column"]


@pytest.mark.django_db
def test_patterns_need_source_use(hacker_user, clickhouse_source):
    with patch(FETCH) as fetch:
        result = post(client_for(hacker_user), clickhouse_source, body())
    assert not fetch.called
    assert result["errors"] == ["source not found"]


@pytest.mark.django_db
def test_patterns_report_fetch_errors(test_user, clickhouse_source):
    client = grant(test_user, clickhouse_source)
    with patch(FETCH, side_effect=RuntimeError("boom")):
        result = post(client, clickhouse_source, body())
    assert result["result"] is False and result["errors"] == ["boom"]
