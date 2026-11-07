import json
import socket
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from telescope_alerts import templating
from telescope_alerts.channels import DeliveryError, email, net, pagerduty, slack
from telescope_alerts.channels import webhook
from telescope_alerts.models import Alert, AlertChannel, SchedulerLease
from telescope_alerts.scheduler import acquire_lease, release_lease

T0 = 1_767_268_800_000


def message(state="ALERT", group="payment"):
    alert = Alert(
        pk=7,
        name="Payment errors",
        kind="search",
        interval="5m",
        threshold_type="above",
        threshold=50,
        note="runbook: https://wiki/x",
        tags=["team-payments", "prod"],
    )
    return templating.build_message(
        alert,
        state,
        group,
        "ServiceName" if group else "",
        109.0,
        T0,
        T0 + 300_000,
        "ServiceName='payment' and SeverityText='ERROR'",
        "https://telescope.example/",
    )


def test_message_variables():
    m = message()
    assert m["title"] == 'Alert for "Payment errors" (payment) - 109 >= 50'
    assert m["status"] == "firing" and m["comparator"] == ">="
    assert m["link"] == "https://telescope.example/alerts/7"
    assert m["startTimeISO"] == "2026-01-01T12:00:00.000Z"
    assert m["var"] == {"ServiceName": "payment"}
    assert m["thresholdMax"] is None
    assert m["eventId"] == message("OK")["eventId"] != message(group="cart")["eventId"]
    assert message("OK")["status"] == "resolved"
    assert message("OK")["title"].startswith('Resolved "Payment errors"')


def test_template_is_not_html_escaped_and_has_json_filter():
    body = templating.render(
        '{"t": {{ title|json }}, "v": {{ value }}, "svc": "{{ var.ServiceName }}", "tags": {{ tags|json }}}',
        message(),
    )
    data = json.loads(body)
    assert data == {
        "t": 'Alert for "Payment errors" (payment) - 109 >= 50',
        "v": 109.0,
        "svc": "payment",
        "tags": ["team-payments", "prod"],
    }
    assert templating.render("{{ sourceQuery }}", message()) == (
        "ServiceName='payment' and SeverityText='ERROR'"
    )


def test_webhook_default_body_and_headers():
    m = message()
    assert json.loads(webhook.payload({}, m)) == json.loads(json.dumps(m))
    headers = webhook.headers({"headers": {"X-Alert": "{{ alertId }}"}}, m)
    assert headers["X-Alert"] == "7"
    assert len(headers["Idempotency-Key"]) == 40


def test_slack_payload_shape():
    p = slack.payload(message())
    assert set(p) == {"text", "blocks"}
    assert p["text"] == message()["title"]
    block = p["blocks"][0]
    assert block["type"] == "section" and block["text"]["type"] == "mrkdwn"
    assert block["text"]["text"].startswith(
        "*<https://telescope.example/alerts/7|Alert for"
    )
    assert slack.escape("<a>&") == "&lt;a&gt;&amp;"


def test_pagerduty_events_v2_shape():
    config = {"routing_key": "R" * 32, "severity": "critical"}
    trigger = pagerduty.payload(config, message())
    assert trigger["event_action"] == "trigger"
    assert trigger["routing_key"] == "R" * 32
    assert trigger["dedup_key"] == "7:payment"
    p = trigger["payload"]
    assert {"summary", "source", "severity"} <= set(p)
    assert p["severity"] in pagerduty.SEVERITIES and len(p["summary"]) <= 1024
    assert p["timestamp"] == "2026-01-01T12:05:00.000Z"
    assert trigger["links"] == [
        {"href": "https://telescope.example/alerts/7", "text": "Open in Telescope"}
    ]
    resolve = pagerduty.payload(config, message("OK"))
    assert resolve == {
        "routing_key": "R" * 32,
        "dedup_key": "7:payment",
        "event_action": "resolve",
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/x",
        "http://localhost:8000/x",
        "http://[::1]/x",
        "http://[::ffff:127.0.0.1]/x",
        "http://10.0.0.1/x",
        "http://192.168.1.1/x",
        "http://169.254.169.254/latest/meta-data",
        "http://0.0.0.0/x",
    ],
)
def test_private_targets_refused(url):
    with pytest.raises(DeliveryError, match="private or loopback"):
        net.check_url(url, allow_private=False)
    net.check_url(url, allow_private=True)


