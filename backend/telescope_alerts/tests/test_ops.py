"""Roadmap P2.1 alert operations: silence, enable/disable, schedule, list paging, evaluations, markers,
test notification and saved-view tags/favorites."""

from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from django.utils import timezone

from telescope.models import SavedView
from telescope_alerts.evaluator import due_windows, evaluate_alert, latest_window_start
from telescope_alerts.models import Alert, AlertHistory, SavedViewFavorite
from telescope_alerts.scheduler import tick
from telescope_alerts.tests.test_api import call, client_for, search_alert
from telescope_alerts.tests.test_evaluator import (
    MIN,
    T0,
    fake_values,  # noqa: F401
    history,
    make_alert,
    webhook,
)

STEP = 5 * MIN


def utc(ms):
    return datetime.fromtimestamp(ms / 1000, tz=dt_timezone.utc)


def silence(alert, delta):
    alert.silenced_until = timezone.now() + delta
    alert.save(update_fields=["silenced_until"])


@pytest.mark.django_db
def test_silenced_alert_writes_history_but_sends_nothing(
    root_user, clickhouse_source, fake_values, receiver, alerts_config
):
    alert = make_alert(root_user, clickhouse_source)
    alert.channels.add(webhook(receiver))
    for i, v in enumerate([3, 60, 70, 80, 4]):
        fake_values[T0 + i * STEP] = {"": float(v)}
    silence(alert, timedelta(hours=1))
    assert evaluate_alert(alert, T0 + 3 * STEP) == 3
    assert [h[2] for h in history(alert)] == ["OK", "ALERT", "ALERT"]
    assert receiver.requests == []
    assert not AlertHistory.objects.exclude(notified_at=None).exists()
    alert.refresh_from_db()
    assert alert.state == "ALERT" and alert.firing_groups == []
    # After `until` the held firing is sent once, then the resolve.
    silence(alert, timedelta(seconds=-1))
    assert evaluate_alert(alert, T0 + 5 * STEP) == 2
    assert [(b["status"], b["startTime"]) for b in receiver.json()] == [
        ("firing", T0 + 3 * STEP),
        ("resolved", T0 + 4 * STEP),
    ]


@pytest.mark.django_db
def test_resolve_during_silence_is_sent_after_it(
    root_user, clickhouse_source, fake_values, receiver, alerts_config
):
    alert = make_alert(root_user, clickhouse_source)
    alert.channels.add(webhook(receiver))
    for i, v in enumerate([3, 60, 4, 5]):
        fake_values[T0 + i * STEP] = {"": float(v)}
    evaluate_alert(alert, T0 + 2 * STEP)
    assert [b["status"] for b in receiver.json()] == ["firing"]
    silence(alert, timedelta(hours=1))
    evaluate_alert(alert, T0 + 3 * STEP)
    assert len(receiver.requests) == 1
    silence(alert, timedelta(seconds=-1))
    evaluate_alert(alert, T0 + 4 * STEP)
    assert [(b["status"], b["startTime"]) for b in receiver.json()] == [
        ("firing", T0 + STEP),
        ("resolved", T0 + 3 * STEP),
    ]


@pytest.mark.django_db
def test_disabled_alert_is_skipped_and_not_overwritten(
    root_user, clickhouse_source, fake_values, monkeypatch
):
    alert = make_alert(root_user, clickhouse_source, state="DISABLED")
    assert tick("t", 120, T0 + 3 * STEP) == 0
    assert not AlertHistory.objects.exists()
    # A disable that lands while a window is being queried wins over the evaluator's write.
    alert.state = "OK"
    alert.save()
    from telescope_alerts import evaluator

    def disable_then_query(aq, start, end):
        Alert.objects.filter(pk=alert.pk).update(state="DISABLED")
        return {"": 1.0}

    monkeypatch.setattr(evaluator, "query_window", disable_then_query)
    assert evaluate_alert(alert, T0 + 2 * STEP) == 0
    alert.refresh_from_db()
    assert alert.state == "DISABLED"
    monkeypatch.setattr(evaluator, "query_window", lambda *a: 1 / 0)
    Alert.objects.filter(pk=alert.pk).update(state="OK")
    alert.refresh_from_db()
    Alert.objects.filter(pk=alert.pk).update(state="DISABLED")
    evaluate_alert(alert, T0 + 2 * STEP)
    assert Alert.objects.get(pk=alert.pk).state == "DISABLED"


