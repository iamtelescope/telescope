"""P5.2 against the P0.2 otel_logs data: search and patterns tiles obey variables, the dashboard
filter and the time range, page without gaps, and only answer users who may use the source.
"""

from datetime import datetime

import pytest
from rest_framework.test import APIClient

from telescope.models import Connection, Source
from telescope.utils import get_telescope_column

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]


def ms(iso):
    return int(datetime.fromisoformat(iso[:26] + "+00:00").timestamp() * 1000)


@pytest.fixture
def otel_logs(ch_client, ch_settings_dict, otel_db):
    rows = ch_client.query(
        "SELECT name, type FROM system.columns WHERE database = %(d)s AND table = 'otel_logs'",
        parameters={"d": otel_db},
    ).result_rows
    columns = {}
    for name, type_ in rows:
        column = get_telescope_column(name, type_)
        column.pop("name")
        column["values"] = []
        columns[name] = column
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
            "default_chosen_columns": ["ServiceName", "Body"],
            "columns": columns,
            "conn": conn,
            "data": {"database": otel_db, "table": "otel_logs", "settings": ""},
        },
    )


@pytest.fixture
def window(otel_facts):
    return ms(otel_facts["start"]), ms(otel_facts["end"])


def post(user, source, kind, body):
    client = APIClient()
    client.force_login(user)
    url = f"/ui/v1/sources/{source.slug}/{kind}Tile?dashboard=d&tile=t"
    return client.post(url, body, format="json").json()


def search_body(window, **changes):
    body = {
        "from": str(window[0]),
        "to": str(window[1]),
        "query": "ServiceName = $service",
        "dashboard_query": "SeverityText = 'ERROR'",
        "params": {"service": "payment"},
        "columns": "ServiceName, SeverityText, Body",
        "limit": 50,
    }
    body.update(changes)
    return body


def identity(row):
    d = row["data"]
    return (row["time"]["unixtime"], int(row["time"]["microseconds"]), d["Body"])


def test_search_tile_pages_match_sql_truth(
    root_user, otel_logs, window, ch_client, otel_db
):
    rows, before, resolved = [], None, {}
    for _ in range(3):
        result = post(
            root_user,
            otel_logs,
            "search",
            search_body(window, before=before, **resolved),
        )
        assert result["result"] is True, result
        data = result["data"]
        rows += data["rows"]
        before = data["cursor"]
        resolved = {"from": data["time_from"], "to": data["time_to"]}
        assert before is not None
    truth = ch_client.query(
        f"SELECT toUnixTimestamp64Milli(Timestamp), modulo(toUnixTimestamp64Micro(Timestamp), 1000000), Body"
        f" FROM `{otel_db}`.otel_logs WHERE Timestamp BETWEEN fromUnixTimestamp64Milli(%(f)s)"
        " AND fromUnixTimestamp64Milli(%(t)s) AND ServiceName = 'payment' AND SeverityText = 'ERROR'"
        " ORDER BY Timestamp DESC LIMIT 150",
        parameters={"f": window[0], "t": window[1]},
    ).result_rows
    assert len(rows) == 150
    assert [r[0] for r in map(identity, rows)] == [t[0] for t in truth]
    assert sorted(map(identity, rows)) == sorted(tuple(t) for t in truth)
    assert {(r["data"]["ServiceName"], r["data"]["SeverityText"]) for r in rows} == {
        ("payment", "ERROR")
    }


def test_search_tile_obeys_time_range(root_user, otel_logs, otel_facts):
    fact = otel_facts["connection_refused"]
    body = search_body(
        (ms(fact["from"]), ms(fact["to"])),
        query="ServiceName = $service and Body ~ '(?i)connection refused'",
        dashboard_query="",
        params={"service": fact["service"]},
        limit=500,
    )
    result = post(root_user, otel_logs, "search", body)
    assert result["validation"]["result"] is not False, result["validation"]
    rows = result["data"]["rows"]
    assert len(rows) == fact["rows"] == 25
    assert all(
        ms(fact["from"]) <= r["time"]["unixtime"] <= ms(fact["to"]) for r in rows
    )


def test_search_tile_injection_is_a_value(root_user, otel_logs, window):
    result = post(
        root_user,
        otel_logs,
        "search",
        search_body(window, params={"service": "x' or 1=1 or ServiceName != '"}),
    )
    assert result["result"] is True, result
    assert result["data"]["rows"] == []


def test_patterns_tile_finds_the_cart_family_through_a_variable(
    root_user, otel_logs, window, otel_facts
):
    truth = {t["template"]: t["rows"] for t in otel_facts["cart_patterns"]["templates"]}
    body = {
        "from": str(window[0]),
        "to": str(window[1]),
        "query": "ServiceName = $service",
        "dashboard_query": "",
        "params": {"service": "cart"},
        "column": "Body",
        "sample": 100_000,
    }
    result = post(root_user, otel_logs, "patterns", body)
    assert result["result"] is True, result
    data = result["data"]
    assert data["kind"] == "patterns" and data["total"] == sum(truth.values())
    found = {p["pattern"]: p["est_total"] for p in data["patterns"]}
    assert found == truth


def test_tiles_need_source_use(test_user, otel_logs, window):
    for kind, body in [("search", search_body(window)), ("patterns", {})]:
        result = post(test_user, otel_logs, kind, body)
        assert result["data"] == {"code": "no_access"}
