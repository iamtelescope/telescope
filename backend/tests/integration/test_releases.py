"""P3.3 release markers on the P0.2 data: the planted checkout deploy at start+16h."""

from datetime import datetime
from unittest.mock import patch

import pytest

from telescope_otel.releases import fetch_releases
from tests.integration.test_trace_view import connection, make_source  # noqa: F401

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]
HOUR = 3600_000
COUNT = [{"agg": "count"}]


def ms(iso):
    return int(datetime.fromisoformat(iso[:26] + "+00:00").timestamp() * 1000)


@pytest.fixture
def window(otel_facts):
    return ms(otel_facts["start"]), ms(otel_facts["end"])


@pytest.mark.parametrize("table", ["otel_logs", "otel_traces"])
def test_checkout_deploy_is_one_marker(
    connection, otel_db, otel_facts, window, table
):  # noqa: F811
    source = make_source(f"p33-{table}", connection, otel_db, table, {})
    deploy = otel_facts["deploy"]
    start, end = window
    found = fetch_releases(source, "ServiceName = 'checkout'", "", COUNT, start, end)
    assert [(r["service"], r["version"]) for r in found] == [("checkout", "1.5.0")]
    assert 0 <= found[0]["time"] - ms(deploy["at"]) < 60_000
    # No other service changes version, so an unscoped tile shows the same single marker.
    assert fetch_releases(source, "", "", COUNT, start, end) == found
    assert fetch_releases(source, "ServiceName = 'cart'", "", COUNT, start, end) == []
    # A tile of checkout errors still dates the release by every checkout row.
    errors = [
        {"agg": "count", "where": "ServiceName = 'checkout' and SeverityText = 'ERROR'"}
    ]
    if table == "otel_traces":
        errors = [
            {
                "agg": "count",
                "where": "ServiceName = 'checkout' and StatusCode = 'Error'",
            }
        ]
    assert fetch_releases(source, "", "", errors, start, end) == found
    # A window opening after the deploy has no release in it.
    assert fetch_releases(source, "", "", COUNT, start + 17 * HOUR, end) == []


RELEASE_DB = "telescope_test_p33_releases"
MIN = 60_000


@pytest.fixture
def release_logs(ch_client, otel_db, connection):  # noqa: F811
    ch_client.command(f"CREATE DATABASE IF NOT EXISTS {RELEASE_DB}")
    ch_client.command(f"DROP TABLE IF EXISTS {RELEASE_DB}.otel_logs")
    ch_client.command(f"CREATE TABLE {RELEASE_DB}.otel_logs AS `{otel_db}`.otel_logs")
    yield make_source("p33-release-limit", connection, RELEASE_DB, "otel_logs", {})
    ch_client.command(f"DROP DATABASE IF EXISTS {RELEASE_DB}")


def test_release_limit_keeps_the_newest_releases(release_logs, ch_client):
    start = 1767225600000
    rows = [
        ("cart", "2.0.0", 0),
        ("checkout", "1.4.0", 1),
        ("api", "3.0.0", 5),
        ("cart", "2.1.0", 10),
        ("checkout", "1.5.0", 20),
        ("checkout", "1.6.0", 30),
        ("checkout", "1.7.0", 40),
    ]
    ch_client.insert(
        f"{RELEASE_DB}.otel_logs",
        [
            [
                datetime.utcfromtimestamp((start + m * MIN) / 1000),
                s,
                {"service.version": v},
            ]
            for s, v, m in rows
        ],
        column_names=["Timestamp", "ServiceName", "ResourceAttributes"],
    )
    end = start + 60 * MIN

    def found(time_from):
        result = fetch_releases(release_logs, "", "", COUNT, time_from, end)
        return [
            (r["service"], r["version"], (r["time"] - start) // MIN) for r in result
        ]

    # Each service's first version was already running; the rest are releases.
    assert found(start) == [
        ("cart", "2.1.0", 10),
        ("checkout", "1.5.0", 20),
        ("checkout", "1.6.0", 30),
        ("checkout", "1.7.0", 40),
    ]
    assert found(start + 15 * MIN) == [
        ("checkout", "1.5.0", 20),
        ("checkout", "1.6.0", 30),
        ("checkout", "1.7.0", 40),
    ]
    # Over the row limit, the newest releases are the ones kept.
    with patch("telescope_otel.releases.MAX_ROWS", 2):
        assert found(start) == [("checkout", "1.6.0", 30), ("checkout", "1.7.0", 40)]
