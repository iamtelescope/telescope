"""P1.6 acceptance on the P0.2 tables: detection fills every role for all three DDL variants."""

import pytest

from telescope_otel.detect import detect
from telescope_otel.roles import ROLES, validate_otel
from telescope_otel.views import read_table

pytestmark = pytest.mark.clickhouse

VARIANTS = ["otel", "otel_exporter", "otel_k8s"]
TABLES = {"otel_logs": "logs", "otel_traces": "traces", "otel_metrics_gauge": "metrics"}


@pytest.fixture(scope="module")
def conn_data(ch_settings_dict):
    s = ch_settings_dict
    return {
        "host": s["host"],
        "port": s["port"],
        "user": s["username"],
        "password": s["password"],
        "ssl": False,
        "verify": False,
    }


@pytest.mark.parametrize("db", VARIANTS)
@pytest.mark.parametrize("table", TABLES)
def test_detection_fills_every_role(ch_client, conn_data, db, table):
    if not ch_client.command(f"EXISTS TABLE `{db}`.`{table}`"):
        pytest.fail(
            f"{db}.{table} missing; load it with dev/otel/generate.py --variants compat,exporter,k8s"
        )
    columns, tables = read_table(conn_data, db, table)
    result = detect(table, columns, tables)
    otel = result["otel"]
    assert otel["signal"] == TABLES[table]
    assert set(otel["roles"]) == set(ROLES[otel["signal"]])
    assert validate_otel(otel, dict(columns)) == []
    if otel["signal"] == "metrics":
        assert set(otel["metric_tables"]) == {
            "gauge",
            "sum",
            "histogram",
            "exponential_histogram",
            "summary",
        }
    names = dict(columns)
    assert names[result["settings"]["time_column"]].startswith("DateTime")
    assert set(result["settings"]["default_chosen_columns"]) <= set(names)


def test_non_otel_table_yields_nothing(ch_client, conn_data):
    ch_client.command("CREATE DATABASE IF NOT EXISTS telescope_test")
    ch_client.command(
        "CREATE TABLE IF NOT EXISTS telescope_test.p16_plain "
        "(ts DateTime64(3), message String, level String, attrs Map(String, String)) "
        "ENGINE = MergeTree ORDER BY ts"
    )
    try:
        columns, tables = read_table(conn_data, "telescope_test", "p16_plain")
        assert columns and detect("p16_plain", columns, tables) is None
    finally:
        ch_client.command("DROP TABLE telescope_test.p16_plain")
