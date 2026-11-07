"""Fixtures for tests against a real ClickHouse loaded by dev/otel/generate.py.

Tests marked @pytest.mark.clickhouse are skipped unless TELESCOPE_TEST_CH_HOST and TELESCOPE_TEST_CH_PORT
(HTTP port) are set. Optional: TELESCOPE_TEST_CH_USER, TELESCOPE_TEST_CH_PASSWORD, TELESCOPE_TEST_OTEL_DB.
"""

import json
import os
from pathlib import Path

import pytest

FACTS_PATH = Path(__file__).resolve().parents[3] / "dev" / "otel" / "facts.json"
OTEL_TABLES = [
    "otel_logs",
    "otel_traces",
    "otel_metrics_gauge",
    "otel_metrics_sum",
    "otel_metrics_histogram",
]


def ch_settings():
    host, port = os.environ.get("TELESCOPE_TEST_CH_HOST"), os.environ.get(
        "TELESCOPE_TEST_CH_PORT"
    )
    if not host or not port:
        return None
    return {
        "host": host,
        "port": int(port),
        "username": os.environ.get("TELESCOPE_TEST_CH_USER", "default"),
        "password": os.environ.get("TELESCOPE_TEST_CH_PASSWORD", ""),
    }


def pytest_collection_modifyitems(config, items):
    if ch_settings():
        return
    skip = pytest.mark.skip(
        reason="TELESCOPE_TEST_CH_HOST / TELESCOPE_TEST_CH_PORT not set"
    )
    for item in items:
        if "clickhouse" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def ch_settings_dict():
    settings = ch_settings()
    if not settings:
        pytest.skip("TELESCOPE_TEST_CH_HOST / TELESCOPE_TEST_CH_PORT not set")
    return settings


@pytest.fixture(scope="session")
def ch_client(ch_settings_dict):
    import clickhouse_connect

    client = clickhouse_connect.get_client(**ch_settings_dict)
    yield client
    client.close()


@pytest.fixture(scope="session")
def otel_facts():
    return json.loads(FACTS_PATH.read_text())


@pytest.fixture(scope="session")
def otel_db(ch_client, otel_facts):
    """Name of the database holding the P0.2 data; fails if it does not match facts.json."""
    db = os.environ.get("TELESCOPE_TEST_OTEL_DB", "otel")
    for table in OTEL_TABLES:
        exists = ch_client.command(f"EXISTS TABLE `{db}`.`{table}`")
        count = (
            ch_client.command(f"SELECT count() FROM `{db}`.`{table}`")
            if exists
            else None
        )
        if count != otel_facts["rows"][table]:
            pytest.fail(
                f"{db}.{table} has {count} rows, facts.json expects {otel_facts['rows'][table]}; "
                "load it with: python dev/otel/generate.py",
                pytrace=False,
            )
    return db
