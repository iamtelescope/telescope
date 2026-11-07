"""P3.2 service map SQL, row folding and the endpoint, without ClickHouse."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope_otel.service_map import fetch_service_map, service_map_sql
from telescope_otel.trace import TraceError
from tests.otel import columns as C
from tests.otel.test_trace import make_source, post

rbac_manager = RBACManager()


@contextmanager
def fake_rows(rows):
    client = MagicMock()
    client.query.return_value.result_rows = rows
    connect = MagicMock()
    connect.return_value.__enter__.return_value.client = client
    with patch("telescope_otel.service_map.ClickhouseConnect", connect):
        yield client


@pytest.fixture
def traces(clickhouse_connection):
    return make_source("tr", clickhouse_connection, C.TRACES, "otel_traces")


@pytest.mark.django_db
def test_sql_joins_server_to_client_spans_with_sampling(traces):
    roles = traces.data["otel"]["roles"]
    roles.setdefault("timestamp", "Timestamp")
    sql = service_map_sql(traces, roles, "ServiceName = 'cart'", 10, None)
    assert "cityHash64(`TraceId`) % 10 = 0" in sql
    assert "S.__sm_trace = C.__sm_trace AND S.__sm_parent = C.__sm_span" in sql
    assert "GROUPING SETS ((S.__sm_service, C.__sm_service), (S.__sm_service))" in sql
    assert sql.count("(ServiceName = 'cart')") == 2
    assert "{trace_id:String}" not in sql
    assert "`TraceId` = {trace_id:String}" in service_map_sql(
        traces, roles, "", 1, "abc"
    )


@pytest.mark.django_db
def test_rows_fold_into_nodes_and_edges(traces):
    rows = [
        ("checkout", "", 1, 10, 2, [1e6, 2e6, 3e6]),
        ("checkout", "frontend", 0, 9, 2, [1e6, 2e6, 3e6]),
        # A caller without client spans: in the node total, but no edge.
        ("checkout", "", 0, 1, 0, [1e6, 1e6, 1e6]),
    ]
    with fake_rows(rows) as client:
        result = fetch_service_map(traces, 0, 1000, "", 5)
    assert client.query.call_args.kwargs["parameters"] == {
        "from": 0,
        "to": 1000,
        "trace_id": "",
    }
    assert result["sampling"] == 5
    assert result["nodes"] == [
        {
            "service": "checkout",
            "requests": 50,
            "errors": 10,
            "error_rate": 0.2,
            "p50": 1.0,
            "p95": 2.0,
            "p99": 3.0,
        },
        {
            "service": "frontend",
            "requests": 0,
            "errors": 0,
            "error_rate": 0.0,
            "p50": None,
            "p95": None,
            "p99": None,
        },
    ]
    assert [(e["client"], e["server"], e["requests"]) for e in result["edges"]] == [
        ("frontend", "checkout", 45)
    ]


@pytest.mark.django_db
def test_trace_is_never_sampled_and_precision_scales(traces):
    traces.data["otel"]["roles"]["duration_precision"] = 3
    with fake_rows([("a", "", 1, 1, 0, [7, 7, 7])]) as client:
        result = fetch_service_map(traces, 0, 1, "", 50, "abc")
    assert result["sampling"] == 1 and result["nodes"][0]["p95"] == 7
    assert "% 1 = 0" in client.query.call_args.args[0]
    traces.data["otel"]["roles"].pop("duration")
    with fake_rows([("a", "", 1, 1, 0, [0, 0, 0])]):
        assert fetch_service_map(traces, 0, 1)["nodes"][0]["p95"] is None


@pytest.mark.django_db
def test_bad_query_and_missing_roles(traces):
    with pytest.raises(TraceError):
        fetch_service_map(traces, 0, 1, "ServiceName = ", 1)
    traces.data["otel"]["roles"].pop("span_kind")
    with pytest.raises(TraceError, match="has no span_kind role"):
        fetch_service_map(traces, 0, 1, "", 1)


@pytest.mark.django_db
def test_endpoint_validates_and_checks_access(root_user, test_user, traces):
    body = {"from": 0, "to": 10, "sampling": 10}
    assert post(root_user, "tr/serviceMap", {**body, "sampling": 101})["validation"][
        "fields"
    ]["sampling"]
    assert post(root_user, "tr/serviceMap", {**body, "from": 20})["validation"][
        "non_field"
    ]
    assert post(root_user, "tr/serviceMap", {**body, "trace_id": "x' or 1"})[
        "validation"
    ]["fields"]["trace_id"]
    assert post(test_user, "tr/serviceMap", body)["errors"] == ["source not found"]

    rbac_manager.grant_source_role(traces, SourceRole.USER.value, user=test_user)
    result = {"nodes": [], "edges": []}
    with patch(
        "telescope_otel.service_map_views.fetch_service_map", return_value=result
    ) as fetch:
        resp = post(test_user, "tr/serviceMap", {**body, "query": "a = 1"})
    assert resp["result"] and resp["data"] == result
    assert fetch.call_args.args[1:] == (0, 10, "a = 1", 10, None)


@pytest.mark.django_db
def test_endpoint_refuses_logs_sources(root_user, clickhouse_connection):
    make_source("lg", clickhouse_connection, C.LOGS, "otel_logs")
    resp = post(root_user, "lg/serviceMap", {"from": 0, "to": 1})
    assert resp["errors"] == ["source lg is not an OTel traces source"]
