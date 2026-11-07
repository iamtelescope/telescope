"""Alert evaluation. Windowing, thresholds, N-of-M and backfill follow HyperDX
api/src/tasks/checkAlerts/index.ts (MIT); queries go through the chart engine."""

import logging
import time
from collections import Counter
from typing import Dict, List, Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from telescope.fetchers import get_fetchers
from telescope.fetchers.chart import ZERO_FILL_AGGS

from telescope_alerts import channels, templating
from telescope_alerts.definition import AlertDefinitionError, alert_data, resolve
from telescope_alerts.models import (
    INTERVAL_MINUTES,
    STATE_ALERT,
    STATE_DISABLED,
    STATE_ERROR,
    STATE_INSUFFICIENT_DATA,
    STATE_OK,
    STATE_PENDING,
    Alert,
    AlertHistory,
)

logger = logging.getLogger("telescope.alerts")

MAX_BACKFILL_WINDOWS = 10
PREVIEW_WINDOWS = 24
PREVIEW_GROUPS = 10
MAX_GROUP_KEY = 255


def exceeds(threshold_type, threshold, threshold_max, value) -> bool:
    if threshold_type == "above":
        return value >= threshold
    if threshold_type == "above_exclusive":
        return value > threshold
    if threshold_type == "below":
        return value < threshold
    if threshold_type == "below_or_equal":
        return value <= threshold
    if threshold_type == "equal":
        return value == threshold
    if threshold_type == "not_equal":
        return value != threshold
    if threshold_max is None:
        raise ValueError(f"threshold_max is required for {threshold_type}")
    inside = threshold <= value <= threshold_max
    return inside if threshold_type == "between" else not inside


def alert_exceeds(alert, value) -> bool:
    return exceeds(alert.threshold_type, alert.threshold, alert.threshold_max, value)


def now_ms() -> int:
    return int(time.time() * 1000)


def latest_window_start(interval: str, at_ms: int, origin: int = 0) -> int:
    """Start of the last complete window before `at_ms`; windows are aligned to `origin` (ms)."""
    step = INTERVAL_MINUTES[interval] * 60_000
    return origin + (at_ms - origin) // step * step - step


def due_windows(alert, at_ms: int) -> List[int]:
    """Schedule offset and start follow HyperDX getScheduledWindowStart."""
    step = alert.interval_ms
    latest = latest_window_start(alert.interval, at_ms, alert.window_origin)
    if alert.last_evaluated_window is None:
        first = latest
    else:
        first = alert.last_evaluated_window + step
    if alert.start_ms is not None:
        first = max(first, alert.start_ms)
    return list(range(first, latest + 1, step))[-MAX_BACKFILL_WINDOWS:]


def is_silenced(alert) -> bool:
    """Read fresh, so a silence set during a long tick holds the next delivery."""
    until = (
        Alert.objects.filter(pk=alert.pk)
        .values_list("silenced_until", flat=True)
        .first()
    )
    return until is not None and until > timezone.now()


def _number(value) -> Optional[float]:
    return None if value is None else float(value)


def query_window(aq, start: int, end: int) -> Dict[str, Optional[float]]:
    """Group key -> value for one window; '' when not grouped, None when there is no data."""
    fetcher = get_fetchers()[aq.source.kind]
    display = "table" if aq.grouped else "number"
    response = fetcher.fetch_chart_data(aq.request(start, end - 1, display))
    if not aq.grouped:
        return {"": _number(response.value)}
    return {
        str(row["group"])[:MAX_GROUP_KEY]: _number(row["values"][0])
        for row in response.rows
    }


def _set_error(alert, window_start: int, message: str):
    with transaction.atomic():
        AlertHistory.objects.update_or_create(
            alert=alert,
            group_key="",
            window_start=window_start,
            defaults={
                "window_end": window_start + alert.interval_ms,
                "state": STATE_ERROR,
                "value": None,
                "error": message[:2000],
            },
        )
        fields = {
            "state": STATE_ERROR,
            "last_error": message,
            "last_evaluated_at": timezone.now(),
        }
        # A disable that landed during the query wins.
        Alert.objects.filter(pk=alert.pk).exclude(state=STATE_DISABLED).update(**fields)
        for name, value in fields.items():
            setattr(alert, name, value)


def _window_states(alert, aq, window_start, values) -> Dict[str, tuple]:
    """Group key -> (state, value)."""
    step = alert.interval_ms
    lookback = alert.of_windows - 1
    recent = Counter()
    pending = set()
    if lookback > 0:
        rows = AlertHistory.objects.filter(
            alert=alert,
            window_start__gte=window_start - lookback * step,
            window_start__lt=window_start,
            state__in=[STATE_ALERT, STATE_PENDING],
        ).values_list("group_key", "state", "window_start")
        for group, state, start in rows:
            recent[group] += 1
            if state == STATE_PENDING and start == window_start - step:
                pending.add(group)
    zero_fill = aq.series["agg"] in ZERO_FILL_AGGS
    if aq.grouped:
        # Firing or pending groups with no rows in this window count as 0 when the agg zero-fills.
        for group in (set(alert.firing_groups) | pending) - set(values):
            if zero_fill:
                values[group] = 0.0
        if not values:
            values[""] = 0.0 if zero_fill else None
    states = {}
    for group, value in values.items():
        if value is None:
            state = STATE_INSUFFICIENT_DATA
        elif alert_exceeds(alert, value):
            hits = recent[group] + 1
            state = STATE_ALERT if hits >= alert.consecutive_windows else STATE_PENDING
        else:
            state = STATE_OK
        states[group] = (state, value)
    return states


