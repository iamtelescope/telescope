from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from telescope.fetchers.chart import ChartResult
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole

rbac_manager = RBACManager()
T0 = 1762423200000
DELTAS = "telescope.views.source.deltas.fetch_deltas"
HEATMAP = "telescope.views.source.deltas.fetch_heatmap"
OUTLIER = {"y_min": 10, "y_max": 100, "t_min": T0, "t_max": T0 + 60000}


def client_for(user, source=None):
    if source is not None:
        rbac_manager.grant_source_role(source, SourceRole.USER.value, user=user)
    client = APIClient()
    client.force_login(user)
    return client


def body(**changes):
    data = {"from": str(T0), "to": str(T0 + 3600000), "column": "thread_id"}
    data.update(changes)
    return data


def post(client, source, path, data):
    return client.post(
        f"/ui/v1/sources/{source.slug}/{path}", data, format="json"
    ).json()


@pytest.mark.django_db
def test_deltas_pass_the_selection(test_user, clickhouse_source):
    client = client_for(test_user, clickhouse_source)
    with patch(DELTAS, return_value={"properties": []}) as fetch:
        result = post(
            client,
            clickhouse_source,
            "deltas",
            body(query="hostname='h1'", text="boom", outlier=OUTLIER, sample=100),
        )
    assert result["result"] is True and result["data"] == {"properties": []}
    selection, outlier, sample = fetch.call_args.args
    assert (selection.time_from, selection.time_to) == (T0, T0 + 3600000)
    assert (selection.column, selection.query, selection.text) == (
        "thread_id",
        "hostname='h1'",
        "boom",
    )
    assert outlier == {**OUTLIER, "y_min": 10.0, "y_max": 100.0} and sample == 100


@pytest.mark.django_db
def test_deltas_default_sample(test_user, clickhouse_source):
    client = client_for(test_user, clickhouse_source)
    with patch(DELTAS, return_value={}) as fetch:
        post(client, clickhouse_source, "deltas", body(outlier=OUTLIER))
    assert fetch.call_args.args[2] == 5000


@pytest.mark.django_db
@pytest.mark.parametrize(
    "changes, field",
    [
        ({"column": "message"}, "column"),
        ({"column": "nope"}, "column"),
        ({"outlier": {**OUTLIER, "y_min": 1000}}, "outlier"),
        ({"outlier": {**OUTLIER, "t_max": T0 - 1}}, "outlier"),
        ({"outlier": None}, "outlier"),
        ({"sample": 0}, "sample"),
        ({"sample": 20_001}, "sample"),
        ({"query": "nope=1"}, "query"),
        ({"to": str(T0)}, "to"),
        ({"raw_query": "1=1"}, "non_field"),
    ],
)
def test_deltas_validation(test_user, clickhouse_source, changes, field):
    client = client_for(test_user, clickhouse_source)
    data = body(**{"outlier": OUTLIER, **changes})
    if data["outlier"] is None:
        del data["outlier"]
    with patch(DELTAS) as fetch:
        result = post(client, clickhouse_source, "deltas", data)
    assert not fetch.called
    assert result["validation"]["result"] is False
    assert field in result["validation"]["fields"] or result["validation"][field]


@pytest.mark.django_db
def test_heatmap_view(test_user, clickhouse_source):
    client = client_for(test_user, clickhouse_source)
    chart = ChartResult(kind="heatmap", time_from=T0, time_to=T0 + 1, extra={"x": 1})
    with patch(HEATMAP, return_value=chart) as fetch:
        result = post(client, clickhouse_source, "heatmap", body(granularity="1m"))
    assert result["data"] == {
        "kind": "heatmap",
        "from": T0,
        "to": T0 + 1,
        "columns": [],
        "rows": [],
        "truncated": False,
        "x": 1,
    }
    assert fetch.call_args.args[1] == "1m"


@pytest.mark.django_db
def test_deltas_need_source_use_and_clickhouse(
    hacker_user, test_user, clickhouse_source, docker_source
):
    with patch(DELTAS) as fetch:
        result = post(
            client_for(hacker_user), clickhouse_source, "deltas", body(outlier=OUTLIER)
        )
        assert result["errors"] == ["source not found"]
        result = post(
            client_for(test_user, docker_source), docker_source, "heatmap", body()
        )
        assert result["errors"] == ["deltas are not supported for docker sources"]
    assert not fetch.called


@pytest.mark.django_db
def test_chart_data_heatmap_goes_to_the_heatmap_fetch(test_user, clickhouse_source):
    client = client_for(test_user, clickhouse_source)
    chart = ChartResult(kind="heatmap", time_from=T0, time_to=T0 + 1)
    data = {
        "from": str(T0),
        "to": str(T0 + 3600000),
        "query": "hostname='a'",
        "display": "heatmap",
        "series": [{"agg": "heatmap", "column": "thread_id", "where": "level='Error'"}],
    }
    with patch("telescope.fetchers.deltas.fetch_heatmap", return_value=chart) as fetch:
        result = client.post(
            f"/ui/v1/sources/{clickhouse_source.slug}/chartData", data, format="json"
        ).json()
    assert result["result"] is True and result["data"]["kind"] == "heatmap"
    selection, granularity = fetch.call_args.args
    assert selection.column == "thread_id" and granularity == "auto"
    assert selection.query == "(hostname='a') and (level='Error')"
    bad = {**data, "series": [{"agg": "heatmap", "column": "message"}]}
    result = client.post(
        f"/ui/v1/sources/{clickhouse_source.slug}/chartData", bad, format="json"
    ).json()
    assert result["validation"]["fields"]["series"] == {
        "0": {"column": ["column message is not numeric"]}
    }
