import json

import pytest

from telescope.models import SourceRoleBinding
from telescope_alerts import evaluator
from telescope_alerts.evaluator import (
    MAX_BACKFILL_WINDOWS,
    due_windows,
    evaluate_alert,
    exceeds,
    latest_window_start,
)
from telescope_alerts.models import Alert, AlertChannel, AlertHistory

MIN = 60_000
T0 = 1_767_268_800_000  # 2026-01-01T12:00:00Z


@pytest.mark.parametrize(
    "kind,value,expected",
    [
        ("above", 9.99, False),
        ("above", 10, True),
        ("above_exclusive", 10, False),
        ("above_exclusive", 10.01, True),
        ("below", 10, False),
        ("below", 9.99, True),
        ("below_or_equal", 10, True),
        ("below_or_equal", 10.01, False),
        ("equal", 10, True),
        ("equal", 11, False),
        ("not_equal", 10, False),
        ("not_equal", 11, True),
        ("between", 10, True),
        ("between", 20, True),
        ("between", 9.99, False),
        ("between", 20.01, False),
        ("not_between", 10, False),
        ("not_between", 20, False),
        ("not_between", 9.99, True),
        ("not_between", 20.01, True),
    ],
)
def test_exceeds_bounds(kind, value, expected):
    assert exceeds(kind, 10, 20, value) is expected


def test_range_needs_max():
    with pytest.raises(ValueError):
        exceeds("between", 1, None, 2)


def test_windows_are_aligned_and_capped():
    assert latest_window_start("5m", T0 + 7 * MIN) == T0
    assert latest_window_start("1h", T0 + 30 * MIN) == T0 - 60 * MIN
    alert = Alert(interval="5m", last_evaluated_window=None)
    assert due_windows(alert, T0 + 5 * MIN + 1) == [T0]
    alert.last_evaluated_window = T0
    assert due_windows(alert, T0 + 9 * MIN) == []
    alert.last_evaluated_window = T0 - 100 * 5 * MIN
    windows = due_windows(alert, T0 + 5 * MIN)
    assert len(windows) == MAX_BACKFILL_WINDOWS and windows[-1] == T0
    assert all(b - a == 5 * MIN for a, b in zip(windows, windows[1:]))


def make_alert(owner, source, **kw):
    fields = dict(
        name="errors",
        owner=owner,
        kind="search",
        source_slug=source.slug,
        series={"agg": "count"},
        interval="5m",
        threshold_type="above",
        threshold=50,
        last_evaluated_window=T0 - 5 * MIN,
    )
    fields.update(kw)
    return Alert.objects.create(**fields)


@pytest.fixture
def fake_values(monkeypatch):
    """Window start -> {group: value} served instead of ClickHouse."""
    data = {}

    def fake(aq, start, end):
        value = data.get(start, {"": 0.0})
        if isinstance(value, Exception):
            raise value
        return dict(value)

    monkeypatch.setattr(evaluator, "query_window", fake)
    return data


def webhook(receiver):
    return AlertChannel.objects.create(
        kind="webhook", name="hook", config={"url": receiver.url}
    )


def history(alert):
    return list(
        AlertHistory.objects.filter(alert=alert)
        .order_by("window_start", "group_key")
        .values_list("window_start", "group_key", "state", "value")
    )


@pytest.mark.django_db
def test_fires_once_and_resolves(
    root_user, clickhouse_source, fake_values, receiver, alerts_config
):
    alert = make_alert(root_user, clickhouse_source)
    alert.channels.add(webhook(receiver))
    for i, v in enumerate([3, 60, 70, 4, 5]):
        fake_values[T0 + i * 5 * MIN] = {"": float(v)}
    assert evaluate_alert(alert, T0 + 25 * MIN) == 5
    assert [h[2] for h in history(alert)] == ["OK", "ALERT", "ALERT", "OK", "OK"]
    bodies = receiver.json()
    assert [b["status"] for b in bodies] == ["firing", "resolved"]
    assert bodies[0]["value"] == 60 and bodies[0]["startTime"] == T0 + 5 * MIN
    assert bodies[0]["link"] == f"http://telescope.example/alerts/{alert.pk}"
    alert.refresh_from_db()
    assert alert.state == "OK" and alert.firing_groups == []
    assert alert.last_evaluated_window == T0 + 20 * MIN
    notified = AlertHistory.objects.exclude(notified_at=None)
    assert sorted(notified.values_list("window_start", flat=True)) == [
        T0 + 5 * MIN,
        T0 + 15 * MIN,
    ]
    # Nothing is due any more, so a second tick writes nothing.
    assert evaluate_alert(alert, T0 + 25 * MIN) == 0


@pytest.mark.django_db
def test_n_of_m_goes_pending_first(root_user, clickhouse_source, fake_values):
    alert = make_alert(
        root_user, clickhouse_source, consecutive_windows=2, of_windows=3
    )
    for i, v in enumerate([60, 1, 60, 60, 1]):
        fake_values[T0 + i * 5 * MIN] = {"": float(v)}
    evaluate_alert(alert, T0 + 25 * MIN)
    assert [h[2] for h in history(alert)] == ["PENDING", "OK", "ALERT", "ALERT", "OK"]


