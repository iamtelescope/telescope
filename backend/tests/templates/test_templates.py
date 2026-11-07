"""Roadmap P4.2: dashboard templates, "create from template" and provisioning by slug."""

import json

import pytest
from django.core.management import CommandError, call_command
from rest_framework.test import APIClient

from telescope.models import Dashboard
from telescope.serializers.dashboard import NewDashboardSerializer
from telescope_otel.provision import (
    TemplateError,
    instantiate,
    load_templates,
    placeholder_roles,
    provision,
)
from tests.templates.helpers import otel_source, system_sources

pytestmark = pytest.mark.django_db

RUNTIME = [
    "jvm-runtime",
    "go-runtime",
    "nodejs-runtime",
    "python-runtime",
    "dotnet-runtime",
]


@pytest.fixture
def otel(clickhouse_connection):
    sources = {
        "traces": otel_source(clickhouse_connection, "traces", "otel_traces"),
        "logs": otel_source(clickhouse_connection, "logs", "otel_logs"),
        "metrics": otel_source(clickhouse_connection, "metrics", "otel_metrics_gauge"),
    }
    sources["traces"].data["otel"]["links"] = {"logs": "logs"}
    sources["traces"].save()
    return sources


@pytest.fixture
def system(clickhouse_connection):
    return system_sources(clickhouse_connection)


def bind(template, otel, system):
    pool = {**otel, **system}
    return {role: pool[role] for role in template["roles"]}


def validate(user, data):
    serializer = NewDashboardSerializer(
        data={"name": "x", "description": "", "shared": False, "data": data},
        context={"user": user, "old_sources": set()},
    )
    assert serializer.is_valid(), serializer.errors
    return serializer.validated_data["data"]


def test_gallery_has_every_template():
    assert set(load_templates()) == {"services", "kubernetes", "clickhouse", *RUNTIME}


@pytest.mark.parametrize("slug", sorted(load_templates()))
def test_every_template_validates_through_the_serializer(slug, root_user, otel, system):
    template = load_templates()[slug]
    data = validate(root_user, instantiate(template, bind(template, otel, system)))
    assert len(data["tiles"]) == len(template["dashboard"]["tiles"])
    assert "{{" not in json.dumps(data)


@pytest.mark.parametrize("slug", sorted(load_templates()))
def test_template_tiles_only_use_declared_roles(slug):
    template = load_templates()[slug]
    assert placeholder_roles(template["dashboard"]) <= set(template["roles"])
    ids = [t["id"] for t in template["dashboard"]["tiles"]]
    assert len(ids) == len(set(ids))


def test_services_binds_roles_to_columns(root_user, otel):
    data = instantiate(load_templates()["services"], {"traces": otel["traces"]})
    tiles = {t["id"]: t for t in data["tiles"]}
    top = tiles["top-endpoints"]["chart"]
    assert top["source"] == "traces"
    assert top["group_by"] == "ServiceName, SpanName"
    assert "SpanKind in ['Server', 'SPAN_KIND_SERVER']" in top["query"]
    assert top["series"][1]["formula"] == "total / 1000000"
    assert tiles["p95"]["chart"]["number_format"]["unit"] == "duration_ns"
    assert tiles["db-time"]["chart"]["group_by"] == "SpanAttributes.'db.statement'"
    assert data["variables"][0] == {
        "name": "service",
        "label": "Service",
        "type": "values",
        "source": "traces",
        "column": "ServiceName",
        "multi": True,
    }


def test_optional_role_left_out_drops_its_tiles(root_user, otel):
    data = validate(
        root_user,
        instantiate(load_templates()["kubernetes"], {"metrics": otel["metrics"]}),
    )
    assert all(t["chart"]["source"] == "metrics" for t in data["tiles"])
    assert "logs" not in {s["id"] for s in data["sections"]}
    assert {t["section"] for t in data["tiles"]} == {"pods", "nodes", "namespaces"}


def test_clickhouse_template_with_parts_only(root_user, system):
    data = validate(
        root_user,
        instantiate(load_templates()["clickhouse"], {"parts": system["parts"]}),
    )
    assert {t["id"] for t in data["tiles"]} == {
        "parts-per-partition",
        "parts-by-table",
    }
    assert [s["id"] for s in data["sections"]] == ["parts"]


def test_clickhouse_template_needs_one_role():
    with pytest.raises(TemplateError, match="at least one role"):
        instantiate(load_templates()["clickhouse"], {})


def test_required_role_is_required(otel):
    with pytest.raises(TemplateError, match="pick a source for Traces"):
        instantiate(load_templates()["services"], {"logs": otel["logs"]})


