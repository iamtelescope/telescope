"""P1.3: quick filters and presets that ui/src/utils/context.js derives from a row."""

from types import SimpleNamespace

from tests.context.contextjs import context_for


def col(type_="String", suggest=True):
    return {"type": type_, "suggest": suggest}


SOURCE = SimpleNamespace(
    kind="clickhouse",
    time_column="ts",
    date_column="d",
    columns={
        "ts": col("DateTime64(3)"),
        "d": col("Date"),
        "service": col(suggest=False),
        "host": col(),
        "message": col(),
        "status": col("UInt16"),
        "trace_id": col(suggest=False),
        "ResourceAttributes": col("Map(String, String)", suggest=False),
    },
)
ROW = {
    "time": {"unixtime": 1767268833082, "microseconds": "082000"},
    "data": {
        "ts": "2026-01-01 12:00:33.082",
        "d": "2026-01-01",
        "service": "pay'ments",
        "host": "a\\b",
        "message": "x" * 201,
        "status": 503,
        "trace_id": "",
        "ResourceAttributes": {
            "k8s.pod.name": "pay-1",
            "k8s.namespace.name": "shop",
            "other": "skip",
        },
    },
}


def test_chips_come_from_the_row_and_are_escaped(tmp_path):
    ctx = context_for(tmp_path, SOURCE, ROW, "all", 100)
    assert [(f["id"], f["expr"]) for f in ctx["filters"]] == [
        ("col:service", "service = 'pay\\'ments'"),
        ("attr:k8s.namespace.name", "ResourceAttributes.'k8s.namespace.name' = 'shop'"),
        ("attr:k8s.pod.name", "ResourceAttributes.'k8s.pod.name' = 'pay-1'"),
        ("col:host", "host = 'a\\\\b'"),
        ("col:status", "status = 503"),
    ]
    # an empty trace id offers no "same trace"; the 201-char message is not a chip
    assert ctx["presets"] == ["all", "service", "pod", "custom"]
    assert ctx["query"] == ""
    assert ctx["window"] == {"from": 1767268832982, "to": 1767268833182}


def test_presets_build_the_query(tmp_path):
    assert (
        context_for(tmp_path, SOURCE, ROW, "service", 1000)["query"]
        == "service = 'pay\\'ments'"
    )
    assert context_for(tmp_path, SOURCE, ROW, "pod", 1000)["query"] == (
        "(ResourceAttributes.'k8s.namespace.name' = 'shop') and (ResourceAttributes.'k8s.pod.name' = 'pay-1')"
    )


def test_otel_roles_name_the_service_column(tmp_path):
    source = SimpleNamespace(
        **{**vars(SOURCE), "columns": {**SOURCE.columns, "svc": col()}}
    )
    source.data = {"otel": {"roles": {"service": "svc"}}}
    row = {**ROW, "data": {**ROW["data"], "svc": "cart"}}
    assert (
        context_for(tmp_path, source, row, "service", 1000)["query"] == "svc = 'cart'"
    )
