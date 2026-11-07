import pytest
from rest_framework.test import APIClient

from telescope.models import Dashboard, GlobalRoleBinding
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope_alerts.models import Alert, AlertChannel

rbac_manager = RBACManager()


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def call(client, method, path, body=None):
    response = getattr(client, method)(f"/{path}", body, format="json")
    assert response.status_code == 200, response.content[:300]
    return response.json()


def search_alert(source="clickhouse", **changes):
    body = {
        "name": "Errors",
        "kind": "search",
        "source": source,
        "query": "hostname='a'",
        "series": {"agg": "count"},
        "interval": "5m",
        "threshold_type": "above",
        "threshold": 50,
    }
    body.update(changes)
    return body


@pytest.mark.django_db
def test_alert_crud(root_user, clickhouse_source):
    client = client_for(root_user)
    created = call(client, "post", "ui/v1/alerts", search_alert(tags=["prod"]))
    assert created["result"], created
    alert = created["data"]
    assert alert["state"] == "OK" and alert["owner"]["username"] == root_user.username
    assert alert["can_edit"] and alert["tags"] == ["prod"]
    assert alert["threshold_max"] is None
    listed = call(client, "get", "ui/v1/alerts")["data"]
    assert [a["id"] for a in listed] == [alert["id"]]
    updated = call(
        client,
        "patch",
        f"ui/v1/alerts/{alert['id']}",
        search_alert(threshold_type="between", threshold=1, threshold_max=5),
    )
    assert updated["result"], updated
    assert updated["data"]["threshold_max"] == 5
    assert call(client, "get", f"ui/v1/alerts/{alert['id']}/history")["data"] == []
    assert call(client, "delete", f"ui/v1/alerts/{alert['id']}")["result"]
    assert not Alert.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "changes,field",
    [
        ({"threshold_type": "between"}, "threshold_max"),
        ({"threshold_type": "between", "threshold_max": 1}, "threshold_max"),
        ({"consecutive_windows": 3, "of_windows": 2}, "of_windows"),
        ({"interval": "2m"}, "interval"),
        ({"threshold_type": "over"}, "threshold_type"),
        ({"series": {"agg": "avg", "column": "message"}}, "series"),
        ({"query": "nosuchcolumn='x'"}, "query"),
        ({"group_by": "nosuch"}, "group_by"),
        ({"channels": [999]}, "channels"),
        ({"source": "nope"}, "source"),
    ],
)
def test_alert_validation(root_user, clickhouse_source, changes, field):
    doc = call(client_for(root_user), "post", "ui/v1/alerts", search_alert(**changes))
    assert not doc["result"]
    assert field in doc["validation"]["fields"], doc["validation"]


@pytest.mark.django_db
def test_docker_and_starrocks_accept_count_alerts(
    root_user, docker_source, starrocks_source
):
    client = client_for(root_user)
    for slug in ("docker", "starrocks"):
        doc = call(client, "post", "ui/v1/alerts", search_alert(source=slug, query=""))
        assert doc["result"], (slug, doc)
    doc = call(
        client,
        "post",
        "ui/v1/alerts",
        search_alert(
            source="docker", query="", series={"agg": "avg", "column": "status"}
        ),
    )
    assert not doc["result"]
    assert doc["validation"]["fields"]["series"] == {
        "agg": ["aggregation avg is not supported for docker sources"]
    }


@pytest.mark.django_db
def test_alert_needs_source_use(test_user, root_user, clickhouse_source):
    client = client_for(test_user)
    doc = call(client, "post", "ui/v1/alerts", search_alert())
    assert doc["validation"]["fields"]["source"] == ["source not found"]
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    assert call(client, "post", "ui/v1/alerts", search_alert())["result"]
    doc = call(client, "post", "ui/v1/alerts", search_alert(raw_query="1=1"))
    assert not doc["result"] and "raw" in str(doc["validation"]).lower()


@pytest.mark.django_db
def test_view_and_edit_rights(root_user, test_user, hacker_user, clickhouse_source):
    alert = call(client_for(root_user), "post", "ui/v1/alerts", search_alert())["data"]
    path = f"ui/v1/alerts/{alert['id']}"
    hacker = client_for(hacker_user)
    assert call(hacker, "get", "ui/v1/alerts")["data"] == []
    assert call(hacker, "get", path)["errors"] == ["Alert not found"]
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    viewer = client_for(test_user)
    seen = call(viewer, "get", path)["data"]
    assert seen["id"] == alert["id"] and seen["can_edit"] is False
    doc = call(viewer, "patch", path, search_alert(name="mine"))
    assert not doc["result"] and "owner" in doc["errors"][0]
    assert not call(viewer, "delete", path)["result"]
    assert Alert.objects.get().name == "Errors"


@pytest.mark.django_db
def test_tile_alert(test_user, clickhouse_source, dashboard):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    client = client_for(test_user)
    body = {
        "name": "Tile",
        "kind": "tile",
        "dashboard": dashboard.slug,
        "tile_id": "t1",
        "interval": "1m",
        "threshold_type": "above",
        "threshold": 10,
    }
    doc = call(client, "post", "ui/v1/alerts", body)
    assert doc["result"], doc
    alert = doc["data"]
    assert alert["source"] == clickhouse_source.slug
    assert alert["dashboard"] == {"slug": dashboard.slug, "name": dashboard.name}
    assert alert["series"] == {"agg": "count"}
    for changes, field in [
        ({"tile_id": "note1"}, "non_field_errors"),
        ({"tile_id": "zzz"}, "non_field_errors"),
        ({"series_index": 1}, "series_index"),
        ({"dashboard": "nope"}, "dashboard"),
    ]:
        doc = call(client, "post", "ui/v1/alerts", {**body, **changes})
        assert not doc["result"]
        assert field in doc["validation"]["fields"] or doc["validation"]["non_field"]


