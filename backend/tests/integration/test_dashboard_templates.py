"""Roadmap P4.2 acceptance: instantiated templates rendered against the P0.2 data and the
ClickHouse system tables of the test server."""

from datetime import datetime, timezone

import pytest
from rest_framework.test import APIClient

from telescope.models import Connection
from telescope_otel.provision import instantiate, load_templates
from tests.templates.helpers import make_source, otel_source

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]

HOUR = 3600 * 1000
SYSTEM_TABLES = {
    "query_log": "event_time",
    "metric_log": "event_time",
    "parts": "modification_time",
}


def columns(ch_client, database, table):
    return ch_client.query(
        "SELECT name, type FROM system.columns WHERE database = %(d)s AND table = %(t)s"
        " ORDER BY position",
        parameters={"d": database, "t": table},
    ).result_rows


@pytest.fixture
def conn(ch_settings_dict):
    return Connection.objects.create(
        kind="clickhouse",
        name="test",
        data={
            "host": ch_settings_dict["host"],
            "port": ch_settings_dict["port"],
            "user": ch_settings_dict["username"],
            "password": ch_settings_dict["password"],
            "ssl": False,
            "verify": False,
        },
    )


@pytest.fixture
def otel(conn, ch_client, otel_db):
    return {
        role: otel_source(
            conn, role, table, columns(ch_client, otel_db, table), otel_db
        )
        for role, table in [
            ("traces", "otel_traces"),
            ("logs", "otel_logs"),
            ("metrics", "otel_metrics_gauge"),
        ]
    }


@pytest.fixture
def day(otel_facts):
    start = datetime.fromisoformat(otel_facts["start"][:26] + "+00:00")
    t0 = int(start.timestamp() * 1000)
    return t0, t0 + 24 * HOUR


def bound(slug, sources):
    template = load_templates()[slug]
    return instantiate(
        template, {r: sources[r] for r in template["roles"] if r in sources}
    )


def render(user, data, tile_id, window):
    """Chart data of one tile, as the dashboard page requests it with every variable empty."""
    tile = next(t for t in data["tiles"] if t["id"] == tile_id)
    chart = tile["chart"]
    params = {v["name"]: [] if v.get("multi") else "" for v in data["variables"]}
    body = {
        "from": str(window[0]),
        "to": str(window[1]),
        "query": chart["query"],
        "dashboard_query": data["query"],
        "raw_query": "",
        "context_columns": {},
        "display": chart["display"],
        "series": chart["series"],
        "group_by": chart["group_by"],
        "granularity": chart["granularity"],
        "limit": chart["limit"],
        "params": params,
    }
    client = APIClient()
    client.force_login(user)
    result = client.post(
        f"/ui/v1/sources/{chart['source']}/chartData", body, format="json"
    ).json()
    assert result["result"] is True, (tile_id, result)
    return result["data"]


def render_all(user, data, window):
    return {
        t["id"]: render(user, data, t["id"], window)
        for t in data["tiles"]
        if t["chart"]["display"] != "text"
    }


def values(chart, group, index=0):
    """Timestamps and values of one series of a time chart."""
    item = next(
        s for s in chart["series"] if s["group"] == group and s["series_index"] == index
    )
    return list(zip(chart["timestamps"], item["values"]))


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M")


def test_services_ranks_checkout_first_and_shows_the_payment_spike(
    root_user, otel, day, otel_facts
):
    data = bound("services", otel)
    out = render_all(root_user, data, day)
    top = out["top-endpoints"]["rows"][0]
    assert top["groups"] == ["frontend", otel_facts["slow_endpoint"]["span_name"]]

    spike = otel_facts["error_spike"]
    payment = values(out["errors-per-service"], "payment")
    peak = max(payment, key=lambda p: p[1])
    assert spike["from"][:16] <= iso(peak[0]) < spike["to"][:16]
    counts = sorted(v for _, v in payment)
    assert peak[1] > 5 * counts[len(counts) // 2]
    logs = values(out["error-logs"], "payment")
    assert (
        spike["from"][:16] <= iso(max(logs, key=lambda p: p[1])[0]) < spike["to"][:16]
    )


def test_kubernetes_puts_the_restarting_pod_first(root_user, otel, day, otel_facts):
    data = bound("kubernetes", otel)
    out = render_all(root_user, data, day)
    pod = otel_facts["restarting_pod"]
    first = out["pods"]["rows"][0]
    assert first["groups"] == [pod["pod"], pod["namespace"], pod["node"]]
    assert first["values"][0] == pod["restarts"]
    assert out["pod-cpu"]["series"][0]["group"] == pod["pod"]
    assert out["restarts"]["series"][0]["group"] == pod["pod"]


@pytest.mark.parametrize(
    "slug",
    ["jvm-runtime", "go-runtime", "nodejs-runtime", "python-runtime", "dotnet-runtime"],
)
def test_runtime_templates_render(slug, root_user, otel, day):
    data = bound(slug, otel)
    assert render_all(root_user, data, day)


def test_clickhouse_system_template_renders(root_user, conn, ch_client):
    sources = {}
    for table, time_column in SYSTEM_TABLES.items():
        found = columns(ch_client, "system", table)
        if found:
            sources[table] = make_source(
                conn, f"system-{table}", "system", table, found, time_column
            )
    assert "parts" in sources
    ch_client.command("SYSTEM FLUSH LOGS")
    now = int(datetime.now().timestamp() * 1000)
    data = instantiate(load_templates()["clickhouse"], sources)
    out = render_all(root_user, data, (now - 7 * 24 * HOUR, now))
    parts = ch_client.query(
        "SELECT count() c FROM system.parts WHERE active"
        " AND modification_time >= now() - INTERVAL 7 DAY"
        " GROUP BY database, table, partition ORDER BY c DESC LIMIT 1"
    ).result_rows
    assert out["parts-per-partition"]["rows"][0]["values"][0] == parts[0][0]
    if "query_log" in sources:
        assert out["queries"]["value"] > 0
        assert out["slowest"]["rows"] and out["by-kind"]["series"]
    if "metric_log" in sources:
        assert any(v for s in out["memory"]["series"] for v in s["values"])
        assert any(v for s in out["cpu"]["series"] for v in s["values"])
