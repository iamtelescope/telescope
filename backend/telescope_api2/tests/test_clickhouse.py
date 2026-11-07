"""Acceptance 2 against a real ClickHouse: system.query_log.log_comment names who asked."""

import json
import uuid
from datetime import datetime

import pytest

from telescope_alerts.evaluator import evaluate_alert
from telescope_alerts.models import Alert
from telescope_alerts.tests.conftest import otel_source

from telescope_api2.tests.conftest import session_client, token_client

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]


@pytest.fixture
def logs(ch_client, ch_settings_dict, otel_db):
    return otel_source(ch_client, ch_settings_dict, otel_db, "otel_logs", "otel-logs")


@pytest.fixture
def window(otel_facts):
    start = datetime.fromisoformat(otel_facts["start"][:26] + "+00:00")
    t0 = int(start.timestamp() * 1000)
    return t0, t0 + 24 * 3600 * 1000


def logged(ch_client, since, marker):
    ch_client.command("SYSTEM FLUSH LOGS")
    if not ch_client.command("EXISTS TABLE system.query_log"):
        pytest.skip("this ClickHouse server has no system.query_log")
    rows = ch_client.query(
        "SELECT log_comment, query FROM system.query_log"
        " WHERE event_time_microseconds >= %(since)s AND type = 'QueryFinish'"
        " AND log_comment LIKE %(marker)s ORDER BY event_time_microseconds",
        parameters={"since": since, "marker": f"%{marker}%"},
    ).result_rows
    return [(json.loads(c), q) for c, q in rows]


def chart(window, **changes):
    body = {"from": str(window[0]), "to": str(window[1]), "display": "line"}
    body.update(series=[{"agg": "count"}], granularity="1h", **changes)
    return body


def test_tile_query_is_attributed(root_user, logs, ch_client, window):
    since = ch_client.command("SELECT now64(6)")
    slug = f"ops-{uuid.uuid4().hex[:6]}"
    response = session_client(root_user).post(
        f"/ui/v1/sources/{logs.slug}/chartData?dashboard={slug}&tile=t7",
        chart(window),
        format="json",
    )
    assert response.json()["result"], response.json()
    rows = logged(ch_client, since, slug)
    assert len(rows) == 1 and "otel_logs" in rows[0][1]
    assert rows[0][0] == {
        "surface": "dashboard",
        "dashboard": slug,
        "tile": "t7",
        "source": logs.slug,
        "user": root_user.pk,
    }
    # debug.sql is what ClickHouse ran, before the driver's FORMAT suffix.
    (sql,) = response.json()["data"]["debug"]["sql"]
    assert rows[0][1].startswith(sql)


def test_api_query_is_attributed(root_user, logs, ch_client, window):
    since = ch_client.command("SELECT now64(6)")
    response = token_client(root_user).post(
        f"/api/v1/sources/{logs.slug}/chart", chart(window), format="json"
    )
    assert response.status_code == 200, response.content
    assert sum(v or 0 for v in response.json()["series"][0]["values"]) > 0
    rows = logged(ch_client, since, '"surface":"api"')
    assert [r[0] for r in rows] == [
        {"surface": "api", "source": logs.slug, "user": root_user.pk}
    ]


def test_alert_query_is_attributed(root_user, logs, ch_client, window):
    since = ch_client.command("SELECT now64(6)")
    alert = Alert.objects.create(
        name="errors",
        owner=root_user,
        kind="search",
        source_slug=logs.slug,
        query="SeverityText = 'ERROR'",
        series={"agg": "count"},
        interval="1h",
        threshold_type="above",
        threshold=1,
    )
    assert evaluate_alert(alert, at_ms=window[0] + 12 * 3600 * 1000) > 0
    rows = logged(ch_client, since, '"surface":"alert"')
    mine = [c for c, _ in rows if c.get("alert") == alert.pk]
    assert mine and all(
        c == {"surface": "alert", "alert": alert.pk, "user": root_user.pk} for c in mine
    )
