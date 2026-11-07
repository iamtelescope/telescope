"""P3.3 release markers: row reduction, role checks and the releases endpoint without ClickHouse."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope_otel.releases import release_columns, releases_from_rows, scope_where
from tests.otel import columns as C
from tests.otel.test_trace import make_source

rbac_manager = RBACManager()
BODY = {
    "from": "1000000",
    "to": "2000000",
    "query": "",
    "display": "line",
    "series": [{"agg": "count"}],
}


def post(user, slug, body):
    client = APIClient()
    client.force_login(user)
    return client.post(f"/ui/v1/otel/{slug}/releases", body, format="json").json()


def test_first_version_of_each_service_is_not_a_release():
    rows = [
        ("checkout", "1.4.0", 100),
        ("cart", "2.0.0", 50),
        ("checkout", "1.5.0", 900),
        ("cart", "2.1.0", 400),
        ("api", "3.0.0", 600),
    ]
    assert releases_from_rows(rows, 500) == [
        {"time": 900, "service": "checkout", "version": "1.5.0"}
    ]
    assert releases_from_rows(rows, 0) == [
        {"time": 400, "service": "cart", "version": "2.1.0"},
        {"time": 900, "service": "checkout", "version": "1.5.0"},
    ]


@pytest.mark.django_db
def test_release_columns_need_service_roles(clickhouse_connection):
    logs = make_source("lg", clickhouse_connection, C.LOGS, "otel_logs")
    assert release_columns(logs) == (
        "`ServiceName`",
        "`ResourceAttributes`['service.version']",
    )
    traces = make_source("tr", clickhouse_connection, C.TRACES, "otel_traces")
    assert release_columns(traces)[0] == "`ServiceName`"
    del traces.data["otel"]["roles"]["resource_attrs"]
    assert release_columns(traces) is None
    traces.data.pop("otel")
    assert release_columns(traces) is None


@pytest.mark.django_db
def test_scope_ors_series_filters_only_when_all_have_one(clickhouse_connection):
    logs = make_source("lg", clickhouse_connection, C.LOGS, "otel_logs")
    both = [
        {"agg": "count", "where": "ServiceName = 'a'"},
        {"agg": "count", "where": "ServiceName = 'b'"},
    ]
    assert scope_where(logs, "", both).count("OR") == 1
    assert "OR" not in scope_where(logs, "", both + [{"agg": "count"}])
    formula = both + [{"agg": "formula", "formula": "a/b"}]
    assert scope_where(logs, "", formula).count("OR") == 1


@pytest.mark.django_db
def test_endpoint_binds_filters_and_checks_access(
    root_user, test_user, clickhouse_connection
):
    logs = make_source("lg", clickhouse_connection, C.LOGS, "otel_logs")
    found = [{"time": 1500000, "service": "checkout", "version": "1.5.0"}]
    body = {
        **BODY,
        "query": "ServiceName = $svc",
        "dashboard_query": "SeverityText = 'INFO'",
        "params": {"svc": "checkout"},
    }
    with patch("telescope_otel.releases.fetch_releases", return_value=found) as fetch:
        resp = post(root_user, "lg", body)
    assert resp["result"] and resp["data"] == found
    source, query, raw, series, time_from, time_to = fetch.call_args.args
    assert source.slug == "lg" and raw == "" and series == [{"agg": "count"}]
    assert query == "(ServiceName = 'checkout') and (SeverityText = 'INFO')"
    assert (time_from, time_to) == (1000000, 2000000)

    resp = post(root_user, "lg", {**BODY, "query": "NoSuchColumn = 1"})
    assert resp["validation"]["fields"]["query"]
    with patch("telescope_otel.releases.fetch_releases") as fetch:
        assert post(test_user, "lg", BODY)["errors"] == ["source not found"]
        assert not fetch.called
    rbac_manager.grant_source_role(logs, SourceRole.USER.value, user=test_user)
    with patch("telescope_otel.releases.fetch_releases", return_value=[]):
        assert post(test_user, "lg", BODY)["data"] == []


@pytest.mark.django_db
def test_non_otel_source_has_no_releases(root_user, clickhouse_connection):
    logs = make_source("lg", clickhouse_connection, C.LOGS, "otel_logs")
    logs.data.pop("otel")
    logs.save()
    assert post(root_user, "lg", BODY)["data"] == []