def test_schedule_offset_and_start():
    assert latest_window_start("1h", T0 + 30 * MIN, 15 * MIN) == T0 - 45 * MIN
    assert latest_window_start("1h", T0 + 10 * MIN, 15 * MIN) == T0 - 105 * MIN
    alert = Alert(interval="1h", schedule_offset_minutes=15)
    assert due_windows(alert, T0 + 16 * MIN) == [T0 - 45 * MIN]
    start = T0 + 7 * MIN
    alert = Alert(interval="5m", schedule_start_at=utc(start))
    assert due_windows(alert, start + 4 * MIN) == []
    assert due_windows(alert, start + 5 * MIN) == [start]
    # Backfill never reaches before the start.
    alert.last_evaluated_window = start - 50 * MIN
    assert due_windows(alert, start + 11 * MIN) == [start, start + 5 * MIN]


@pytest.mark.django_db
def test_schedule_validation_and_reset(root_user, clickhouse_source):
    client = client_for(root_user)
    doc = call(client, "post", "ui/v1/alerts", search_alert(schedule_offset_minutes=5))
    assert doc["validation"]["fields"]["schedule_offset_minutes"]
    doc = call(
        client,
        "post",
        "ui/v1/alerts",
        search_alert(
            schedule_offset_minutes=2, schedule_start_at="2026-01-01T00:00:00Z"
        ),
    )
    assert doc["validation"]["fields"]["schedule_offset_minutes"]
    created = call(
        client,
        "post",
        "ui/v1/alerts",
        search_alert(schedule_start_at="2026-01-01T00:03:00Z"),
    )["data"]
    assert created["schedule_start_at"].startswith("2026-01-01T00:03:00")
    Alert.objects.filter(pk=created["id"]).update(last_evaluated_window=T0)
    updated = call(
        client,
        "patch",
        f"ui/v1/alerts/{created['id']}",
        search_alert(schedule_offset_minutes=3),
    )["data"]
    assert updated["schedule_offset_minutes"] == 3
    assert updated["schedule_start_at"] is None
    assert updated["last_evaluated_window"] is None


@pytest.mark.django_db
def test_silence_and_enable_api(root_user, test_user, clickhouse_source):
    client = client_for(root_user)
    alert = call(client, "post", "ui/v1/alerts", search_alert())["data"]
    path = f"ui/v1/alerts/{alert['id']}"
    assert alert["silenced"] is None
    past = call(client, "post", f"{path}/silenced", {"until": "2020-01-01T00:00:00Z"})
    assert past["validation"]["fields"]["until"] == ["must be in the future"]
    until = (timezone.now() + timedelta(hours=1)).isoformat()
    got = call(client, "post", f"{path}/silenced", {"until": until})["data"]
    assert got["silenced"]["by"]["username"] == root_user.username
    assert call(client, "get", path)["data"]["silenced"]["until"]
    assert call(client, "delete", f"{path}/silenced")["data"]["silenced"] is None

    assert call(client, "post", f"{path}/enabled", {"enabled": False})["data"][
        "state"
    ] == ("DISABLED")
    got = call(client, "post", f"{path}/enabled", {"enabled": True})["data"]
    assert got["state"] == "OK"
    assert not call(client, "post", f"{path}/enabled", {"enabled": "yes"})["result"]

    # A user who cannot see the alert can neither silence nor disable it.
    other = client_for(test_user)
    for method, sub, body in [
        ("post", "silenced", {"until": until}),
        ("delete", "silenced", None),
        ("post", "enabled", {"enabled": False}),
        ("post", "test", None),
    ]:
        doc = call(other, method, f"{path}/{sub}", body)
        assert doc["errors"] == ["Alert not found"], (sub, doc)


@pytest.mark.django_db
def test_paginated_list_with_tags(root_user, clickhouse_source):
    client = client_for(root_user)
    for i in range(7):
        tags = ["prod"] + (["db"] if i % 2 else [])
        call(client, "post", "ui/v1/alerts", search_alert(name=f"a{i}", tags=tags))
    assert len(call(client, "get", "ui/v1/alerts")["data"]) == 7
    page = call(client, "get", "ui/v1/alerts?page=2&page_size=3")["data"]
    assert page["total"] == 7 and page["tags"] == ["db", "prod"]
    assert [a["name"] for a in page["items"]] == ["a3", "a4", "a5"]
    page = call(client, "get", "ui/v1/alerts?page=1&tags=prod,db")["data"]
    assert [a["name"] for a in page["items"]] == ["a1", "a3", "a5"]
    page = call(client, "get", "ui/v1/alerts?page=1&q=A6&state=OK")["data"]
    assert [a["name"] for a in page["items"]] == ["a6"]
    assert call(client, "get", "ui/v1/alerts?page=9")["data"]["items"] == []


