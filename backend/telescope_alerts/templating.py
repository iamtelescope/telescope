"""Notification messages and the webhook body/header templates (Django templates, autoescape off)."""

import hashlib
import json
from datetime import datetime, timezone

from django.template import Context, Engine, Library

from telescope_alerts.models import (
    KIND_TILE,
    RANGE_THRESHOLD_TYPES,
    STATE_ALERT,
    STATE_ERROR,
    STATE_INSUFFICIENT_DATA,
    STATE_OK,
    STATE_PENDING,
)

register = Library()


@register.filter(name="json")
def json_filter(value):
    return json.dumps(value)


ENGINE = Engine(autoescape=False, builtins=["telescope_alerts.templating"])
MAX_TEMPLATE_BYTES = 10_000
MAX_SOURCE_QUERY = 2000

# Ported from HyperDX checkAlerts/template.ts (MIT).
COMPARATORS = {
    "above": ">=",
    "above_exclusive": ">",
    "below": "<",
    "below_or_equal": "<=",
    "equal": "=",
    "not_equal": "!=",
    "between": "between",
    "not_between": "outside",
}
STATUS_BY_STATE = {
    STATE_ALERT: "firing",
    STATE_OK: "resolved",
    STATE_INSUFFICIENT_DATA: "no_data",
    STATE_PENDING: "pending",
    STATE_ERROR: "error",
}


def compile_template(text: str):
    """Raises django.template.TemplateSyntaxError for a template that does not compile."""
    if len(text.encode()) > MAX_TEMPLATE_BYTES:
        raise ValueError(f"template must be at most {MAX_TEMPLATE_BYTES} bytes")
    return ENGINE.from_string(text)


def render(text: str, variables: dict) -> str:
    return compile_template(text).render(Context(variables, autoescape=False))


def iso(ms: int) -> str:
    return (
        datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def format_value(value) -> str:
    if value is None:
        return "no data"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6g}"


def describe_condition(alert) -> str:
    comparator = COMPARATORS[alert.threshold_type]
    if alert.threshold_type in RANGE_THRESHOLD_TYPES:
        return f"{comparator} {format_value(alert.threshold)} and {format_value(alert.threshold_max)}"
    return f"{comparator} {format_value(alert.threshold)}"


def event_id(alert, group_key: str) -> str:
    return hashlib.sha1(f"{alert.pk}:{group_key}".encode()).hexdigest()[:20]


def alert_link(alert, public_url: str) -> str:
    return f"{(public_url or '').rstrip('/')}/alerts/{alert.pk}"


def build_message(
    alert,
    state,
    group_key,
    group_by_name,
    value,
    window_start,
    window_end,
    source_query,
    public_url,
):
    """All template variables of a notification; see docs/alert-webhook-template-variables.md in HyperDX."""
    group_suffix = f" ({group_key})" if group_key else ""
    condition = describe_condition(alert)
    if state == STATE_ALERT:
        title = f'Alert for "{alert.name}"{group_suffix} - {format_value(value)} {condition}'
    elif state == STATE_OK:
        title = f'Resolved "{alert.name}"{group_suffix} - {format_value(value)}, no longer {condition}'
    else:
        title = f'"{alert.name}"{group_suffix} is {state}'
    link = alert_link(alert, public_url)
    lines = [
        f"Condition: value {condition} over {alert.interval}",
        f"Value: {format_value(value)}",
        f"Window: {iso(window_start)} - {iso(window_end)}",
    ]
    if group_key:
        lines.append(f"Group: {group_by_name} = {group_key}")
    if source_query:
        lines.append(f"Query: {source_query}")
    if alert.note:
        lines.append(f"Note: {alert.note}")
    return {
        "title": title,
        "body": "\n".join(lines),
        "link": link,
        "state": state,
        "status": STATUS_BY_STATE.get(state, ""),
        "alertId": str(alert.pk),
        "alertName": alert.name,
        "alertType": "dashboard_chart" if alert.kind == KIND_TILE else "search",
        "eventId": event_id(alert, group_key),
        "startTime": window_start,
        "endTime": window_end,
        "startTimeISO": iso(window_start),
        "endTimeISO": iso(window_end),
        "comparator": COMPARATORS[alert.threshold_type],
        "threshold": alert.threshold,
        "thresholdMax": (
            alert.threshold_max
            if alert.threshold_type in RANGE_THRESHOLD_TYPES
            else None
        ),
        "value": value,
        "groupKey": group_key,
        "var": {group_by_name: group_key} if group_by_name else {},
        "sourceQuery": (source_query or "")[:MAX_SOURCE_QUERY],
        "note": alert.note,
        "tags": list(alert.tags or []),
    }


def sample_message(public_url: str) -> dict:
    """A firing `between` alert with every variable set, for "send test"."""
    now = int(datetime.now(timezone.utc).timestamp() * 1000) // 60_000 * 60_000
    return {
        "title": 'Alert for "Test alert" (checkout) - 42 between 10 and 100',
        "body": "This is a test notification from Telescope.",
        "link": f"{(public_url or '').rstrip('/')}/alerts",
        "state": STATE_ALERT,
        "status": "firing",
        "alertId": "test",
        "alertName": "Test alert",
        "alertType": "search",
        "eventId": "test",
        "startTime": now - 300_000,
        "endTime": now,
        "startTimeISO": iso(now - 300_000),
        "endTimeISO": iso(now),
        "comparator": "between",
        "threshold": 10,
        "thresholdMax": 100,
        "value": 42,
        "groupKey": "checkout",
        "var": {"service": "checkout"},
        "sourceQuery": "service='checkout' and level='ERROR'",
        "note": "Test note",
        "tags": ["test"],
    }