def test_source_must_fit_the_role(otel, system):
    template = load_templates()["services"]
    with pytest.raises(TemplateError, match="does not fit Traces"):
        instantiate(template, {"traces": otel["logs"]})
    with pytest.raises(TemplateError, match="does not fit Parts"):
        instantiate(load_templates()["clickhouse"], {"parts": system["query_log"]})
    with pytest.raises(TemplateError, match="unknown role"):
        instantiate(template, {"traces": otel["traces"], "nope": otel["logs"]})


def test_missing_column_role_is_reported(otel):
    otel["traces"].data["otel"]["roles"]["status_code"] = ""
    with pytest.raises(TemplateError, match="has no status_code column"):
        instantiate(load_templates()["services"], {"traces": otel["traces"]})


def test_duration_precision_sets_unit_and_divisor(otel):
    otel["traces"].data["otel"]["roles"]["duration_precision"] = 6
    data = instantiate(load_templates()["services"], {"traces": otel["traces"]})
    tiles = {t["id"]: t for t in data["tiles"]}
    assert tiles["p95"]["chart"]["number_format"]["unit"] == "duration_us"
    assert tiles["top-endpoints"]["chart"]["series"][1]["formula"] == "total / 1000"


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def test_list_offers_candidates_and_linked_default(root_user, otel, system):
    result = client_for(root_user).get("/ui/v1/dashboard-templates").json()
    assert result["result"] is True
    by_slug = {t["slug"]: t for t in result["data"]}
    roles = {r["name"]: r for r in by_slug["services"]["roles"]}
    assert roles["traces"]["candidates"] == [{"slug": "traces", "name": "traces"}]
    assert roles["traces"]["default"] == "traces"
    assert roles["logs"]["default"] == "logs"
    assert roles["logs"]["optional"] is True
    ch = {r["name"]: r for r in by_slug["clickhouse"]["roles"]}
    assert ch["parts"]["candidates"] == [{"slug": "ch-parts", "name": "ch-parts"}]
    assert ch["parts"]["table"] == "system.parts"


def test_list_hides_sources_the_user_cannot_use(test_user, otel):
    result = client_for(test_user).get("/ui/v1/dashboard-templates").json()
    services = next(t for t in result["data"] if t["slug"] == "services")
    assert all(not r["candidates"] for r in services["roles"])


def test_create_from_template_makes_a_normal_dashboard(root_user, otel):
    body = {
        "name": "Shop services",
        "shared": True,
        "sources": {"traces": "traces", "logs": "logs"},
    }
    result = client_for(root_user).post(
        "/ui/v1/dashboard-templates/services", body, format="json"
    )
    assert result.json()["result"] is True, result.json()
    slug = result.json()["data"]["slug"]
    dashboard = Dashboard.objects.get(slug=slug)
    assert dashboard.name == "Shop services" and dashboard.shared
    assert dashboard.owner == root_user
    assert dashboard.data["tiles"][0]["chart"]["source"] == "traces"
    fetched = client_for(root_user).get(f"/ui/v1/dashboards/{slug}").json()
    assert fetched["data"]["data"]["variables"][0]["source"] == "traces"


def test_create_from_template_rejects_foreign_sources(test_user, otel):
    result = client_for(test_user).post(
        "/ui/v1/dashboard-templates/services",
        {"name": "x", "sources": {"traces": "traces"}},
        format="json",
    )
    assert result.json()["result"] is False
    assert result.json()["errors"] == ["source traces not found"]
    assert not Dashboard.objects.exists()


def test_create_from_unknown_template(root_user):
    result = client_for(root_user).post(
        "/ui/v1/dashboard-templates/nope", {"name": "x", "sources": {}}, format="json"
    )
    assert result.json()["errors"] == ["template nope not found"]


def write(path, item):
    path.write_text(json.dumps(item))
    return path


def test_provisioning_a_directory_twice_is_idempotent(root_user, otel, tmp_path):
    write(
        tmp_path / "services.json",
        {
            "slug": "prod-services",
            "template": "services",
            "sources": {"traces": "traces"},
        },
    )
    write(
        tmp_path / "plain.json",
        {
            "telescope_dashboard": 1,
            "name": "Plain",
            "data": {
                "version": 3,
                "time": {"from": "now-1h", "to": "now"},
                "query": "",
                "refresh": "off",
                "variables": [],
                "sections": [],
                "tiles": [],
            },
        },
    )
    first = provision([str(tmp_path)], root_user)
    assert [(slug, action) for _, slug, action in first] == [
        ("plain", "created"),
        ("prod-services", "created"),
    ]
    versions = dict(Dashboard.objects.values_list("slug", "version"))
    second = provision([str(tmp_path)], root_user)
    assert [action for _, _, action in second] == ["unchanged", "unchanged"]
    assert Dashboard.objects.count() == 2
    assert dict(Dashboard.objects.values_list("slug", "version")) == versions
    services = Dashboard.objects.get(slug="prod-services")
    assert services.name == "Services" and services.shared