def test_public_target_and_bad_scheme():
    net.check_url("https://8.8.8.8/x", allow_private=False)
    with pytest.raises(DeliveryError, match="http"):
        net.check_url("file:///etc/passwd", allow_private=True)


def test_redirects_not_followed(make_receiver):
    target = make_receiver()
    redirect = make_receiver(status=302, location=target.url)
    with pytest.raises(DeliveryError, match="redirects"):
        net.post(redirect.url, {"a": 1}, {}, allow_private=True)
    assert len(redirect.requests) == 1 and target.requests == []


def test_retries_then_succeeds(make_receiver):
    flaky = make_receiver(status=lambda n: 503 if n < 3 else 200)
    net.post(flaky.url, {"a": 1}, {}, allow_private=True)
    assert len(flaky.requests) == 3


def test_retries_give_up(make_receiver):
    down = make_receiver(status=500)
    with pytest.raises(DeliveryError, match="HTTP 500"):
        net.post(down.url, {}, {}, allow_private=True)
    assert len(down.requests) == 1 + net.RETRIES


def test_email(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    email.send(
        {"recipients": ["oncall@example.com"]},
        message(),
        {"from_email": "alerts@example.com"},
    )
    sent = mail.outbox[0]
    assert sent.to == ["oncall@example.com"]
    assert sent.from_email == "alerts@example.com"
    assert sent.subject == message()["title"]
    assert "https://telescope.example/alerts/7" in sent.body


@pytest.mark.django_db
def test_lease():
    assert acquire_lease("a", 60)
    assert acquire_lease("a", 60)
    assert not acquire_lease("b", 60)
    SchedulerLease.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert acquire_lease("b", 60)
    assert not acquire_lease("a", 60)
    release_lease("b")
    assert acquire_lease("a", 60)


@pytest.mark.django_db
def test_masked_secret_not_resent():
    from telescope_alerts.channels import clean_config, mask_config

    stored = {"routing_key": "secret-key", "severity": "error"}
    masked = mask_config("pagerduty", stored)
    assert masked["routing_key"] == "****"
    config, errors = clean_config("pagerduty", masked, stored)
    assert errors == {} and config["routing_key"] == "secret-key"
    assert AlertChannel.objects.count() == 0


def test_connection_pinned_to_checked_address(receiver, monkeypatch):
    """A second DNS answer (rebinding) is never used: delivery dials the checked IP."""
    port = receiver.server.server_address[1]
    lookups = []
    real = socket.getaddrinfo

    def fake_getaddrinfo(host, *args, **kwargs):
        lookups.append(host)
        if host != "rebind.example":
            return real(host, *args, **kwargs)
        ip = "127.0.0.1" if len(lookups) == 1 else "10.255.255.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(net, "_is_public", lambda addr: str(addr) == "127.0.0.1")
    net.post(f"http://rebind.example:{port}/hook?a=1", {"x": 1}, {}, False)
    assert lookups == ["rebind.example", "127.0.0.1"]
    assert receiver.requests[0]["path"] == "/hook?a=1"
    assert receiver.requests[0]["headers"]["Host"] == f"rebind.example:{port}"


def test_env_proxy_not_used(receiver, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://10.255.255.1:3128")
    monkeypatch.setenv("http_proxy", "http://10.255.255.1:3128")
    net.post(receiver.url, {"x": 1}, {}, allow_private=True)
    assert len(receiver.requests) == 1


@pytest.mark.parametrize(
    "kind,old",
    [
        (
            "webhook",
            {"url": "https://hooks.example.com/a", "headers": {"A": "s3cret"}},
        ),
        ("pagerduty", {"routing_key": "R" * 32, "severity": "error"}),
    ],
)
def test_masked_secret_not_kept_for_new_url(kind, old, alerts_config):
    from telescope_alerts.channels import RETYPE_SECRET, clean_config, mask_config

    back = mask_config(kind, old)
    config, errors = clean_config(kind, back, old)
    assert errors == {} and "****" not in json.dumps(config)
    back["url"] = "https://8.8.8.8/attacker"
    config, errors = clean_config(kind, back, old)
    field = "headers" if kind == "webhook" else "routing_key"
    assert errors[field] == [RETYPE_SECRET]
    assert "s3cret" not in json.dumps(config) and "R" * 32 not in json.dumps(config)


def test_email_subject_with_line_break_in_group(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    email.send({"recipients": ["oncall@example.com"]}, message(group="a\r\nb\nc"), {})
    subject = mail.outbox[0].subject
    assert "\n" not in subject and "\r" not in subject and "a b c" in subject
