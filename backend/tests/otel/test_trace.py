"""P2.3 tree build, critical path, error rules and the trace endpoints without ClickHouse."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from telescope.models import Source
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope_otel.detect import detect
from telescope_otel.trace import (
    TraceError,
    build_tree,
    fetch_trace,
    is_error_status,
    lookup_window,
)
from tests.otel import columns as C

rbac_manager = RBACManager()


def span(i, parent, offset, duration):
    return {
        "_key": ("span", i, offset),
        "id": i,
        "parent_id": parent,
        "offset_ns": offset,
        "duration_ns": duration,
        "synthetic": False,
    }


def shape(ordered):
    return [
        (
            s["id"],
            s["depth"],
            None if s["parent"] is None else ordered[s["parent"]]["id"],
        )
        for s in ordered
    ]


def test_tree_orders_children_by_start():
    ordered = build_tree(
        [
            span("a", "", 0, 100),
            span("c", "a", 50, 10),
            span("b", "a", 10, 30),
            span("d", "b", 20, 5),
        ]
    )
    assert shape(ordered) == [
        ("a", 0, None),
        ("b", 1, "a"),
        ("d", 2, "b"),
        ("c", 1, "a"),
    ]
    assert [s["children"] for s in ordered] == [2, 1, 0, 0]


def test_missing_parent_gets_one_synthetic_root():
    ordered = build_tree(
        [span("a", "", 0, 100), span("x", "gone", 120, 10), span("y", "gone", 110, 40)]
    )
    assert shape(ordered) == [
        ("a", 0, None),
        ("gone", 0, None),
        ("y", 1, "gone"),
        ("x", 1, "gone"),
    ]
    root = ordered[1]
    assert root["synthetic"] and root["name"] == "missing span"
    assert (root["offset_ns"], root["duration_ns"]) == (110, 40)


def test_zero_parent_and_cycles_still_render():
    ordered = build_tree(
        [
            span("a", "0000000000000000", 0, 10),
            span("p", "q", 1, 1),
            span("q", "p", 2, 1),
        ]
    )
    assert {s["id"] for s in ordered} == {"a", "p", "q"}
    assert shape(ordered)[0] == ("a", 0, None)
    assert shape(ordered)[1:] == [("p", 0, None), ("q", 1, "p")]


def test_duplicate_span_ids_keep_both_rows():
    ordered = build_tree([span(0, "", 0, 10), span("b", 0, 1, 2), span("b", 0, 3, 2)])
    assert len(ordered) == 3 and [s["depth"] for s in ordered] == [0, 1, 1]


def test_critical_path_follows_the_last_finishing_child():
    # a: 0..100; b: 10..40, c: 30..90 (overlaps b), d: 95..120 (ends after its parent)
    ordered = build_tree(
        [
            span("a", "", 0, 100),
            span("b", "a", 10, 30),
            span("c", "a", 30, 60),
            span("d", "a", 95, 25),
        ]
    )
    crit = {s["id"]: s["critical"] for s in ordered}
    assert crit == {
        "a": [[0, 10], [90, 95]],
        "b": [[10, 30]],
        "c": [[30, 90]],
        "d": [[95, 100]],
    }


def test_error_status_rules():
    assert is_error_status("Error") and is_error_status("ERROR")
    assert is_error_status("STATUS_CODE_ERROR")
    assert (
        not is_error_status("Unset")
        and not is_error_status("")
        and not is_error_status(None)
    )
    assert not is_error_status("STATUS_CODE_OK")


def test_lookup_window():
    assert lookup_window(10_000_000) == (10_000_000 - 3600_000, 10_000_000 + 3600_000)
    assert lookup_window(None, now_ms=100_000_000) == (
        100_000_000 - 86400_000,
        100_000_000,
    )


def make_source(slug, conn, cols, table, links=None):
    otel = detect(table, cols)["otel"]
    otel["links"] = links or {}
    return Source.create(
        kind="clickhouse",
        data={
            "slug": slug,
            "name": slug,
            "description": "",
            "time_column": "Timestamp",
            "date_column": "",
            "severity_column": "",
            "columns": C.source_columns(cols),
            "default_chosen_columns": ["Timestamp"],
            "conn": conn,
            "data": {"database": "otel", "table": table, "otel": otel},
        },
    )


def post(user, path, body):
    client = APIClient()
    client.force_login(user)
    return client.post(f"/ui/v1/otel/{path}", body, format="json").json()


@pytest.mark.django_db
def test_trace_rejects_bad_ids_and_wrong_signal(root_user, clickhouse_connection):
    make_source("tr", clickhouse_connection, C.TRACES, "otel_traces")
    make_source("lg", clickhouse_connection, C.LOGS, "otel_logs")
    resp = post(root_user, "tr/trace", {"trace_id": "x' or 1=1"})
    assert resp["validation"]["fields"]["trace_id"]
    resp = post(root_user, "lg/trace", {"trace_id": "abc"})
    assert resp["errors"] == ["source lg is not an OTel traces source"]
    resp = post(root_user, "tr/traceLogs", {"trace_id": "abc"})
    assert resp["errors"] == ["no logs source is linked to this traces source"]
    assert post(root_user, "nope/trace", {"trace_id": "abc"})["errors"] == [
        "source not found"
    ]


@pytest.mark.django_db
def test_trace_logs_uses_the_linked_source(root_user, test_user, clickhouse_connection):
    traces = make_source(
        "tr", clickhouse_connection, C.TRACES, "otel_traces", {"logs": "lg"}
    )
    logs = make_source("lg", clickhouse_connection, C.LOGS, "otel_logs")
    result = {"logs": [], "truncated": False}
    with patch(
        "telescope_otel.trace_views.fetch_trace_logs", return_value=result
    ) as fetch:
        resp = post(root_user, "tr/traceLogs", {"trace_id": "abc", "around_ms": 5})
    assert resp["data"] == result
    assert fetch.call_args.args[0].slug == "lg"
    assert fetch.call_args.args[1:] == ("abc", 5)

    rbac_manager.grant_source_role(traces, SourceRole.USER.value, user=test_user)
    with patch("telescope_otel.trace_views.fetch_trace_logs") as fetch:
        resp = post(test_user, "tr/traceLogs", {"trace_id": "abc"})
    assert resp["errors"] == ["no access to logs source lg"] and not fetch.called
    rbac_manager.grant_source_role(logs, SourceRole.VIEWER.value, user=test_user)
    with patch("telescope_otel.trace_views.fetch_trace_logs", return_value=result):
        assert post(test_user, "tr/traceLogs", {"trace_id": "abc"})["errors"] == [
            "no access to logs source lg"
        ]


@pytest.mark.django_db
def test_duration_precision_scales_to_ns(clickhouse_connection):
    source = make_source("tr", clickhouse_connection, C.TRACES, "otel_traces")
    source.data["otel"]["roles"]["duration_precision"] = 3
    row = [
        "s",
        "",
        "n",
        "Server",
        "svc",
        1_000,
        7,
        "Error",
        "",
        {},
        {},
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    ]
    with patch("telescope_otel.trace._select_trace", return_value=([row], False)):
        trace = fetch_trace(source, "abc", around_ms=0)
    assert trace["duration_ns"] == 7_000_000 and trace["error_count"] == 1
    source.data["otel"]["roles"].pop("span_id")
    with pytest.raises(TraceError, match="has no span_id role"):
        fetch_trace(source, "abc", around_ms=0)
