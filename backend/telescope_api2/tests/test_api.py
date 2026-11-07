import re

import pytest
from django.urls import get_resolver
from rest_framework.test import APIClient

from telescope.models import Dashboard
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from tests.data import get_dashboard_data

from telescope_api2 import throttle, urls
from telescope_api2.tests.conftest import (
    chart_body,
    search_body,
    session_client,
    token_client,
)

rbac_manager = RBACManager()


@pytest.mark.django_db
def test_token_required(root_user):
    anonymous = APIClient()
    assert anonymous.get("/api/v1/dashboards").status_code in (401, 403)
    anonymous.credentials(HTTP_AUTHORIZATION="Token nope")
    assert anonymous.get("/api/v1/dashboards").status_code in (401, 403)
    # A browser session is not a token.
    assert session_client(root_user).get("/api/v1/dashboards").status_code in (
        401,
        403,
    )


@pytest.mark.django_db
def test_deactivated_user_token_is_refused(root_user, ch_source):
    client = token_client(root_user)
    assert client.get("/api/v1/dashboards").status_code == 200
    root_user.is_active = False
    root_user.save()
    assert client.get("/api/v1/dashboards").status_code in (401, 403)
    body = {"name": "x", "description": "", "data": get_dashboard_data()}
    assert client.post("/api/v1/dashboards", body, format="json").status_code in (
        401,
        403,
    )
    assert not Dashboard.objects.filter(name="x").exists()


@pytest.mark.django_db
def test_dashboard_crud_and_codes(test_user, ch_source):
    rbac_manager.grant_source_role(ch_source, SourceRole.USER.value, user=test_user)
    client = token_client(test_user)
    body = {"name": "Prod", "description": "", "shared": False}
    body["data"] = get_dashboard_data()
    created = client.post("/api/v1/dashboards", body, format="json")
    assert created.status_code == 201
    slug = created.json()["slug"]
    assert client.get(f"/api/v1/dashboards/{slug}").json()["name"] == "Prod"
    patched = client.patch(
        f"/api/v1/dashboards/{slug}", {**body, "version": 1}, format="json"
    )
    assert patched.status_code == 200 and patched.json()["version"] == 2
    stale = client.patch(
        f"/api/v1/dashboards/{slug}", {**body, "version": 1}, format="json"
    )
    assert stale.status_code == 400 and "version" in stale.json()["validation"]
    assert client.delete(f"/api/v1/dashboards/{slug}").status_code == 204
    assert client.get(f"/api/v1/dashboards/{slug}").status_code == 404


@pytest.mark.django_db
def test_list_paginates(root_user):
    for n in range(5):
        Dashboard.objects.create(
            slug=f"d{n}", name=f"d{n}", owner=root_user, updated_by=root_user, data={}
        )
    client = token_client(root_user)
    pages = [
        client.get(f"/api/v1/dashboards?page={p}&page_size=2").json() for p in [1, 2, 3]
    ]
    assert [len(p["data"]) for p in pages] == [2, 2, 1]
    assert [p["has_more"] for p in pages] == [True, True, False]
    assert {p["total"] for p in pages} == {5}
    slugs = [d["slug"] for p in pages for d in p["data"]]
    assert sorted(slugs) == [f"d{n}" for n in range(5)]
    bad = client.get("/api/v1/dashboards?page=x")
    assert bad.status_code == 400
    capped = client.get("/api/v1/dashboards?page_size=100000").json()
    assert capped["page_size"] == 500


@pytest.mark.django_db
def test_saved_views_list_all_sources(root_user, ch_source, docker_source):
    client = token_client(root_user)
    for source in [ch_source.slug, docker_source.slug]:
        body = {"name": f"v {source}", "description": "", "shared": False}
        body.update(scope="personal", source=source, data={"query": ""})
        assert (
            client.post("/api/v1/saved-views", body, format="json").status_code == 201
        )
    listed = client.get("/api/v1/saved-views").json()
    assert sorted(v["name"] for v in listed["data"]) == ["v clickhouse", "v docker"]
    one = client.get(f"/api/v1/saved-views?source={docker_source.slug}").json()
    assert [v["name"] for v in one["data"]] == ["v docker"]
    missing = client.post("/api/v1/saved-views", {"name": "x"}, format="json")
    assert missing.status_code == 400


