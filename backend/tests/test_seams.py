import inspect

import pytest

from django.apps import apps
from django.core.management import call_command

import telescope.fetchers.clickhouse as clickhouse_fetcher

FEATURE_APPS = ["telescope_alerts", "telescope_otel", "telescope_api2"]


def test_feature_apps_installed():
    for name in FEATURE_APPS:
        assert apps.is_installed(name)


def test_feature_apps_have_no_models():
    for name in FEATURE_APPS:
        assert list(apps.get_app_config(name).get_models()) == []


@pytest.mark.django_db
def test_no_pending_migrations():
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)


def test_clickhouse_queries_go_through_wrapper():
    # Only the wrapper itself may call client.query directly.
    assert inspect.getsource(clickhouse_fetcher).count("client.query(") == 1


def test_client_query_is_passthrough():
    calls = []

    class Client:
        def query(self, sql, **kw):
            calls.append((sql, kw))
            return "result"

    assert (
        clickhouse_fetcher._client_query(Client(), "SELECT 1", parameters={"a": 1})
        == "result"
    )
    assert calls == [("SELECT 1", {"parameters": {"a": 1}})]
