import pytest

from telescope_otel.detect import detect
from telescope_otel.roles import ROLES, validate_otel
from tests.otel import columns as C


def test_logs_fill_every_role():
    result = detect("otel_logs", C.LOGS)
    otel = result["otel"]
    assert otel["signal"] == "logs"
    assert set(otel["roles"]) == set(ROLES["logs"])
    assert otel["roles"]["attrs"] == "LogAttributes"
    assert result["settings"] == {
        "time_column": "Timestamp",
        "date_column": "",
        "severity_column": "SeverityText",
        "default_chosen_columns": ["Timestamp", "ServiceName", "SeverityText", "Body"],
    }
    assert validate_otel(otel, dict(C.LOGS)) == []


def test_traces_fill_every_role_including_nested():
    result = detect("otel_traces", C.TRACES)
    otel = result["otel"]
    assert otel["signal"] == "traces"
    assert set(otel["roles"]) == set(ROLES["traces"])
    assert otel["roles"]["events"] == "Events"
    assert otel["roles"]["links"] == "Links"
    assert otel["roles"]["duration_precision"] == 9
    assert result["settings"]["severity_column"] == "StatusCode"
    assert validate_otel(otel, dict(C.TRACES)) == []


def test_traces_without_nested_columns_leave_events_unset():
    cols = [c for c in C.TRACES if "." not in c[0]]
    roles = detect("spans", cols)["otel"]["roles"]
    assert "events" not in roles and "links" not in roles


def test_gauge_fills_every_role_and_sibling_tables():
    result = detect("otel_metrics_gauge", C.GAUGE, C.METRIC_TABLES + ["other"])
    otel = result["otel"]
    assert otel["signal"] == "metrics"
    assert set(otel["roles"]) == set(ROLES["metrics"])
    assert otel["metric_tables"] == {
        k: f"otel_metrics_{k}"
        for k in ["gauge", "sum", "histogram", "exponential_histogram", "summary"]
    }
    assert result["settings"]["time_column"] == "TimeUnix"
    assert result["settings"]["default_chosen_columns"] == [
        "TimeUnix",
        "ServiceName",
        "MetricName",
        "Value",
    ]
    assert validate_otel(otel, dict(C.GAUGE)) == []


@pytest.mark.parametrize(
    "table,cols,kind",
    [
        ("otel_metrics_sum", C.SUM, "sum"),
        ("otel_metrics_histogram", C.HISTOGRAM, "histogram"),
        (
            "otel_metrics_exponential_histogram",
            C.EXP_HISTOGRAM,
            "exponential_histogram",
        ),
        ("otel_metrics_summary", C.SUMMARY, "summary"),
    ],
)
def test_metric_kind_from_columns(table, cols, kind):
    otel = detect(table, cols, C.METRIC_TABLES[:2] + [table])["otel"]
    assert otel["metric_tables"][kind] == table


def test_metric_table_with_other_name_maps_only_itself():
    assert detect("my_gauges", C.GAUGE, ["my_gauges"])["otel"]["metric_tables"] == {
        "gauge": "my_gauges"
    }


def test_string_severity_number_is_not_the_otel_number():
    cols = [(n, "String" if n == "SeverityNumber" else t) for n, t in C.LOGS]
    assert "severity_number" not in detect("logs", cols)["otel"]["roles"]


def test_date_column_only_when_a_date_typed_column_exists():
    assert (
        detect("l", C.LOGS + [("TimestampTime", "DateTime")])["settings"]["date_column"]
        == ""
    )
    assert (
        detect("l", C.LOGS + [("EventDate", "Date")])["settings"]["date_column"]
        == "EventDate"
    )


def test_non_otel_table_yields_nothing():
    cols = [("ts", "DateTime64(3)"), ("message", "String"), ("level", "String")]
    assert detect("app", cols) is None
    # One missing marker column is enough to reject.
    assert detect("otel_logs", [c for c in C.LOGS if c[0] != "LogAttributes"]) is None
