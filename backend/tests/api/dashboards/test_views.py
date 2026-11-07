from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from telescope.fetchers.response import ChartDataResponse
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole

from tests.data import get_dashboard_data

rbac_manager = RBACManager()
T0 = 1762423200000


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def chart_body(**changes):
    body = {
        "from": str(T0),
        "to": str(T0 + 3600000),
        "query": "",
        "dashboard_query": "",
        "raw_query": "",
        "context_columns": {},
        "display": "line",
        "series": [{"agg": "count"}],
        "group_by": "",
        "granularity": "auto",
        "limit": 10,
    }
    body.update(changes)
    return body


@pytest.mark.django_db
def test_dashboard_crud(test_user, clickhouse_source):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    client = client_for(test_user)
    body = {
        "name": "Prod",
        "description": "",
        "shared": False,
        "data": get_dashboard_data(),
    }
    created = client.post("/ui/v1/dashboards", body, format="json").json()
    assert created["result"] is True
    assert created["messages"] == ["Dashboard has been created"]
    slug = created["data"]["slug"]
    assert created["data"]["version"] == 1

    listed = client.get("/ui/v1/dashboards").json()
    assert [d["slug"] for d in listed["data"]] == [slug]
    assert listed["data"][0]["tiles_count"] == 2

    got = client.get(f"/ui/v1/dashboards/{slug}").json()
    assert got["data"]["data"]["tiles"][1]["chart"]["text"] == "Runbook"

    body.update(name="Prod 2", version=1)
    updated = client.patch(f"/ui/v1/dashboards/{slug}", body, format="json").json()
    assert updated["messages"] == ["Dashboard has been updated"]
    assert updated["data"]["version"] == 2
    assert updated["data"]["slug"] == slug

    conflict = client.patch(f"/ui/v1/dashboards/{slug}", body, format="json").json()
    assert conflict["validation"]["result"] is False
    assert conflict["validation"]["fields"]["version"] == [
        "Dashboard was changed elsewhere, reload it"
    ]

    deleted = client.delete(f"/ui/v1/dashboards/{slug}").json()
    assert deleted == {
        "result": True,
        "data": {},
        "messages": ["Dashboard has been deleted"],
        "errors": [],
        "validation": {"result": True, "fields": {}, "non_field": []},
    }


@pytest.mark.django_db
def test_create_validation_fields(test_user):
    client = client_for(test_user)
    data = get_dashboard_data("missing")
    data["tiles"][1]["id"] = "t1"
    body = {"name": "", "description": "", "shared": False, "data": data}
    result = client.post("/ui/v1/dashboards", body, format="json").json()
    assert result["validation"]["result"] is False
    assert "name" in result["validation"]["fields"]
    assert result["validation"]["fields"]["data"]["tiles"] == ["duplicate tile id t1"]


@pytest.mark.django_db
def test_private_dashboard_not_found(hacker_user, dashboard):
    client = client_for(hacker_user)
    for response in [
        client.get(f"/ui/v1/dashboards/{dashboard.slug}"),
        client.delete(f"/ui/v1/dashboards/{dashboard.slug}"),
        client.patch(f"/ui/v1/dashboards/{dashboard.slug}", {}, format="json"),
    ]:
        assert response.status_code == 200
        assert response.json()["result"] is False
        assert response.json()["errors"] == ["Dashboard not found"]


@pytest.mark.django_db
def test_shared_dashboard_tile_needs_source_use(hacker_user, dashboard):
    dashboard.shared = True
    dashboard.save()
    client = client_for(hacker_user)
    got = client.get(f"/ui/v1/dashboards/{dashboard.slug}").json()
    assert got["data"]["permissions"] == ["read"]
    chart = got["data"]["data"]["tiles"][0]["chart"]

    with patch("telescope.views.source.views.get_fetchers") as get_fetchers:
        result = client.post(
            f"/ui/v1/sources/{chart['source']}/chartData",
            chart_body(group_by=chart["group_by"]),
            format="json",
        ).json()
        assert not get_fetchers.called
    assert result["result"] is False
    assert result["errors"] == ["Source not found or access denied"]
    assert result["data"] == {"code": "no_access"}


@pytest.mark.django_db
def test_chart_data_unknown_source(test_user):
    result = (
        client_for(test_user)
        .post("/ui/v1/sources/nope/chartData", chart_body(), format="json")
        .json()
    )
    assert result["data"] == {"code": "no_access"}


