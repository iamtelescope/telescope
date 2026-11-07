"""Roadmap P1.1 acceptance against a native ClickHouse loaded with the P0.2 OTel kit."""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from rest_framework.test import APIClient

from telescope.models import Dashboard
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope_alerts.definition import alert_data, resolve
from telescope_alerts.evaluator import evaluate_alert, query_window
from telescope_alerts.models import Alert, AlertChannel, AlertHistory
from telescope_alerts.scheduler import tick

pytestmark = pytest.mark.clickhouse

MIN = 60_000
BACKEND = Path(__file__).resolve().parents[2]
rbac_manager = RBACManager()


def ms(iso):
    return int(
        datetime.fromisoformat(iso[:26].replace("Z", "") + "+00:00").timestamp() * 1000
    )


@pytest.fixture
def spike(otel_facts):
    s = otel_facts["error_spike"]
    return {**s, "from_ms": ms(s["from"]), "to_ms": ms(s["to"])}


def search_alert(owner, source, query, **kw):
    fields = dict(
        name="payment errors",
        owner=owner,
        kind="search",
        source_slug=source.slug,
        query=query,
        series={"agg": "count"},
        interval="5m",
        threshold_type="above",
        threshold=50,
    )
    fields.update(kw)
    return Alert.objects.create(**fields)


def states(alert, group=""):
    return list(
        AlertHistory.objects.filter(alert=alert, group_key=group)
        .order_by("window_start")
        .values_list("window_start", "state", "value")
    )


@pytest.mark.django_db
def test_search_alert_fires_on_spike_and_resolves(
    root_user, otel_logs_source, spike, receiver, alerts_config
):
    start = spike["from_ms"] - 15 * MIN
    alert = search_alert(
        root_user,
        otel_logs_source,
        spike["query"],
        last_evaluated_window=start - 5 * MIN,
    )
    alert.channels.add(
        AlertChannel.objects.create(
            kind="webhook", name="r", config={"url": receiver.url}
        )
    )
    # Two ticks: backfill is capped at 10 windows per tick.
    evaluate_alert(alert, start + 10 * 5 * MIN)
    evaluate_alert(alert, start + 14 * 5 * MIN)
    rows = states(alert)
    assert len(rows) == 14
    firing = [w for w, state, _ in rows if state == "ALERT"]
    assert firing == [spike["from_ms"], spike["from_ms"] + 5 * MIN]
    assert [v for w, _, v in rows if w in firing] == spike["error_logs_per_5m_spike"]
    assert {s for w, s, _ in rows if w not in firing} == {"OK"}
    assert (
        max(v for w, _, v in rows if w not in firing)
        <= spike["error_logs_per_5m_max_outside"]
    )
    bodies = receiver.json()
    assert [(b["status"], b["startTime"]) for b in bodies] == [
        ("firing", spike["from_ms"]),
        ("resolved", spike["to_ms"]),
    ]
    assert bodies[0]["sourceQuery"] == spike["query"]


@pytest.mark.django_db
def test_grouped_alert_only_payment_fires(root_user, otel_logs_source, spike):
    start = spike["from_ms"] - 10 * MIN
    alert = search_alert(
        root_user,
        otel_logs_source,
        "SeverityText='ERROR'",
        group_by="ServiceName",
        last_evaluated_window=start - 5 * MIN,
    )
    evaluate_alert(alert, start + 6 * 5 * MIN)
    alerting = set(
        AlertHistory.objects.filter(alert=alert, state="ALERT").values_list(
            "group_key", flat=True
        )
    )
    assert alerting == {"payment"}
    groups = set(
        AlertHistory.objects.filter(alert=alert).values_list("group_key", flat=True)
    )
    assert {"payment", "frontend", "checkout"} <= groups
    alert.refresh_from_db()
    assert alert.state == "OK" and alert.firing_groups == []


@pytest.fixture
def checkout_dashboard(root_user, otel_traces_source):
    chart = {
        "source": otel_traces_source.slug,
        "display": "line",
        "series": [{"agg": "quantile", "column": "Duration", "level": 0.95}],
        "query": "SpanName='POST /api/checkout'",
        "raw_query": "",
        "context_columns": {},
        "group_by": "",
        "granularity": "auto",
        "limit": 10,
    }
    return Dashboard.objects.create(
        slug="checkout-latency",
        name="Checkout latency",
        owner=root_user,
        updated_by=root_user,
        data={
            "time": {"from": "now-1h", "to": "now"},
            "query": "",
            "refresh": "off",
            "tiles": [{"id": "p95", "x": 0, "y": 0, "w": 12, "h": 8, "chart": chart}],
        },
    )


