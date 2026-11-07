"""P1.5 acceptance: dashboard variables bound through FlyQL, against the P0.2 otel_logs data."""

from datetime import datetime

import pytest
from rest_framework.test import APIClient

from telescope.models import Connection, Source

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]


def column(type):
    return {
        "display_name": "",
        "type": type,
        "autocomplete": True,
        "suggest": True,
        "jsonstring": False,
        "group_by": True,
        "values": [],
    }


@pytest.fixture
def otel_logs(ch_settings_dict, otel_db):
    conn = Connection.objects.create(
        kind="clickhouse",
        name="otel",
        data={
            "host": ch_settings_dict["host"],
            "port": ch_settings_dict["port"],
            "user": ch_settings_dict["username"],
            "password": ch_settings_dict["password"],
            "ssl": False,
            "verify": False,
        },
    )
    return Source.create(
        kind="clickhouse",
        data={
            "slug": "otel-logs",
            "name": "otel logs",
            "description": "",
            "time_column": "Timestamp",
            "date_column": "",
            "uniq_column": "",
            "severity_column": "SeverityText",
            "default_chosen_columns": ["Timestamp", "ServiceName"],
            "columns": {
                "Timestamp": column("DateTime64(9)"),
                "ServiceName": column("LowCardinality(String)"),
                "SeverityText": column("LowCardinality(String)"),
            },
            "conn": conn,
            "data": {"database": otel_db, "table": "otel_logs", "settings": ""},
        },
    )


@pytest.fixture
def window(otel_facts):
    start = datetime.fromisoformat(otel_facts["start"][:26] + "+00:00")
    t0 = int(start.timestamp() * 1000)
    return t0, t0 + 24 * 3600 * 1000


def chart(root_user, source, window, **changes):
    body = {
        "from": str(window[0]),
        "to": str(window[1]),
        "query": "ServiceName = $service",
        "dashboard_query": "",
        "raw_query": "",
        "context_columns": {},
        "display": "table",
        "series": [{"agg": "count"}],
        "group_by": "ServiceName",
        "granularity": "auto",
        "limit": 50,
    }
    body.update(changes)
    client = APIClient()
    client.force_login(root_user)
    return client.post(
        f"/ui/v1/sources/{source.slug}/chartData", body, format="json"
    ).json()


def truth(ch_client, otel_db, window, where, parameters):
    sql = (
        f"SELECT ServiceName, count() FROM `{otel_db}`.otel_logs"
        " WHERE Timestamp BETWEEN fromUnixTimestamp64Milli(%(f)s) AND fromUnixTimestamp64Milli(%(t)s)"
        f" AND {where} GROUP BY ServiceName ORDER BY count() DESC, ServiceName"
    )
    parameters = {"f": window[0], "t": window[1], **parameters}
    return [
        {"group": g, "values": [n]}
        for g, n in ch_client.query(sql, parameters=parameters).result_rows
    ]


def test_single_value_gives_exactly_that_series(
    root_user, otel_logs, window, ch_client, otel_db
):
    result = chart(root_user, otel_logs, window, params={"service": "payment"})
    assert result["result"] is True, result
    rows = result["data"]["rows"]
    assert [r["group"] for r in rows] == ["payment"]
    assert rows == truth(
        ch_client, otel_db, window, "ServiceName = %(s)s", {"s": "payment"}
    )


def test_timeseries_with_one_value_has_one_series(root_user, otel_logs, window):
    result = chart(
        root_user, otel_logs, window, display="line", params={"service": "payment"}
    )
    assert [s["name"] for s in result["data"]["series"]] == ["payment"]


def test_multi_value_matches_in(root_user, otel_logs, window, ch_client, otel_db):
    values = ["payment", "cart"]
    result = chart(root_user, otel_logs, window, params={"service": values})
    assert result["data"]["rows"] == truth(
        ch_client, otel_db, window, "ServiceName IN %(s)s", {"s": values}
    )


def test_injection_returns_no_rows(root_user, otel_logs, window):
    result = chart(root_user, otel_logs, window, params={"service": "x' or 1=1"})
    assert result["result"] is True, result
    assert result["data"]["rows"] == []
    number = chart(
        root_user,
        otel_logs,
        window,
        display="number",
        group_by="",
        params={"service": "x' or 1=1"},
    )
    assert number["data"]["value"] == 0


def test_missing_required_value_is_not_queried(root_user, otel_logs, window):
    result = chart(root_user, otel_logs, window, params={})
    assert result["validation"]["fields"] == {
        "params": {"service": ["no value for $service"]}
    }
    assert "kind" not in (result["data"] or {})
