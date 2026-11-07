"""P3.2 service map on the planted P0.2 data: call graph, counts against a Python oracle,
sampling, the payment error spike, one trace and the FlyQL filter."""

from collections import Counter
from datetime import datetime

import pytest

from telescope_otel.service_map import fetch_service_map
from tests.integration.test_trace_view import connection, make_source  # noqa: F401

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]
# The UI paints a node red from this error rate up (HyperDX's "high" bucket).
RED = 0.05


def ms(iso):
    return int(datetime.fromisoformat(iso[:26] + "+00:00").timestamp() * 1000)


@pytest.fixture
def traces(connection, otel_db):  # noqa: F811
    return make_source("p32-traces", connection, otel_db, "otel_traces", {})


@pytest.fixture
def day(otel_facts):
    return ms(otel_facts["start"]), ms(otel_facts["end"])


def oracle(ch_client, otel_db, where="1"):
    """(client, server) -> (requests, errors), joining parents in Python."""
    rows = ch_client.query(
        "SELECT TraceId, SpanId, ParentSpanId, ServiceName, SpanKind, StatusCode"
        f" FROM {otel_db}.otel_traces WHERE {where}"
    ).result_rows
    clients = {(t, s): svc for t, s, _, svc, kind, _ in rows if kind == "Client"}
    requests, errors = Counter(), Counter()
    for t, _, parent, svc, kind, code in rows:
        client = clients.get((t, parent))
        if kind == "Server" and client and client != svc:
            requests[(client, svc)] += 1
            errors[(client, svc)] += code == "Error"
    return requests, errors


def edges(result):
    return {(e["client"], e["server"]): e for e in result["edges"]}


def test_edges_are_the_call_graph_with_exact_counts(
    traces, day, otel_facts, ch_client, otel_db
):
    result = fetch_service_map(traces, *day)
    got = edges(result)
    assert sorted(got) == sorted(tuple(e) for e in otel_facts["call_graph"])
    requests, errors = oracle(ch_client, otel_db)
    assert {k: e["requests"] for k, e in got.items()} == dict(requests)
    assert {k: e["errors"] for k, e in got.items()} == {k: errors[k] for k in requests}
    nodes = {n["service"]: n for n in result["nodes"]}
    assert sorted(nodes) == sorted(otel_facts["services"])
    servers = dict(
        ch_client.query(
            f"SELECT ServiceName, count() FROM {otel_db}.otel_traces WHERE SpanKind = 'Server'"
            " GROUP BY ServiceName"
        ).result_rows
    )
    assert {s: n["requests"] for s, n in nodes.items()} == servers
    assert nodes["frontend"]["p95"] > nodes["postgres"]["p95"] > 0


def test_sampling_ten_scales_within_15_percent(traces, day):
    exact = edges(fetch_service_map(traces, *day, sampling=1))
    sampled = fetch_service_map(traces, *day, sampling=10)
    assert sampled["sampling"] == 10
    got = edges(sampled)
    assert sorted(got) == sorted(exact)
    for key, edge in exact.items():
        assert abs(got[key]["requests"] - edge["requests"]) <= 0.15 * edge["requests"]


def test_payment_is_red_only_in_the_spike(traces, otel_facts):
    spike = otel_facts["error_spike"]
    lo, hi = ms(spike["from"]), ms(spike["to"])
    during = {n["service"]: n for n in fetch_service_map(traces, lo, hi)["nodes"]}
    assert during["payment"]["error_rate"] >= RED
    assert during["payment"]["error_rate"] == pytest.approx(
        spike["charge_error_ratio"][1], abs=0.05
    )
    before = {
        n["service"]: n
        for n in fetch_service_map(traces, lo - 6 * 3600_000, lo)["nodes"]
    }
    assert 0 < before["payment"]["error_rate"] < RED


def test_one_trace(traces, otel_facts, ch_client, otel_db):
    big = otel_facts["big_trace"]
    result = fetch_service_map(
        traces, ms(big["start"]), ms(big["end"]), sampling=10, trace_id=big["trace_id"]
    )
    assert result["sampling"] == 1
    requests, _ = oracle(ch_client, otel_db, f"TraceId = '{big['trace_id']}'")
    assert {k: e["requests"] for k, e in edges(result).items()} == dict(requests)
    assert {n["service"] for n in result["nodes"]} == set(big["services"])


def test_flyql_filter_applies_to_both_sides(traces, day, ch_client, otel_db):
    query = "ServiceName in ['checkout', 'payment']"
    got = edges(fetch_service_map(traces, *day, query=query))
    requests, _ = oracle(ch_client, otel_db, "ServiceName IN ('checkout', 'payment')")
    assert sorted(got) == [("checkout", "payment")]
    assert got[("checkout", "payment")]["requests"] == requests[("checkout", "payment")]