@pytest.mark.django_db
def test_evaluation_pages_match_history_rows(root_user, clickhouse_source, fake_values):
    alert = make_alert(root_user, clickhouse_source, group_by="hostname")
    for i in range(25):
        fake_values[T0 + i * STEP] = {"a": float(i * 10), "b": 1.0}
    evaluate_alert(alert, T0 + 10 * STEP)
    evaluate_alert(alert, T0 + 20 * STEP)
    evaluate_alert(alert, T0 + 25 * STEP)
    client = client_for(root_user)
    seen, before, pages = [], "", 0
    while True:
        doc = call(
            client,
            "get",
            f"ui/v1/alerts/{alert.pk}/evaluations?limit=7{before}",
        )["data"]
        pages += 1
        for entry in doc["items"]:
            ranks = {g["state"] for g in entry["groups"]}
            assert entry["state"] == ("ALERT" if "ALERT" in ranks else "OK")
            seen += [
                (entry["window_start"], g["group_key"], g["state"], g["value"])
                for g in entry["groups"]
            ]
        if not doc["has_more"]:
            break
        before = f"&before={doc['next_before']}"
    assert pages == 4
    assert sorted(seen) == history(alert) and len(seen) == 50
    rows = call(
        client,
        "get",
        f"ui/v1/alerts/{alert.pk}/history?from={T0 + 5 * STEP}&to={T0 + 8 * STEP}",
    )["data"]
    assert [(r["window_start"], r["group_key"]) for r in rows] == [
        (T0 + i * STEP, g) for i in (5, 6, 7) for g in "ab"
    ]


@pytest.mark.django_db
def test_markers_are_firing_transitions(
    root_user, test_user, clickhouse_source, fake_values
):
    alert = make_alert(root_user, clickhouse_source, group_by="hostname")
    pattern = [1, 60, 60, 1, 60, 1]
    for i, v in enumerate(pattern):
        fake_values[T0 + i * STEP] = {"a": float(v), "b": float(pattern[-1 - i])}
    evaluate_alert(alert, T0 + 6 * STEP)
    client = client_for(root_user)
    base = f"ui/v1/alerts/markers?source={clickhouse_source.slug}"
    got = call(client, "get", f"{base}&from={T0}&to={T0 + 6 * STEP}")["data"]
    assert [(m["time"], m["group_key"]) for m in got] == [
        (T0 + STEP, "a"),
        (T0 + STEP, "b"),
        (T0 + 3 * STEP, "b"),
        (T0 + 4 * STEP, "a"),
    ]
    assert got[0]["alert_id"] == alert.pk and got[0]["name"] == alert.name
    # A window continuing a run that started before `from` is no new marker.
    got = call(client, "get", f"{base}&from={T0 + 2 * STEP}&to={T0 + 6 * STEP}")
    assert [(m["time"], m["group_key"]) for m in got["data"]] == [
        (T0 + 3 * STEP, "b"),
        (T0 + 4 * STEP, "a"),
    ]
    other = call(client_for(test_user), "get", f"{base}&from={T0}&to={T0 + 9}")
    assert other["data"] == []
    assert not call(client, "get", f"ui/v1/alerts/markers?from=1&to=2")["result"]


@pytest.mark.django_db
def test_tile_markers(root_user, clickhouse_source, fake_values):
    from telescope.models import Dashboard

    dashboard = Dashboard.objects.create(
        slug="d1", name="d", owner=root_user, data={"tiles": []}
    )
    alert = make_alert(
        root_user, clickhouse_source, kind="tile", dashboard=dashboard, tile_id="t1"
    )
    AlertHistory.objects.create(
        alert=alert, window_start=T0, window_end=T0 + STEP, state="ALERT"
    )
    make_alert(root_user, clickhouse_source, name="search")
    client = client_for(root_user)
    listed = call(client, "get", "ui/v1/alerts?dashboard=d1")["data"]
    assert [a["id"] for a in listed] == [alert.pk]
    path = f"ui/v1/alerts/markers?dashboard=d1&from={T0}&to={T0 + STEP}"
    assert [m["time"] for m in call(client, "get", f"{path}&tile=t1")["data"]] == [T0]
    assert call(client, "get", f"{path}&tile=t2")["data"] == []


