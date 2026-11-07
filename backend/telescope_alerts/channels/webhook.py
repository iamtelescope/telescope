"""Generic webhook: templated body and headers, adapted from HyperDX transports/generic.ts (MIT)."""

import hashlib
import json

from telescope_alerts import templating
from telescope_alerts.channels import net


def payload(config: dict, message: dict) -> str:
    template = config.get("body") or ""
    if not template.strip():
        return json.dumps(message)
    return templating.render(template, message)


def headers(config: dict, message: dict) -> dict:
    result = {
        name: templating.render(value, message)
        for name, value in (config.get("headers") or {}).items()
    }
    key = json.dumps(
        [message["eventId"], message["startTime"], message["endTime"], message["state"]]
    )
    result["Idempotency-Key"] = hashlib.sha1(key.encode()).hexdigest()
    return result


def send(config: dict, message: dict, allow_private: bool):
    net.post(
        config["url"], payload(config, message), headers(config, message), allow_private
    )