@pytest.mark.django_db
def test_empty_window_is_insufficient_for_avg(
    root_user, clickhouse_source, fake_values
):
    alert = make_alert(
        root_user,
        clickhouse_source,
        series={"agg": "avg", "column": "thread_id"},
    )
    fake_values[T0] = {"": None}
    evaluate_alert(alert, T0 + 5 * MIN)
    assert history(alert) == [(T0, "", "INSUFFICIENT_DATA", None)]
    alert.refresh_from_db()
    assert alert.state == "INSUFFICIENT_DATA"


@pytest.mark.django_db
def test_grouped_only_breaching_group_fires_and_missing_group_resolves(
    root_user, clickhouse_source, fake_values, receiver, alerts_config
):
    alert = make_alert(root_user, clickhouse_source, group_by="hostname")
    alert.channels.add(webhook(receiver))
    fake_values[T0] = {"a": 80.0, "b": 2.0}
    fake_values[T0 + 5 * MIN] = {"b": 3.0}
    evaluate_alert(alert, T0 + 10 * MIN)
    assert history(alert) == [
        (T0, "a", "ALERT", 80.0),
        (T0, "b", "OK", 2.0),
        (T0 + 5 * MIN, "a", "OK", 0.0),
        (T0 + 5 * MIN, "b", "OK", 3.0),
    ]
    bodies = receiver.json()
    assert [(b["status"], b["groupKey"]) for b in bodies] == [
        ("firing", "a"),
        ("resolved", "a"),
    ]
    assert bodies[0]["var"] == {"hostname": "a"}


@pytest.mark.django_db
def test_query_error_retries_window(root_user, clickhouse_source, fake_values):
    alert = make_alert(root_user, clickhouse_source)
    fake_values[T0] = TimeoutError("Timeout exceeded: elapsed 30 seconds")
    assert evaluate_alert(alert, T0 + 5 * MIN) == 0
    alert.refresh_from_db()
    assert alert.state == "ERROR" and "Timeout" in alert.last_error
    assert alert.last_evaluated_window == T0 - 5 * MIN
    assert history(alert) == [(T0, "", "ERROR", None)]
    fake_values[T0] = {"": 1.0}
    assert evaluate_alert(alert, T0 + 5 * MIN) == 1
    assert history(alert) == [(T0, "", "OK", 1.0)]


@pytest.mark.django_db
def test_revoked_source_access_is_error(test_user, clickhouse_source, fake_values):
    binding = SourceRoleBinding.objects.create(
        user=test_user, source=clickhouse_source, role="user"
    )
    alert = make_alert(test_user, clickhouse_source)
    assert evaluate_alert(alert, T0 + 5 * MIN) == 1
    binding.delete()
    assert evaluate_alert(alert, T0 + 10 * MIN) == 0
    alert.refresh_from_db()
    assert alert.state == "ERROR" and alert.last_error == "source not found"
    row = AlertHistory.objects.get(alert=alert, window_start=T0 + 5 * MIN)
    assert (row.state, row.error) == ("ERROR", "source not found")


@pytest.mark.django_db
def test_raw_query_needs_raw_query_permission(
    test_user, clickhouse_source, fake_values
):
    SourceRoleBinding.objects.create(
        user=test_user, source=clickhouse_source, role="user"
    )
    alert = make_alert(test_user, clickhouse_source, raw_query="1 = 1")
    evaluate_alert(alert, T0 + 5 * MIN)
    alert.refresh_from_db()
    assert alert.state == "ERROR" and "raw" in alert.last_error.lower()


@pytest.mark.django_db
def test_window_written_elsewhere_sends_nothing(
    root_user, clickhouse_source, fake_values, receiver, alerts_config
):
    alert = make_alert(root_user, clickhouse_source)
    alert.channels.add(webhook(receiver))
    fake_values[T0] = {"": 99.0}
    AlertHistory.objects.create(
        alert=alert, window_start=T0, window_end=T0 + 5 * MIN, state="ALERT", value=99
    )
    assert evaluate_alert(alert, T0 + 5 * MIN) == 0
    assert receiver.requests == []
    assert AlertHistory.objects.filter(alert=alert).count() == 1


@pytest.mark.django_db
def test_failed_channel_is_recorded(
    root_user, clickhouse_source, fake_values, make_receiver, alerts_config
):
    bad = make_receiver(status=500)
    good = make_receiver()
    alert = make_alert(root_user, clickhouse_source)
    alert.channels.add(webhook(bad), webhook(good))
    fake_values[T0] = {"": 99.0}
    evaluate_alert(alert, T0 + 5 * MIN)
    assert len(bad.requests) == 4  # 1 attempt + 3 retries
    assert len(good.requests) == 1
    row = AlertHistory.objects.get(alert=alert)
    assert row.notified_at is not None and "HTTP 500" in row.error
    alert.refresh_from_db()
    assert alert.state == "ALERT" and "notification failed" in alert.last_error
    assert json.loads(good.requests[0]["body"])["status"] == "firing"