@pytest.mark.django_db
def test_search_pages_with_cursor(root_user, ch_source, fake_ch):
    client = token_client(root_user)
    response = client.post(
        f"/api/v1/sources/{ch_source.slug}/search", search_body(), format="json"
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["rows"] == [] and body["cursor"] is None
    minimal = search_body()
    del minimal["context_columns"], minimal["query"], minimal["raw_query"]
    response = client.post(
        f"/api/v1/sources/{ch_source.slug}/search", minimal, format="json"
    )
    assert response.status_code == 200, response.content
    assert [c["name"] for c in body["columns"]] == ["hostname"]
    invalid = client.post(
        f"/api/v1/sources/{ch_source.slug}/search",
        search_body(limit="x"),
        format="json",
    )
    assert invalid.status_code == 400 and "limit" in invalid.json()["validation"]


@pytest.mark.django_db
def test_query_error_is_400(root_user, ch_source, fake_ch):
    fake_ch.query.side_effect = RuntimeError("Code: 62. Syntax error")
    response = token_client(root_user).post(
        f"/api/v1/sources/{ch_source.slug}/chart", chart_body(), format="json"
    )
    assert response.status_code == 400
    assert response.json()["errors"] == ["Code: 62. Syntax error"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role, debug",
    [(SourceRole.USER.value, False), (SourceRole.RAW_QUERY_USER.value, True)],
)
@pytest.mark.parametrize("api", ["ui", "v2"])
def test_debug_sql_only_with_raw_query(test_user, ch_source, fake_ch, role, debug, api):
    rbac_manager.grant_source_role(ch_source, role, user=test_user)
    if api == "ui":
        response = session_client(test_user).post(
            f"/ui/v1/sources/{ch_source.slug}/chartData", chart_body(), format="json"
        )
        data = response.json()["data"]
    else:
        response = token_client(test_user).post(
            f"/api/v1/sources/{ch_source.slug}/chart", chart_body(), format="json"
        )
        data = response.json()
    assert ("debug" in data) == debug
    if debug:
        sql = data["debug"]["sql"]
        assert sql == [fake_ch.query.call_args.args[0]]
        assert sql[0].startswith("SELECT") and "FROM db.logs" in sql[0]


@pytest.mark.django_db
def test_debug_sql_on_search(root_user, ch_source, fake_ch):
    data = session_client(root_user).post(
        f"/ui/v1/sources/{ch_source.slug}/data", search_body(), format="json"
    )
    assert data.json()["data"]["debug"]["sql"][0].startswith("SELECT")


@pytest.mark.django_db
def test_rate_limit(root_user, monkeypatch):
    monkeypatch.setattr(throttle, "RATE_LIMIT_PER_MINUTE", 3)
    client = token_client(root_user)
    codes = [client.get("/api/v1/dashboards").status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    assert 0 < int(client.get("/api/v1/dashboards")["Retry-After"]) <= 60


@pytest.mark.django_db
def test_openapi_lists_every_route():
    response = APIClient().get("/api/v1/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["openapi"].startswith("3.")
    routes = {
        "/" + re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", str(p.pattern))
        for p in urls.urlpatterns
    }
    routes = {r.replace("{pk}", "{id}") for r in routes} - {"/api/v1/openapi.json"}
    assert routes <= set(spec["paths"])
    for path, methods in spec["paths"].items():
        for name in re.findall(r"{(\w+)}", path):
            for method in methods.values():
                assert name in [p["name"] for p in method.get("parameters", [])], (
                    path,
                    name,
                )


def test_routes_resolve_before_the_api_stub():
    resolver = get_resolver()
    for path in ["/api/v1/dashboards", "/api/v1/sources/x/search", "/api/v1/alerts/1"]:
        assert (
            resolver.resolve(path).func.view_class.__module__ == "telescope_api2.views"
        )


@pytest.mark.django_db
def test_chart_compare_queries_the_previous_period(root_user, ch_source, fake_ch):
    response = token_client(root_user).post(
        f"/api/v1/sources/{ch_source.slug}/chart",
        chart_body(compare=True),
        format="json",
    )
    assert response.status_code == 200, response.content
    assert fake_ch.query.call_count == 2
    assert response.json()["previous_offset_ms"] == 3600000
