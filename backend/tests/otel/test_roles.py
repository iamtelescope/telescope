from telescope_otel.roles import validate_otel

COLS = {"Timestamp": {}, "TraceId": {}, "Events.Name": {}, "Events.Timestamp": {}}


def test_valid_block():
    otel = {
        "signal": "traces",
        "roles": {"timestamp": "Timestamp", "trace_id": "TraceId", "events": "Events"},
        "links": {"logs": "app-logs"},
    }
    assert validate_otel(otel, COLS, lambda slug: True) == []


def test_missing_column_is_rejected():
    otel = {"signal": "logs", "roles": {"trace_id": "trace"}}
    assert validate_otel(otel, COLS) == ["column trace not found"]


def test_nested_prefix_must_match_whole_segment():
    otel = {"signal": "traces", "roles": {"events": "Event"}}
    assert validate_otel(otel, COLS) == ["column Event not found"]


def test_empty_roles_are_allowed():
    assert validate_otel({"signal": "logs", "roles": {"body": ""}}, COLS) == []


def test_columns_none_skips_column_checks():
    assert validate_otel({"signal": "logs", "roles": {"body": "x"}}, None) == []


def test_bad_shapes():
    assert validate_otel([], COLS) == ["otel must be an object"]
    assert validate_otel({"signal": "events"}, COLS) == [
        "signal must be one of logs, traces, metrics"
    ]
    assert validate_otel(
        {"signal": "logs", "roles": {"span_kind": "Timestamp"}}, COLS
    ) == ["unknown logs role span_kind"]
    assert validate_otel({"signal": "logs", "roles": {"body": 5}}, COLS) == [
        "role body must be a column name"
    ]
    assert validate_otel({"signal": "logs", "extra": 1}, COLS) == [
        "unknown otel keys: extra"
    ]


def test_duration_precision():
    ok = {"signal": "traces", "roles": {"duration_precision": 6}}
    assert validate_otel(ok, COLS) == []
    bad = {"signal": "traces", "roles": {"duration_precision": 7}}
    assert validate_otel(bad, COLS) == ["duration_precision must be one of 0, 3, 6, 9"]


def test_links():
    otel = {
        "signal": "logs",
        "links": {"traces": "missing", "metrics": "bad slug!", "x": "a"},
    }
    assert validate_otel(otel, COLS, lambda slug: False) == [
        "source missing not found",
        "link metrics must be a source slug",
        "unknown link x",
    ]


def test_metric_tables():
    ok = {
        "signal": "metrics",
        "metric_tables": {"gauge": "otel_metrics_gauge", "sum": ""},
    }
    assert validate_otel(ok, COLS) == []
    assert validate_otel({"signal": "logs", "metric_tables": {}}, COLS) == [
        "metric_tables is only allowed for metrics"
    ]
    bad = {"signal": "metrics", "metric_tables": {"gauge": "a; DROP", "bucket": "t"}}
    assert validate_otel(bad, COLS) == [
        "metric table gauge must be a table name",
        "unknown metric table kind bucket",
    ]
