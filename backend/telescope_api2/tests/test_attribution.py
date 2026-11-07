import json

import pytest

from telescope import query_attribution as qa
from telescope.fetchers import clickhouse
from telescope.models import Dashboard
from tests.data import get_dashboard_data
from telescope_alerts.evaluator import evaluate_alert
from telescope_alerts.models import Alert

from telescope_api2.tests.conftest import (
    chart_body,
    search_body,
    session_client,
    token_client,
)


class Client:
    def __init__(self):
        self.calls = []

    def query(self, sql, **kw):
        self.calls.append(kw)


def comments(fake_ch):
    return [
        json.loads(c.kwargs["settings"]["log_comment"])
        for c in fake_ch.query.call_args_list
    ]


def test_outside_a_block_queries_are_untouched():
    client = Client()
    clickhouse._client_query(client, "SELECT 1", parameters={"a": 1})
    assert client.calls == [{"parameters": {"a": 1}}]


def test_log_comment_merges_settings_and_sanitises():
    client = Client()
    with qa.attribute(surface="dashboard", dashboard="a&b?c", user=lambda: 7):
        with qa.attribute(tile="t" * 300):
            clickhouse._client_query(client, "SELECT 1", settings={"x": 1})
    settings = client.calls[0]["settings"]
    assert settings["x"] == 1
    assert json.loads(settings["log_comment"]) == {
        "surface": "dashboard",
        "dashboard": "a_b_c",
        "tile": "t" * 128,
        "user": 7,
    }


@pytest.mark.django_db
def test_dashboard_tile_query(root_user, ch_source, fake_ch):
    response = session_client(root_user).post(
        f"/ui/v1/sources/{ch_source.slug}/chartData?dashboard=ops-1a2b3c&tile=t1",
        chart_body(),
        format="json",
    )
    assert response.json()["result"], response.json()
    assert comments(fake_ch) == [
        {
            "surface": "dashboard",
            "dashboard": "ops-1a2b3c",
            "tile": "t1",
            "source": ch_source.slug,
            "user": root_user.pk,
        }
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path, surface",
    [("chartData", "chart-preview"), ("data", "search")],
)
def test_ui_surfaces(root_user, ch_source, fake_ch, path, surface):
    body = chart_body() if path == "chartData" else search_body()
    session_client(root_user).post(
        f"/ui/v1/sources/{ch_source.slug}/{path}", body, format="json"
    )
    assert {c["surface"] for c in comments(fake_ch)} == {surface}


@pytest.mark.django_db
def test_api_user_comes_from_the_token(test_user, root_user, ch_source, fake_ch):
    token_client(root_user).post(
        f"/api/v1/sources/{ch_source.slug}/chart", chart_body(), format="json"
    )
    assert comments(fake_ch) == [
        {"surface": "api", "source": ch_source.slug, "user": root_user.pk}
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["search", "tile"])
def test_alert_evaluation(root_user, ch_source, fake_ch, kind):
    fake_ch.query.return_value.result_rows = [(0,)]
    fields = dict(
        name="a",
        owner=root_user,
        kind=kind,
        source_slug=ch_source.slug,
        series={"agg": "count"},
        interval="5m",
        threshold_type="above",
        threshold=1,
    )
    expected = {"surface": "alert", "user": root_user.pk}
    if kind == "tile":
        fields["dashboard"] = Dashboard.objects.create(
            slug="ops",
            name="ops",
            owner=root_user,
            updated_by=root_user,
            data=get_dashboard_data(ch_source.slug),
        )
        fields["dashboard"].data["tiles"][0]["chart"]["group_by"] = ""
        fields["dashboard"].save()
        fields["tile_id"] = "t1"
        expected.update(dashboard="ops", tile="t1")
    alert = Alert.objects.create(**fields)
    assert evaluate_alert(alert) > 0
    expected["alert"] = alert.pk
    assert comments(fake_ch) and all(c == expected for c in comments(fake_ch))
