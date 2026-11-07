from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from telescope.models import APIToken
from telescope_api2 import throttle
from tests.fixtures import *  # noqa: F401,F403
from tests.integration.conftest import (  # noqa: F401
    ch_client,
    ch_settings,
    ch_settings_dict,
    otel_db,
    otel_facts,
)

T0 = 1762423200000


def pytest_collection_modifyitems(config, items):
    if ch_settings():
        return
    skip = pytest.mark.skip(
        reason="TELESCOPE_TEST_CH_HOST / TELESCOPE_TEST_CH_PORT not set"
    )
    for item in items:
        if "clickhouse" in item.keywords and "telescope_api2" in str(item.fspath):
            item.add_marker(skip)


def token_client(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {APIToken.create(user, 't').token}")
    return client


def session_client(user):
    # Some /ui/v1 views let an access error escape as a 500; report it, don't raise.
    client = APIClient(raise_request_exception=False)
    client.force_login(user)
    return client


@pytest.fixture
def fake_ch():
    """A ClickHouse client mock; the real _client_query still runs."""
    with patch("telescope.fetchers.clickhouse.ClickhouseConnect") as connect:
        client = MagicMock()
        client.query.return_value.result_rows = []
        connect.return_value.__enter__.return_value.client = client
        yield client


def search_body(**changes):
    body = {"columns": "hostname", "from": str(T0), "to": str(T0 + 3600000)}
    body.update(limit=10, query="", raw_query="", context_columns={})
    body.update(changes)
    return body


def chart_body(**changes):
    body = {
        "from": str(T0),
        "to": str(T0 + 3600000),
        "query": "",
        "raw_query": "",
        "display": "line",
        "series": [{"agg": "count"}],
        "granularity": "1m",
    }
    body.update(changes)
    return body


@pytest.fixture(autouse=True)
def fresh_rate_limit():
    # User ids repeat across tests, so each test starts with empty counters.
    throttle._hits.clear()


@pytest.fixture
def ch_source(clickhouse_source):
    # The shared fixture has no table, so no SQL could be generated.
    clickhouse_source.data = {"database": "db", "table": "logs"}
    clickhouse_source.save()
    return clickhouse_source