def test_provisioning_updates_by_slug(root_user, otel, tmp_path):
    path = write(
        tmp_path / "k8s.json",
        {"slug": "k8s", "template": "kubernetes", "sources": {"metrics": "metrics"}},
    )
    provision([str(path)], root_user)
    dashboard = Dashboard.objects.get(slug="k8s")
    dashboard.name = "Edited in the UI"
    dashboard.save()
    write(
        path,
        {
            "slug": "k8s",
            "name": "Kubernetes prod",
            "template": "kubernetes",
            "sources": {"metrics": "metrics", "logs": "logs"},
        },
    )
    assert provision([str(path)], root_user)[0][2] == "updated"
    dashboard.refresh_from_db()
    assert dashboard.name == "Kubernetes prod"
    assert dashboard.version == 2
    assert any(t["chart"]["source"] == "logs" for t in dashboard.data["tiles"])


def test_provisioning_reports_bad_files_and_keeps_going(root_user, otel, tmp_path):
    (tmp_path / "a.json").write_text("{not json")
    write(tmp_path / "b.json", {"slug": "b", "template": "services", "sources": {}})
    write(
        tmp_path / "c.json",
        {"slug": "c", "template": "services", "sources": {"traces": "missing"}},
    )
    write(tmp_path / "d.json", {"slug": "d", "template": "go-runtime", "sources": {}})
    write(
        tmp_path / "e.json",
        {"slug": "e", "template": "go-runtime", "sources": {"metrics": "metrics"}},
    )
    results = {
        slug or path[-6:]: action
        for path, slug, action in provision([str(tmp_path)], root_user)
    }
    assert results["a.json"].startswith("error")
    assert results["b.json"] == "error: pick a source for Traces"
    assert results["c.json"] == "error: source missing not found"
    assert results["e"] == "created"
    assert list(Dashboard.objects.values_list("slug", flat=True)) == ["e"]


def test_provisioning_validates_the_data(root_user, tmp_path):
    path = write(
        tmp_path / "bad.json",
        {"name": "Bad", "data": {"version": 3, "tiles": [{"id": "x"}]}},
    )
    assert provision([str(path)], root_user)[0][2].startswith("error: {")
    assert not Dashboard.objects.exists()


def test_command_upserts_and_fails_on_errors(root_user, otel, tmp_path, capsys):
    write(
        tmp_path / "svc.json",
        {"slug": "svc", "template": "services", "sources": {"traces": "traces"}},
    )
    call_command("telescope_provision_dashboards", str(tmp_path))
    call_command("telescope_provision_dashboards", str(tmp_path))
    out = capsys.readouterr().out
    assert "svc created" in out and "svc unchanged" in out
    write(tmp_path / "bad.json", {"slug": "bad", "template": "nope"})
    with pytest.raises(CommandError, match="1 file"):
        call_command("telescope_provision_dashboards", str(tmp_path))
    with pytest.raises(CommandError, match="user not found"):
        call_command("telescope_provision_dashboards", str(tmp_path), username="nobody")


def test_provisioning_never_touches_a_user_dashboard(root_user, test_user, tmp_path):
    data = {
        "version": 3,
        "time": {"from": "now-1h", "to": "now"},
        "query": "",
        "refresh": "off",
        "variables": [],
        "sections": [],
        "tiles": [],
    }
    Dashboard.objects.create(
        slug="mine", name="Mine", owner=root_user, shared=False, data=data
    )
    path = write(tmp_path / "mine.json", {"name": "Provisioned", "data": data})
    for user in (test_user, root_user):
        assert provision([str(path)], user)[0][2].startswith("error: slug mine")
    mine = Dashboard.objects.get(slug="mine")
    assert (mine.name, mine.shared, mine.version) == ("Mine", False, 1)


def test_provisioning_needs_edit_on_a_provisioned_dashboard(
    root_user, test_user, tmp_path
):
    data = {
        "version": 3,
        "time": {"from": "now-1h", "to": "now"},
        "query": "",
        "refresh": "off",
        "variables": [],
        "sections": [],
        "tiles": [],
    }
    path = write(tmp_path / "p.json", {"name": "P", "data": data})
    assert provision([str(path)], root_user)[0][2] == "created"
    write(path, {"name": "Changed", "data": data})
    assert (
        provision([str(path)], test_user)[0][2] == "error: user cannot edit dashboard p"
    )
    assert Dashboard.objects.get(slug="p").name == "P"