@pytest.mark.django_db
def test_chart_data_raw_query_permission(test_user, clickhouse_source):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    client = client_for(test_user)
    url = f"/ui/v1/sources/{clickhouse_source.slug}/chartData"
    result = client.post(url, chart_body(raw_query="1 = 1"), format="json").json()
    assert result["validation"]["result"] is False
    assert result["validation"]["non_field"] == [
        "Insufficient permissions to use source raw queries"
    ]

    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.RAW_QUERY_USER.value, user=test_user
    )
    fetcher = MagicMock()
    fetcher.fetch_chart_data.return_value = ChartDataResponse("number", 1, 2, value=3)
    with patch("telescope.views.source.views.get_fetchers") as get_fetchers:
        get_fetchers.return_value = {"clickhouse": fetcher}
        result = client.post(url, chart_body(raw_query="1 = 1"), format="json").json()
    assert result["result"] is True, result
    assert fetcher.fetch_chart_data.call_args.args[0].raw_query == "1 = 1"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "changes, field",
    [
        ({"to": str(T0)}, "to"),
        ({"display": "text"}, "display"),
        ({"display": "number", "group_by": "hostname"}, "group_by"),
        ({"series": []}, "series"),
        ({"series": [{"agg": "sum", "column": "hostname"}]}, "series"),
        ({"group_by": "hostname, level"}, "group_by"),
        ({"granularity": "2m"}, "granularity"),
        ({"limit": 51}, "limit"),
        ({"query": "nope = 1"}, "query"),
        ({"dashboard_query": "nope = 1"}, "dashboard_query"),
    ],
)
def test_chart_data_validation(root_user, clickhouse_source, changes, field):
    url = f"/ui/v1/sources/{clickhouse_source.slug}/chartData"
    result = (
        client_for(root_user).post(url, chart_body(**changes), format="json").json()
    )
    assert result["validation"]["result"] is False
    assert field in result["validation"]["fields"], result["validation"]
    if field == "to":
        assert result["validation"]["fields"]["to"] == ["must be after from"]


@pytest.mark.django_db
def test_chart_data_docker_count_only(root_user, docker_source):
    url = f"/ui/v1/sources/{docker_source.slug}/chartData"
    body = chart_body(series=[{"agg": "uniq", "column": "stream"}])
    result = client_for(root_user).post(url, body, format="json").json()
    assert result["validation"]["fields"]["series"] == {
        "0": {"agg": ["aggregation uniq is not supported for docker sources"]}
    }


@pytest.mark.django_db
def test_chart_data_combines_queries(root_user, clickhouse_source):
    url = f"/ui/v1/sources/{clickhouse_source.slug}/chartData"
    fetcher = MagicMock()
    fetcher.fetch_chart_data.return_value = ChartDataResponse(
        "table", 1, 2, columns=[], rows=[]
    )
    client = client_for(root_user)
    with patch("telescope.views.source.views.get_fetchers") as get_fetchers:
        get_fetchers.return_value = {"clickhouse": fetcher}
        for query, dashboard_query, expected in [
            (
                "level = 'Error'",
                "hostname = 'a'",
                "(level = 'Error') and (hostname = 'a')",
            ),
            ("level = 'Error'", "", "level = 'Error'"),
            ("", "hostname = 'a'", "hostname = 'a'"),
            ("", "", ""),
        ]:
            body = chart_body(
                display="table",
                query=query,
                dashboard_query=dashboard_query,
                group_by="hostname",
            )
            result = client.post(url, body, format="json").json()
            request = fetcher.fetch_chart_data.call_args.args[0]
            assert request.query == expected
            assert [c.name for c in request.group_by] == ["hostname"]
    assert result["data"] == {
        "kind": "table",
        "from": 1,
        "to": 2,
        "columns": [],
        "rows": [],
        "truncated": False,
    }


@pytest.mark.django_db
def test_chart_data_query_failed(root_user, clickhouse_source):
    url = f"/ui/v1/sources/{clickhouse_source.slug}/chartData"
    fetcher = MagicMock()
    fetcher.fetch_chart_data.side_effect = RuntimeError("Timeout exceeded")
    with patch("telescope.views.source.views.get_fetchers") as get_fetchers:
        get_fetchers.return_value = {"clickhouse": fetcher}
        result = client_for(root_user).post(url, chart_body(), format="json").json()
    assert result["result"] is False
    assert result["errors"] == ["Timeout exceeded"]
    assert result["data"] == {"code": "query_failed"}
