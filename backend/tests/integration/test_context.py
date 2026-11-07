"""P1.3: the CONTEXT tab's requests against the P0.2 OTel logs match direct SQL."""

import pytest
from rest_framework.test import APIClient

from telescope.fetchers import get_fetchers
from telescope.models import Connection, Source
from tests.context.contextjs import context_for

SUGGEST = {"ServiceName", "SeverityText", "TraceId", "SpanId"}


@pytest.fixture
def otel_source(ch_settings_dict, otel_db):
    conn_data = {
        "host": ch_settings_dict["host"],
        "port": ch_settings_dict["port"],
        "user": ch_settings_dict["username"],
        "password": ch_settings_dict["password"],
        "ssl": False,
        "verify": False,
        "ca_cert": "",
        "client_cert": "",
        "client_cert_key": "",
        "server_host_name": "",
        "tls_mode": "",
    }
    conn = Connection.objects.create(
        kind="clickhouse", name="otel", description="", data=conn_data
    )
    schema = get_fetchers()["clickhouse"].get_schema(
        {**conn_data, "database": otel_db, "table": "otel_logs"}
    )
    columns = {}
    for c in schema:
        name = c.pop("name")
        columns[name] = {**c, "suggest": name in SUGGEST}
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
            "columns": columns,
            "default_chosen_columns": ["Timestamp", "ServiceName", "Body"],
            "data": {"database": otel_db, "table": "otel_logs", "settings": ""},
            "conn": conn,
        },
    )


def fetch(user, source, window, query):
    client = APIClient()
    client.force_login(user)
    body = {
        "columns": "Body",
        "from": window["from"],
        "to": window["to"],
        "query": query,
        "limit": 10000,
        "context_columns": {},
    }
    doc = client.post(f"/ui/v1/sources/{source.slug}/data", body, format="json").json()
    assert doc["result"] and doc["validation"]["result"], doc
    return doc["data"]["rows"]


def micros(row):
    return row["time"]["unixtime"] * 1000 + int(row["time"]["microseconds"]) % 1000


def sql_rows(ch_client, db, window, where):
    sql = (
        f"SELECT toUnixTimestamp64Micro(Timestamp), Body FROM `{db}`.otel_logs WHERE {where} "
        f"AND Timestamp BETWEEN fromUnixTimestamp64Milli({window['from']}) "
        f"AND fromUnixTimestamp64Milli({window['to']})"
    )
    return sorted(tuple(r) for r in ch_client.query(sql).result_rows)


@pytest.fixture
def planted(root_user, otel_source, otel_facts):
    f = otel_facts["exception_log"]
    query = f"TraceId = '{f['trace_id']}' and SpanId = '{f['span_id']}' and SeverityText = 'ERROR'"
    rows = fetch(root_user, otel_source, {"from": 0, "to": "now"}, query)
    assert len(rows) == 1
    return rows[0]


@pytest.mark.clickhouse
@pytest.mark.django_db
@pytest.mark.parametrize(
    "preset,range_ms,where",
    [
        ("service", 5000, "ServiceName = 'payment'"),
        ("all", 1000, "true"),
        ("trace", 900000, "TraceId = '{trace}'"),
        (
            "pod",
            60000,
            "ResourceAttributes['k8s.namespace.name'] = '{ns}' AND ResourceAttributes['k8s.pod.name'] = '{pod}'",
        ),
    ],
)
def test_context_matches_sql(
    tmp_path,
    ch_client,
    otel_db,
    root_user,
    otel_source,
    planted,
    preset,
    range_ms,
    where,
):
    res = planted["data"]["ResourceAttributes"]
    where = where.format(
        trace=planted["data"]["TraceId"],
        ns=res["k8s.namespace.name"],
        pod=res["k8s.pod.name"],
    )
    ctx = context_for(tmp_path, otel_source, planted, preset, range_ms)
    assert preset in ctx["presets"]
    rows = fetch(root_user, otel_source, ctx["window"], ctx["query"])
    expected = sql_rows(ch_client, otel_db, ctx["window"], where)
    assert 1 < len(expected) < 10000
    assert sorted((micros(r), r["data"]["Body"]) for r in rows) == expected
    assert planted in rows