@pytest.mark.django_db
def test_test_notification_uses_the_alert(
    root_user, clickhouse_source, receiver, alerts_config
):
    client = client_for(root_user)
    alert = call(client, "post", "ui/v1/alerts", search_alert())["data"]
    path = f"ui/v1/alerts/{alert['id']}/test"
    assert call(client, "post", path)["errors"] == [
        "failed to send test notification: the alert has no channels"
    ]
    Alert.objects.get(pk=alert["id"]).channels.add(webhook(receiver))
    assert call(client, "post", path)["data"] == {"sent": 1}
    (body,) = receiver.json()
    assert body["title"].startswith('[Test] Alert for "Errors"')
    assert body["alertId"] == str(alert["id"]) and body["sourceQuery"] == "hostname='a'"
    assert not AlertHistory.objects.exists()


@pytest.mark.django_db
def test_saved_view_tags_favorites_and_alert_badges(
    root_user, test_user, clickhouse_source
):
    from telescope.rbac.manager import RBACManager
    from telescope.rbac.roles import SourceRole

    RBACManager().grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    mine = SavedView.objects.create(
        slug="mine",
        name="mine",
        description="",
        source=clickhouse_source,
        user=root_user,
        shared=True,
        data={"query": "hostname='a'"},
    )
    client = client_for(root_user)
    call(client, "post", "ui/v1/alerts", search_alert())
    call(client, "post", "ui/v1/alerts", search_alert(name="other", query="x=1"))
    base = f"ui/v1/alerts/saved-views/{clickhouse_source.slug}"
    meta = call(client, "get", base)["data"][str(mine.pk)]
    assert meta["tags"] == [] and meta["favorite"] is False
    assert (meta["id"], meta["slug"], meta["user_id"]) == (
        mine.pk,
        "mine",
        root_user.pk,
    )
    assert [a["name"] for a in meta["alerts"]] == ["Errors"]
    got = call(client, "patch", f"{base}/{mine.pk}", {"tags": ["prod", " prod", ""]})[
        "data"
    ]
    assert got["tags"] == ["prod"]
    got = call(client, "patch", f"{base}/{mine.pk}", {"favorite": True})["data"]
    assert got["favorite"] and got["tags"] == ["prod"]

    other = client_for(test_user)
    seen = call(other, "get", base)["data"][str(mine.pk)]
    assert seen["tags"] == ["prod"] and seen["favorite"] is False
    # Root's alert stays hidden from a user without... (test_user has USE here, so it shows)
    assert [a["name"] for a in seen["alerts"]] == ["Errors"]
    denied = call(other, "patch", f"{base}/{mine.pk}", {"tags": ["x"]})
    assert denied["errors"] == ["Only those who can edit the view can tag it"]
    call(other, "patch", f"{base}/{mine.pk}", {"favorite": True})
    assert SavedViewFavorite.objects.filter(view=mine).count() == 2
    call(client, "patch", f"{base}/{mine.pk}", {"favorite": False})
    assert call(other, "get", base)["data"][str(mine.pk)]["favorite"] is True
    assert not call(client, "patch", f"{base}/999999", {"favorite": True})["result"]
    mine.delete()
    assert not SavedViewFavorite.objects.exists()


@pytest.mark.clickhouse
@pytest.mark.django_db
def test_silence_on_the_planted_spike(
    root_user, otel_logs_source, otel_facts, receiver, alerts_config
):
    from telescope_alerts.tests.test_clickhouse import ms
    from telescope_alerts.tests.test_clickhouse import search_alert as ch_alert

    s = otel_facts["error_spike"]
    spike_from, spike_to = ms(s["from"]), ms(s["to"])
    start = spike_from - 3 * STEP
    alert = ch_alert(
        root_user, otel_logs_source, s["query"], last_evaluated_window=start - STEP
    )
    alert.channels.add(webhook(receiver))
    # Silenced through the first spike window: history is written, nothing is sent.
    silence(alert, timedelta(hours=1))
    evaluate_alert(alert, spike_from + STEP)
    assert [h[2] for h in history(alert)] == ["OK", "OK", "OK", "ALERT"]
    assert receiver.requests == []
    # After `until` the still-firing window notifies, then the end of the spike resolves.
    silence(alert, timedelta(seconds=-1))
    evaluate_alert(alert, spike_to + 2 * STEP)
    assert [h[2] for h in history(alert)][4:] == ["ALERT", "OK", "OK"]
    assert [(b["status"], b["startTime"]) for b in receiver.json()] == [
        ("firing", spike_from + STEP),
        ("resolved", spike_to),
    ]