def tile_alert(owner, dashboard, **kw):
    fields = dict(
        name="checkout p95",
        owner=owner,
        kind="tile",
        dashboard=dashboard,
        tile_id="p95",
        interval="5m",
        threshold_type="above",
        threshold=1e9,
    )
    fields.update(kw)
    return Alert.objects.create(**fields)


@pytest.mark.django_db
def test_tile_quantile_alert_and_range_bounds(
    root_user, checkout_dashboard, otel_facts
):
    w = ms(otel_facts["start"]) + 11 * 60 * MIN
    alert = tile_alert(root_user, checkout_dashboard, last_evaluated_window=w - 5 * MIN)
    assert evaluate_alert(alert, w + 5 * MIN) == 1
    ((_, state, value),) = states(alert)
    assert state == "ALERT" and value > 1e9
    alert.refresh_from_db()
    assert alert.source_slug == "otel-traces"

    aq = resolve(root_user, alert_data(alert))
    assert query_window(aq, w, w + 5 * MIN) == {"": value}
    cases = [
        ("between", value, value + 1, "ALERT"),
        ("between", value - 1, value, "ALERT"),
        ("between", value + 1e-3, value + 1, "OK"),
        ("not_between", value, value + 1, "OK"),
        ("not_between", value - 1, value, "OK"),
        ("not_between", value + 1e-3, value + 1, "ALERT"),
    ]
    for kind, low, high, expected in cases:
        a = tile_alert(
            root_user,
            checkout_dashboard,
            threshold_type=kind,
            threshold=low,
            threshold_max=high,
            last_evaluated_window=w - 5 * MIN,
        )
        evaluate_alert(a, w + 5 * MIN)
        assert states(a)[0][1] == expected, (kind, low, high)


@pytest.mark.django_db
def test_revoked_owner_gets_source_not_found(test_user, otel_logs_source, spike):
    rbac_manager.grant_source_role(
        otel_logs_source, SourceRole.USER.value, user=test_user
    )
    w = spike["from_ms"]
    alert = search_alert(
        test_user, otel_logs_source, spike["query"], last_evaluated_window=w - 5 * MIN
    )
    evaluate_alert(alert, w + 5 * MIN)
    assert states(alert)[0][1] == "ALERT"
    rbac_manager.revoke_source_role(
        otel_logs_source, SourceRole.USER.value, user=test_user
    )
    evaluate_alert(alert, w + 10 * MIN)
    alert.refresh_from_db()
    assert alert.state == "ERROR" and alert.last_error == "source not found"
    assert states(alert)[-1][1] == "ERROR"


@pytest.mark.django_db
def test_preview_matches_evaluation(root_user, otel_logs_source, spike):
    client = APIClient()
    client.force_login(root_user)
    body = {
        "name": "p",
        "kind": "search",
        "source": otel_logs_source.slug,
        "query": spike["query"],
        "series": {"agg": "count"},
        "interval": "5m",
        "threshold_type": "above",
        "threshold": 50,
        "now": str(spike["to_ms"] + 30 * MIN),
    }
    doc = client.post("/ui/v1/alerts/preview", body, format="json").json()
    assert doc["result"], doc
    data = doc["data"]
    assert len(data["windows"]) == 24 and data["step_ms"] == 5 * MIN
    assert data["windows"][-1] == spike["to_ms"] + 25 * MIN
    (series,) = data["series"]
    fire = [w for w, f in zip(data["windows"], series["would_fire"]) if f]
    assert fire == [spike["from_ms"], spike["from_ms"] + 5 * MIN]
    spike_values = [v for w, v in zip(data["windows"], series["values"]) if w in fire]
    assert spike_values == spike["error_logs_per_5m_spike"]


@pytest.mark.django_db
def test_tick_runs_alerts(root_user, otel_logs_source, spike):
    w = spike["from_ms"]
    alert = search_alert(
        root_user, otel_logs_source, spike["query"], last_evaluated_window=w - 5 * MIN
    )
    assert tick("t", 60, w + 10 * MIN) == 2
    assert tick("other", 60, w + 10 * MIN) == -1
    assert [s for _, s, _ in states(alert)] == ["ALERT", "ALERT"]