def _overall_state(states) -> str:
    present = {state for state, _ in states.values()}
    for state in [STATE_ALERT, STATE_PENDING, STATE_OK]:
        if state in present:
            return state
    return STATE_INSUFFICIENT_DATA


class Superseded(Exception):
    """Another evaluator, a schedule change or a disable moved the alert first."""


def notify(alert, message, renew=None):
    """Sends to every channel; returns (errors, number delivered)."""
    errors, sent = [], 0
    for channel in alert.channels.all():
        try:
            channels.send(channel, message)
            sent += 1
        except Exception as err:
            logger.warning("alert %s: channel %s failed: %s", alert.pk, channel.pk, err)
            errors.append(f"{channel.name}: {err}")
        if renew:
            renew()
    return errors, sent


def apply_window(
    alert, aq, window_start: int, values, public_url="", renew=None
) -> bool:
    """Writes the window's history and sends transitions; False if another evaluator wrote it."""
    window_end = window_start + alert.interval_ms
    states = _window_states(alert, aq, window_start, dict(values))
    firing = set(alert.firing_groups)
    # While silenced the firing set is frozen, so held transitions are sent once it ends.
    silenced = is_silenced(alert)
    transitions = []
    rows = []
    for group, (state, value) in states.items():
        rows.append(
            AlertHistory(
                alert=alert,
                group_key=group,
                window_start=window_start,
                window_end=window_end,
                state=state,
                value=value,
            )
        )
        if silenced:
            continue
        if state == STATE_ALERT and group not in firing:
            firing.add(group)
            transitions.append(rows[-1])
        elif state == STATE_OK and group in firing:
            firing.discard(group)
            transitions.append(rows[-1])
    try:
        with transaction.atomic():
            AlertHistory.objects.filter(
                alert=alert, window_start=window_start, state=STATE_ERROR
            ).delete()
            for row in rows:
                row.save(force_insert=True)
            fields = {
                "firing_groups": sorted(firing),
                "state": _overall_state(states),
                "last_error": "",
                "last_evaluated_window": window_start,
                "last_evaluated_at": timezone.now(),
            }
            # Compare-and-set, so two evaluators with disjoint groups cannot both write.
            updated = (
                Alert.objects.filter(
                    pk=alert.pk, last_evaluated_window=alert.last_evaluated_window
                )
                .exclude(state=STATE_DISABLED)
                .update(**fields)
            )
            if not updated:
                raise Superseded()
            for name, value in fields.items():
                setattr(alert, name, value)
    except (IntegrityError, Superseded):
        logger.info("alert %s window %s already evaluated", alert.pk, window_start)
        return False

    errors = []
    for row in transitions:
        message = templating.build_message(
            alert,
            row.state,
            row.group_key,
            aq.group_by_name,
            row.value,
            window_start,
            window_end,
            aq.source_query,
            public_url,
        )
        row_errors, sent = notify(alert, message, renew)
        errors += row_errors
        update = {"error": "; ".join(row_errors)[:2000]}
        if sent:
            update["notified_at"] = timezone.now()
        AlertHistory.objects.filter(pk=row.pk).update(**update)
    if errors:
        alert.last_error = "notification failed: " + "; ".join(errors)
        alert.save(update_fields=["last_error"])
    return True


def evaluate_alert(alert, at_ms: Optional[int] = None, renew=None) -> int:
    """Evaluates the due windows as the owner; `renew` keeps the lease and False stops."""
    at_ms = now_ms() if at_ms is None else at_ms
    windows = due_windows(alert, at_ms)
    if not windows:
        return 0
    public_url = channels.alerts_config().get("public_url", "")
    try:
        aq = resolve(alert.owner, alert_data(alert))
    except AlertDefinitionError as err:
        _set_error(alert, windows[0], err.message)
        return 0
    if alert.source_slug != aq.source.slug:
        Alert.objects.filter(pk=alert.pk).update(source_slug=aq.source.slug)
        alert.source_slug = aq.source.slug
    written = 0
    for window_start in windows:
        if renew and not renew():
            return written
        try:
            values = query_window(aq, window_start, window_start + alert.interval_ms)
        except Exception as err:
            logger.warning("alert %s window %s: %s", alert.pk, window_start, err)
            _set_error(alert, window_start, f"query failed: {err}")
            return written
        if not apply_window(alert, aq, window_start, values, public_url, renew):
            alert.refresh_from_db()
            return written
        written += 1
    return written


def preview(alert, aq, at_ms: Optional[int] = None) -> Dict:
    """The last 24 windows in one time-series query, with the would-fire flag of each."""
    at_ms = now_ms() if at_ms is None else at_ms
    step = alert.interval_ms
    end = latest_window_start(alert.interval, at_ms) + step
    start = end - PREVIEW_WINDOWS * step
    fetcher = get_fetchers()[aq.source.kind]
    response = fetcher.fetch_chart_data(
        aq.request(
            start,
            end,
            "line",
            granularity=alert.interval,
            limit=PREVIEW_GROUPS,
        )
    )
    series = []
    for item in response.series:
        flags, states, hits = [], [], []
        for value in item["values"]:
            hit = value is not None and alert_exceeds(alert, value)
            hits.append(hit)
            recent = sum(hits[-alert.of_windows :])
            if value is None:
                state = STATE_INSUFFICIENT_DATA
            elif not hit:
                state = STATE_OK
            elif recent >= alert.consecutive_windows:
                state = STATE_ALERT
            else:
                state = STATE_PENDING
            states.append(state)
            flags.append(state == STATE_ALERT)
        series.append(
            {
                "group": item["group"] or "",
                "values": item["values"],
                "states": states,
                "would_fire": flags,
            }
        )
    return {
        "windows": response.timestamps,
        "step_ms": step,
        "series": series,
        "truncated": response.truncated,
    }
