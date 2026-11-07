import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.conf import settings

from telescope.models import Connection, Source
from tests.fixtures import *  # noqa: F401,F403
from tests.integration.conftest import (  # noqa: F401
    ch_client,
    ch_settings,
    ch_settings_dict,
    otel_db,
    otel_facts,
)

from telescope_alerts.channels import net


def pytest_collection_modifyitems(config, items):
    if ch_settings():
        return
    skip = pytest.mark.skip(
        reason="TELESCOPE_TEST_CH_HOST / TELESCOPE_TEST_CH_PORT not set"
    )
    for item in items:
        if "clickhouse" in item.keywords and "telescope_alerts" in str(item.fspath):
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    monkeypatch.setattr(net, "BACKOFF_SECONDS", 0)


@pytest.fixture
def alerts_config(monkeypatch):
    config = dict(settings.CONFIG.get("alerts") or {})
    config["allow_private_webhook_targets"] = True
    config["public_url"] = "http://telescope.example"
    monkeypatch.setitem(settings.CONFIG, "alerts", config)
    return config


class Receiver:
    """An in-process HTTP endpoint recording every POST body."""

    def __init__(self, status=200, location=None):
        self.requests = []
        self.status = status
        self.location = location
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode()
                receiver.requests.append(
                    {"path": self.path, "headers": dict(self.headers), "body": body}
                )
                status = receiver.status
                if callable(status):
                    status = status(len(receiver.requests))
                self.send_response(status)
                if receiver.location:
                    self.send_header("Location", receiver.location)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/hook"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def json(self):
        return [json.loads(r["body"]) for r in self.requests]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def receiver():
    r = Receiver()
    yield r
    r.close()


@pytest.fixture
def make_receiver():
    made = []

    def make(**kw):
        made.append(Receiver(**kw))
        return made[-1]

    yield make
    for r in made:
        r.close()


@pytest.fixture
def starrocks_source(clickhouse_connection):
    from tests.data import get_clickhouse_source_data

    data = get_clickhouse_source_data("starrocks", kind="starrocks")
    del data["kind"]
    del data["connection"]
    data["conn"] = Connection.objects.create(
        kind="starrocks",
        name="StarRocks",
        description="",
        data=clickhouse_connection.data,
    )
    return Source.create(kind="starrocks", data=data)


def otel_source(ch_client, ch_settings_dict, db, table, slug, severity=""):
    rows = ch_client.query(
        "SELECT name, type FROM system.columns WHERE database = %(db)s AND table = %(t)s ORDER BY position",
        parameters={"db": db, "t": table},
    ).result_rows
    columns = {
        name: {
            "display_name": "",
            "type": type_,
            "autocomplete": False,
            "suggest": False,
            "jsonstring": False,
            "group_by": True,
            "values": [],
        }
        for name, type_ in rows
    }
    conn = Connection.objects.create(
        kind="clickhouse",
        name=f"otel {slug}",
        description="",
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
            "slug": slug,
            "name": slug,
            "description": "",
            "time_column": "Timestamp",
            "date_column": "",
            "uniq_column": "",
            "severity_column": severity,
            "columns": columns,
            "default_chosen_columns": ["Timestamp"],
            "data": {"database": db, "table": table},
            "conn": conn,
        },
    )


@pytest.fixture
def otel_logs_source(ch_client, ch_settings_dict, otel_db):
    return otel_source(
        ch_client, ch_settings_dict, otel_db, "otel_logs", "otel-logs", "SeverityText"
    )


@pytest.fixture
def otel_traces_source(ch_client, ch_settings_dict, otel_db):
    return otel_source(
        ch_client, ch_settings_dict, otel_db, "otel_traces", "otel-traces"
    )