@pytest.mark.django_db
def test_private_dashboard_tile_is_refused(test_user, hacker_user, clickhouse_source):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=hacker_user
    )
    from tests.data import get_dashboard_data

    private = Dashboard.objects.create(
        slug="private-x",
        name="Private",
        owner=test_user,
        updated_by=test_user,
        data=get_dashboard_data(clickhouse_source.slug),
    )
    doc = call(
        client_for(hacker_user),
        "post",
        "ui/v1/alerts",
        {
            "name": "x",
            "kind": "tile",
            "dashboard": private.slug,
            "tile_id": "t1",
            "interval": "1m",
            "threshold_type": "above",
            "threshold": 1,
        },
    )
    assert doc["validation"]["non_field"] == ["dashboard not found"]


def channel(kind="webhook", **config):
    return {"name": f"{kind} channel", "kind": kind, "config": config}


@pytest.mark.django_db
def test_channels_need_permission(root_user, test_user, alerts_config):
    body = channel(url="http://127.0.0.1:9/hook")
    doc = call(client_for(test_user), "post", "ui/v1/alert-channels", body)
    assert not doc["result"] and "manage_alert_channels" in doc["errors"][0]
    GlobalRoleBinding.objects.create(user=test_user, role="admin")
    assert call(client_for(test_user), "post", "ui/v1/alert-channels", body)["result"]


@pytest.mark.django_db
def test_channel_secrets_masked_and_kept(root_user, test_user, alerts_config):
    admin = client_for(root_user)
    body = channel(
        url="https://hooks.example.com/services/T0/B0/secret",
        headers={"Authorization": "Bearer xyz"},
        body='{"text": {{ title|json }}}',
    )
    doc = call(admin, "post", "ui/v1/alert-channels", body)
    assert doc["result"], doc
    data = doc["data"]
    assert data["config"]["url"] == "https://hooks.example.com/****"
    assert data["config"]["headers"] == {"Authorization": "****"}
    listed = call(admin, "get", "ui/v1/alert-channels")["data"][0]
    assert listed["config"] == data["config"]
    # Non-managers see names only, to attach the channel to their alerts.
    assert call(client_for(test_user), "get", "ui/v1/alert-channels")["data"] == [
        {"id": data["id"], "name": "webhook channel", "kind": "webhook"}
    ]
    doc = call(
        admin,
        "patch",
        f"ui/v1/alert-channels/{data['id']}",
        {**body, "name": "renamed", "config": data["config"]},
    )
    assert doc["result"], doc
    stored = AlertChannel.objects.get()
    assert stored.config["url"] == body["config"]["url"]
    assert stored.config["headers"] == {"Authorization": "Bearer xyz"}
    assert stored.name == "renamed"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind,config,field",
    [
        ("webhook", {"url": "ftp://x"}, "url"),
        ("webhook", {"url": "https://x.example.com", "body": "{% if %}"}, "body"),
        ("slack", {}, "url"),
        ("pagerduty", {"routing_key": ""}, "routing_key"),
        ("pagerduty", {"routing_key": "k", "severity": "bad"}, "severity"),
        ("email", {"recipients": []}, "recipients"),
        ("email", {"recipients": ["not-an-email"]}, "recipients"),
    ],
)
def test_channel_validation(root_user, alerts_config, kind, config, field):
    doc = call(
        client_for(root_user), "post", "ui/v1/alert-channels", channel(kind, **config)
    )
    assert not doc["result"]
    assert field in doc["validation"]["fields"]["config"], doc["validation"]


@pytest.mark.django_db
def test_private_target_refused_unless_allowed(root_user, monkeypatch, settings):
    monkeypatch.setitem(
        settings.CONFIG, "alerts", {"allow_private_webhook_targets": False}
    )
    admin = client_for(root_user)
    for url in ["http://127.0.0.1:8080/x", "http://localhost/x", "http://10.1.2.3/x"]:
        doc = call(admin, "post", "ui/v1/alert-channels", channel(url=url))
        assert not doc["result"]
        assert "private or loopback" in doc["validation"]["fields"]["config"]["url"][0]
    monkeypatch.setitem(
        settings.CONFIG, "alerts", {"allow_private_webhook_targets": True}
    )
    doc = call(
        admin, "post", "ui/v1/alert-channels", channel(url="http://127.0.0.1:1/x")
    )
    assert doc["result"]


@pytest.mark.django_db
def test_send_test(root_user, receiver, alerts_config):
    admin = client_for(root_user)
    created = call(
        admin, "post", "ui/v1/alert-channels", channel("slack", url=receiver.url)
    )
    doc = call(admin, "post", f"ui/v1/alert-channels/{created['data']['id']}/test")
    assert doc["result"], doc
    sent = receiver.json()[0]
    assert sent["text"].startswith('Alert for "Test alert"')
    assert sent["blocks"][0]["type"] == "section"


@pytest.mark.django_db
def test_send_test_reports_failure(root_user, make_receiver, alerts_config):
    bad = make_receiver(status=404)
    admin = client_for(root_user)
    created = call(admin, "post", "ui/v1/alert-channels", channel(url=bad.url))
    doc = call(admin, "post", f"ui/v1/alert-channels/{created['data']['id']}/test")
    assert not doc["result"] and "HTTP 404" in doc["errors"][0]
    assert len(bad.requests) == 1  # 4xx is not retried
