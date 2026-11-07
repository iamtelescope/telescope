from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole

rbac_manager = RBACManager()
T0 = 1762423200000
RESULT = {
    "facets": {"hostname": [{"value": "h1", "count": 3}]},
    "map_keys": {},
    "more": [],
    "total_sampled": 3,
    "sampled": False,
}


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def body(**changes):
    data = {"from": str(T0), "to": str(T0 + 3600000), "columns": ["hostname"]}
    data.update(changes)
    return data


def post(client, source, data):
    return client.post(
        f"/ui/v1/sources/{source.slug}/facets", data, format="json"
    ).json()


@pytest.fixture
def user_client(test_user, clickhouse_source):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    return client_for(test_user)


@pytest.mark.django_db
def test_facets_passes_request_to_fetcher(user_client, clickhouse_source):
    with patch(
        "telescope.views.source.facets.fetch_facets", return_value=RESULT
    ) as fetch:
        result = post(
            user_client,
            clickhouse_source,
            body(
                query="hostname='h1'",
                columns=["hostname", "hostname", "level"],
                limit=5,
                sample=200,
            ),
        )
    assert result["result"] is True
    assert result["data"] == RESULT
    request = fetch.call_args.args[0]
    assert request.source.slug == clickhouse_source.slug
    assert (request.time_from, request.time_to) == (T0, T0 + 3600000)
    assert request.query == "hostname='h1'"
    assert request.columns == ["hostname", "level"]
    assert (request.limit, request.sample, request.map_keys) == (5, 200, {})


@pytest.mark.django_db
def test_facets_defaults(user_client, clickhouse_source):
    with patch(
        "telescope.views.source.facets.fetch_facets", return_value=RESULT
    ) as fetch:
        post(user_client, clickhouse_source, body())
    request = fetch.call_args.args[0]
    assert (request.limit, request.sample, request.text) == (10, 100_000, "")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "changes, field, message",
    [
        ({"columns": ["nope"]}, "columns", "unknown column: nope"),
        ({"map_keys": {"nope": ["a"]}}, "map_keys", "unknown column: nope"),
        ({"limit": 0}, "limit", None),
        ({"sample": 0}, "sample", None),
        ({"query": "nope=1"}, "query", None),
        ({"columns": ["hostname"] * 51}, "columns", None),
    ],
)
def test_facets_validation(user_client, clickhouse_source, changes, field, message):
    with patch("telescope.views.source.facets.fetch_facets") as fetch:
        result = post(user_client, clickhouse_source, body(**changes))
    assert not fetch.called
    assert result["validation"]["result"] is False
    errors = result["validation"]["columns"][field]
    if message:
        assert errors == [message]


@pytest.mark.django_db
def test_facets_text_needs_a_body_column(user_client, clickhouse_source):
    clickhouse_source.columns.pop("message")
    clickhouse_source.save()
    with patch("telescope.views.source.facets.fetch_facets") as fetch:
        result = post(user_client, clickhouse_source, body(text="x"))
    assert not fetch.called
    assert result["validation"]["columns"]["text"] == [
        "text search needs a body column"
    ]


@pytest.mark.django_db
def test_facets_text_uses_the_explorer_body_column(user_client, clickhouse_source):
    with patch(
        "telescope.views.source.facets.fetch_facets", return_value=RESULT
    ) as fetch:
        post(user_client, clickhouse_source, body(text="x"))
    assert fetch.called


@pytest.mark.django_db
def test_facets_raw_query_needs_permission(user_client, clickhouse_source):
    with patch("telescope.views.source.facets.fetch_facets") as fetch:
        result = post(user_client, clickhouse_source, body(raw_query="1=1"))
    assert not fetch.called
    assert result["validation"]["result"] is False


@pytest.mark.django_db
def test_facets_need_source_use(hacker_user, clickhouse_source):
    with patch("telescope.views.source.facets.fetch_facets") as fetch:
        result = post(client_for(hacker_user), clickhouse_source, body())
    assert not fetch.called
    assert result["result"] is False
    assert result["errors"] == ["source not found"]


@pytest.mark.django_db
def test_facets_fetch_error(user_client, clickhouse_source):
    with patch(
        "telescope.views.source.facets.fetch_facets", side_effect=ValueError("boom")
    ):
        result = post(user_client, clickhouse_source, body())
    assert result["result"] is False
    assert result["errors"] == ["boom"]
