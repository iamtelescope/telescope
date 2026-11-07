"""Channel dispatch, config validation and secret masking."""

from urllib.parse import urlparse

from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.template import TemplateSyntaxError

from telescope_alerts import templating
from telescope_alerts.channels import email, net, pagerduty, slack, webhook
from telescope_alerts.channels.net import DeliveryError

MASK = "****"
MAX_HEADERS = 20
MAX_RECIPIENTS = 20

__all__ = ["DeliveryError", "send", "clean_config", "mask_config", "alerts_config"]


def alerts_config() -> dict:
    return settings.CONFIG.get("alerts") or {}


def allow_private() -> bool:
    return bool(alerts_config().get("allow_private_webhook_targets"))


def send(channel, message: dict):
    config = channel.config
    if channel.kind == "email":
        email.send(config, message, alerts_config().get("email") or {})
    elif channel.kind == "slack":
        slack.send(config, message, allow_private())
    elif channel.kind == "pagerduty":
        pagerduty.send(config, message, allow_private())
    else:
        webhook.send(config, message, allow_private())


def mask_url(url: str) -> str:
    parsed = urlparse(url or "")
    if not parsed.scheme or not parsed.netloc:
        return MASK if url else ""
    if parsed.path in ("", "/") and not parsed.query:
        return url
    return f"{parsed.scheme}://{parsed.netloc}/{MASK}"


def mask_config(kind: str, config: dict) -> dict:
    result = dict(config)
    if "url" in result:
        result["url"] = mask_url(result["url"])
    if kind == "webhook":
        result["headers"] = {k: MASK for k in (config.get("headers") or {})}
    if kind == "pagerduty" and result.get("routing_key"):
        result["routing_key"] = MASK
    return result


def _unmask(kind: str, config: dict, old: dict) -> dict:
    """Masked values sent back unchanged keep the stored secret."""
    config = dict(config)
    if old.get("url") and config.get("url") == mask_url(old["url"]):
        config["url"] = old["url"]
    if kind == "webhook":
        old_headers = old.get("headers") or {}
        config["headers"] = {
            k: (old_headers[k] if v == MASK and k in old_headers else v)
            for k, v in (config.get("headers") or {}).items()
        }
    if kind == "pagerduty" and config.get("routing_key") == MASK:
        config["routing_key"] = old.get("routing_key", "")
    return config


def _check_url(url, errors, field="url", required=True):
    if not url:
        if required:
            errors[field] = ["This field is required."]
        return
    if MASK in url:
        errors[field] = ["enter the full URL"]
        return
    try:
        net.check_url(url, allow_private())
    except DeliveryError as err:
        errors[field] = [str(err)]


def clean_config(kind: str, config, old: dict = None):
    """Returns (config, errors); errors is a field -> messages dict."""
    if not isinstance(config, dict):
        return {}, {"config": ["Expected an object"]}
    config = _unmask(kind, config, old or {})
    errors = {}
    if kind in ("slack", "webhook"):
        url = config.get("url") or ""
        _check_url(url, errors)
        cleaned = {"url": url}
        if kind == "webhook":
            headers = config.get("headers") or {}
            if not isinstance(headers, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in headers.items()
            ):
                errors["headers"] = ["must be an object of strings"]
                headers = {}
            elif len(headers) > MAX_HEADERS:
                errors["headers"] = [f"at most {MAX_HEADERS} headers"]
            body = config.get("body") or ""
            if not isinstance(body, str):
                errors["body"] = ["must be a string"]
                body = ""
            for name, text in [("body", body)] + [
                (f"headers.{k}", v) for k, v in headers.items()
            ]:
                try:
                    templating.compile_template(text)
                except (TemplateSyntaxError, ValueError) as err:
                    errors[name] = [f"template error: {err}"]
            cleaned.update(headers=headers, body=body)
        return cleaned, errors
    if kind == "pagerduty":
        key = config.get("routing_key") or ""
        if not isinstance(key, str) or not key.strip():
            errors["routing_key"] = ["This field is required."]
        elif len(key) > 64:
            errors["routing_key"] = ["at most 64 characters"]
        severity = config.get("severity") or "error"
        if severity not in pagerduty.SEVERITIES:
            errors["severity"] = ["must be one of " + ", ".join(pagerduty.SEVERITIES)]
        cleaned = {"routing_key": key.strip(), "severity": severity}
        if config.get("url"):
            _check_url(config["url"], errors)
            cleaned["url"] = config["url"]
        return cleaned, errors
    recipients = config.get("recipients") or []
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]
    if not isinstance(recipients, list) or not recipients:
        errors["recipients"] = ["at least one recipient is required"]
        recipients = []
    elif len(recipients) > MAX_RECIPIENTS:
        errors["recipients"] = [f"at most {MAX_RECIPIENTS} recipients"]
    for address in recipients:
        try:
            validate_email(address)
        except (DjangoValidationError, TypeError):
            errors["recipients"] = [f"invalid email address {address}"]
    return {"recipients": recipients}, errors
