"""PagerDuty Events API v2: trigger on firing, resolve on recovery, deduped per alert and group."""

from telescope_alerts.channels import net
from telescope_alerts.models import STATE_OK

EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"
SEVERITIES = ["critical", "error", "warning", "info"]


def dedup_key(message: dict) -> str:
    return f"{message['alertId']}:{message['groupKey']}"


def payload(config: dict, message: dict) -> dict:
    event = {
        "routing_key": config["routing_key"],
        "dedup_key": dedup_key(message),
    }
    if message["state"] == STATE_OK:
        event["event_action"] = "resolve"
        return event
    event["event_action"] = "trigger"
    event["payload"] = {
        "summary": message["title"][:1024],
        "source": "telescope",
        "severity": config.get("severity") or "error",
        "timestamp": message["endTimeISO"],
        "component": message["alertName"][:255],
        "group": message["groupKey"][:255],
        "class": message["alertType"],
        "custom_details": {
            "value": message["value"],
            "comparator": message["comparator"],
            "threshold": message["threshold"],
            "threshold_max": message["thresholdMax"],
            "window_start": message["startTimeISO"],
            "window_end": message["endTimeISO"],
            "query": message["sourceQuery"],
            "note": message["note"],
            "tags": message["tags"],
        },
    }
    if message.get("link"):
        event["links"] = [{"href": message["link"], "text": "Open in Telescope"}]
    return event


def send(config: dict, message: dict, allow_private: bool):
    net.post(
        config.get("url") or EVENTS_URL,
        payload(config, message),
        {},
        allow_private,
    )