SETUP = """
import json, os
from django.contrib.auth.models import User
from telescope.models import Connection, Source
from telescope_alerts.models import Alert, AlertChannel
p = json.loads(os.environ["ALERT_TEST_SETUP"])
user = User.objects.create(username="root", is_superuser=True)
conn = Connection.objects.create(kind="clickhouse", name="ch", description="", data=p["conn"])
source = Source.create(kind="clickhouse", data={**p["source"], "conn": conn})
channel = AlertChannel.objects.create(kind="webhook", name="r", config={"url": p["url"]})
for group_by in ["", "ServiceName"]:
    alert = Alert.objects.create(name="a" + group_by, owner=user, kind="search", source_slug=source.slug,
        query=p["query"], group_by=group_by, series={"agg": "count"}, interval="5m",
        threshold_type="above", threshold=50, last_evaluated_window=p["last"])
    alert.channels.add(channel)
"""


@pytest.mark.django_db
def test_two_schedulers_write_no_duplicates(
    tmp_path, otel_logs_source, spike, receiver
):
    db = tmp_path / "db.sqlite3"
    config = tmp_path / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "django": {
                    "SECRET_KEY": "test",
                    "DATABASES": {
                        "default": {
                            "ENGINE": "django.db.backends.sqlite3",
                            "NAME": str(db),
                            "OPTIONS": {"timeout": 20},
                        }
                    },
                },
                "alerts": {"allow_private_webhook_targets": True},
                "logging": {
                    "levels": {
                        "all": "WARNING",
                        "telescope": "WARNING",
                        "django": "WARNING",
                    }
                },
            }
        )
    )
    source = {
        k: getattr(otel_logs_source, k)
        for k in [
            "slug",
            "name",
            "description",
            "time_column",
            "date_column",
            "uniq_column",
            "severity_column",
            "columns",
            "default_chosen_columns",
            "data",
        ]
    }
    env = {
        **os.environ,
        "TELESCOPE_CONFIG_FILE": str(config),
        "ALERT_TEST_SETUP": json.dumps(
            {
                "conn": otel_logs_source.conn.data,
                "source": source,
                "url": receiver.url,
                "query": spike["query"],
                "last": spike["from_ms"] - 25 * MIN,
            }
        ),
    }
    manage = [sys.executable, "manage.py"]
    run = dict(cwd=BACKEND, env=env, capture_output=True, text=True, timeout=300)
    assert subprocess.run(manage + ["migrate", "-v", "0"], **run).returncode == 0
    setup = subprocess.run(manage + ["shell", "-c", SETUP], **run)
    assert setup.returncode == 0, setup.stderr[-2000:]

    now = str(spike["from_ms"] + 25 * MIN)
    procs = [
        subprocess.Popen(
            manage + ["telescope_scheduler", "--now", now, "--holder", f"s{i}"],
            cwd=BACKEND,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for i in range(2)
    ]
    outputs = [p.communicate(timeout=300) for p in procs]
    assert all(p.returncode == 0 for p in procs), outputs
    # One took the lease and wrote every window; the other was refused or found nothing due.
    texts = [out.strip() for out, _ in outputs]
    assert "18 windows evaluated" in texts, texts
    texts.remove("18 windows evaluated")
    assert texts[0] in ("0 windows evaluated", "lease held by another scheduler"), texts

    with sqlite3.connect(db) as con:
        rows = con.execute(
            "SELECT alert_id, group_key, window_start FROM telescope_alerts_alerthistory"
        ).fetchall()
        firing = con.execute(
            "SELECT a.name, h.group_key FROM telescope_alerts_alerthistory h "
            "JOIN telescope_alerts_alert a ON a.id = h.alert_id WHERE h.state = 'ALERT'"
        ).fetchall()
    assert len(rows) == len(set(rows))
    ungrouped = [r for r in rows if r[1] == "" and r[0] == min(x[0] for x in rows)]
    assert len(ungrouped) == 9
    assert sorted(firing) == [
        ("a", ""),
        ("a", ""),
        ("aServiceName", "payment"),
        ("aServiceName", "payment"),
    ]
    # One firing per alert: notifications are sent by whichever process wrote the window.
    statuses = sorted((b["alertName"], b["status"]) for b in receiver.json())
    assert statuses == [
        ("a", "firing"),
        ("a", "resolved"),
        ("aServiceName", "firing"),
        ("aServiceName", "resolved"),
    ]
