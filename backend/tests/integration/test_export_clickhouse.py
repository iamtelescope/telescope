"""The explorer download against a real ClickHouse: every matching row, streamed, and never a cut file."""

import csv
import io
import json
import re
import socket
import threading
import time
import uuid

import pytest
from django.http import StreamingHttpResponse
from rest_framework.test import APIClient

from telescope.fetchers.clickhouse import Fetcher
from telescope.fetchers.request import DataRequest
from telescope.models import Connection, Source
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole
from telescope.utils import get_telescope_column

pytestmark = [pytest.mark.clickhouse, pytest.mark.django_db]
rbac_manager = RBACManager()
ROWS = 60_000  # past the largest explorer page (25000) and many 8192-row blocks
T0 = 1_790_000_000_000
STEP_MS = 50


@pytest.fixture(scope="module")
def export_db(ch_client):
    db = f"telescope_export_{uuid.uuid4().hex[:8]}"
    ch_client.command(f"CREATE DATABASE {db}")
    ch_client.command(
        f"CREATE TABLE {db}.logs (ts DateTime64(3, 'UTC'), id UInt64, level LowCardinality(String),"
        " body String, attrs Map(String, String)) ENGINE = MergeTree ORDER BY ts"
    )
    ch_client.command(
        f"INSERT INTO {db}.logs SELECT fromUnixTimestamp64Milli(toInt64({T0} + number * {STEP_MS})), number,"
        " ['info', 'warn', 'error'][number % 3 + 1],"
        " concat('request ', toString(number), if(number % 1000 = 0, ' Connection Refused', '')),"
        f" map('k', toString(number % 7)) FROM numbers({ROWS})"
    )
    yield db
    ch_client.command(f"DROP DATABASE {db}")


def make_source(ch_client, ch_settings_dict, db, settings="", table="logs"):
    columns = {}
    for name, type_ in ch_client.query(
        "SELECT name, type FROM system.columns WHERE database = %(d)s AND table = %(t)s",
        parameters={"d": db, "t": table},
    ).result_rows:
        column = get_telescope_column(name, type_)
        column.pop("name")
        column["values"] = []
        columns[name] = column
    conn = Connection.objects.create(
        kind="clickhouse",
        name=f"export-{uuid.uuid4().hex[:6]}",
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
            "slug": f"export-{uuid.uuid4().hex[:6]}",
            "name": "export",
            "description": "",
            "time_column": "ts",
            "date_column": "",
            "uniq_column": "",
            "severity_column": "level",
            "columns": columns,
            "default_chosen_columns": list(columns),
            "conn": conn,
            "data": {"database": db, "table": table, "settings": settings},
        },
    )


@pytest.fixture
def source(ch_client, ch_settings_dict, export_db):
    return make_source(ch_client, ch_settings_dict, export_db)


def client_for(user, source, role=SourceRole.USER):
    rbac_manager.grant_source_role(source, role.value, user=user)
    client = APIClient()
    client.force_login(user)
    return client


def export(client, source, **changes):
    data = {
        "columns": "ts, id, level",
        "from": str(T0),
        "to": str(T0 + ROWS * STEP_MS),
        "context_columns": {},
        "format": "json",
    }
    data.update(changes)
    return client.post(f"/ui/v1/sources/{source.slug}/export", data, format="json")


def content(response):
    return b"".join(response.streaming_content).decode()


def oracle_ids(ch_client, db, where):
    return [
        r[0]
        for r in ch_client.query(
            f"SELECT id FROM {db}.logs WHERE {where} ORDER BY ts DESC"
        ).result_rows
    ]


def test_json_has_every_row_past_the_page_limit(test_user, source):
    response = export(client_for(test_user, source), source)
    assert response.status_code == 200
    assert isinstance(response, StreamingHttpResponse)
    rows = json.loads(content(response))
    assert len(rows) == ROWS
    ids = [r["data"]["id"] for r in rows]
    # Newest first, as the explorer shows them; ts is unique per row here.
    assert ids == list(range(ROWS - 1, -1, -1))
    assert rows[0]["data"]["attrs"] == {"k": str((ROWS - 1) % 7)}
    assert rows[0]["severity"] == "error"


def test_filter_text_and_range_are_applied(test_user, ch_client, export_db, source):
    time_from, time_to = T0 + 600_000, T0 + 2_400_000
    response = export(
        client_for(test_user, source),
        source,
        query="level='info'",
        text="connection refused",
        **{"from": str(time_from), "to": str(time_to)},
    )
    ids = [r["data"]["id"] for r in json.loads(content(response))]
    expected = oracle_ids(
        ch_client,
        export_db,
        f"ts BETWEEN fromUnixTimestamp64Milli({time_from}) AND fromUnixTimestamp64Milli({time_to})"
        " AND level = 'info' AND positionCaseInsensitive(body, 'connection refused') > 0",
    )
    assert ids == expected
    assert len(ids) == 13  # 12000, 15000, ..., 48000


def test_csv_has_the_visible_columns(test_user, source):
    response = export(
        client_for(test_user, source), source, format="csv", columns="id, attrs.k"
    )
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    text = content(response)
    lines = list(csv.reader(io.StringIO(text)))
    assert lines[0] == ["Time", "id", "attrs.k"]
    assert len(lines) == ROWS + 1
    assert text.count("\r\n") == ROWS + 1
    assert lines[1] == [
        "2026-09-21T15:03:19.950000Z",
        str(ROWS - 1),
        str((ROWS - 1) % 7),
    ]
    assert lines[-1][1:] == ["0", "0"]


def test_raw_where_is_applied_for_raw_query_users(test_user, source):
    client = client_for(test_user, source, SourceRole.RAW_QUERY_USER)
    rows = json.loads(content(export(client, source, raw_query="id < 100")))
    assert sorted(r["data"]["id"] for r in rows) == list(range(100))


def test_user_without_access_is_refused(hacker_user, source):
    client = APIClient()
    client.force_login(hacker_user)
    assert export(client, source).status_code == 404


def running(ch_client, marker):
    return ch_client.command(
        "SELECT count() FROM system.processes WHERE query LIKE %(m)s AND query NOT LIKE '%%system.processes%%'",
        parameters={"m": f"%{marker}%"},
    )


def wait_until(check, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if check():
            return True
        time.sleep(0.2)
    return False


def test_closing_the_download_stops_the_query(
    test_user, ch_client, ch_settings_dict, export_db
):
    # Far more than the driver reads ahead (10 MB), so ClickHouse is still sending when we close.
    ch_client.command(
        f"CREATE TABLE {export_db}.big ENGINE = MergeTree ORDER BY ts AS SELECT"
        f" fromUnixTimestamp64Milli(toInt64({T0} + number)) AS ts, number AS id,"
        " randomPrintableASCII(100) AS body FROM numbers(2000000)"
    )
    source = make_source(ch_client, ch_settings_dict, export_db, table="big")
    marker = f"export-{uuid.uuid4().hex}"
    response = export(
        client_for(test_user, source),
        source,
        columns="ts, id",
        query=f"body != '{marker}'",
        **{"to": str(T0 + 2000000)},
    )
    assert response.status_code == 200
    next(iter(response.streaming_content))
    assert running(ch_client, marker) == 1
    response.close()
    assert wait_until(lambda: running(ch_client, marker) == 0, 3)
    if not ch_client.command("EXISTS TABLE system.query_log"):
        pytest.skip("system.query_log is not configured on this server")
    ch_client.command("SYSTEM FLUSH LOGS")
    # Stopped, not read to the end by the driver.
    assert ch_client.query(
        "SELECT type, result_rows < 2000000 FROM system.query_log WHERE query LIKE %(m)s"
        " AND type != 'QueryStart' AND query NOT LIKE '%%system.%%'",
        parameters={"m": f"%{marker}%"},
    ).result_rows == [("ExceptionWhileProcessing", 1)]


def test_timeout_mid_stream_fails_the_download(
    test_user, ch_client, ch_settings_dict, export_db
):
    # The source's own timeout still applies; it ends the download with an error, not a short file.
    source = make_source(
        ch_client, ch_settings_dict, export_db, settings="max_execution_time=2"
    )
    client = client_for(test_user, source, SourceRole.RAW_QUERY_USER)
    response = export(client, source, raw_query="sleepEachRow(0.0001) = 0")
    assert response.status_code == 200
    received = []
    with pytest.raises(Exception, match="TIMEOUT_EXCEEDED|Timeout exceeded"):
        for chunk in response.streaming_content:
            received.append(chunk)
    assert not b"".join(received).endswith(b"]\n")


def read_head(f):
    head = b""
    while True:
        line = f.readline()
        if not line:
            return b""
        head += line
        if line == b"\r\n":
            return head


def content_length(head):
    for line in head.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            return int(line.split(b":")[1])
    return 0


class CuttingProxy:
    """Passes ClickHouse HTTP through, but drops the connection once a body passes `cut` bytes:
    between two chunks, or inside a body re-sent with a Content-Length when `dechunk` is set.
    """

    def __init__(self, host, port, cut=None, dechunk=False):
        self.upstream, self.cut, self.dechunk = (host, port), cut, dechunk
        self.server = socket.create_server(("127.0.0.1", 0))
        self.port = self.server.getsockname()[1]
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        while True:
            client, _ = self.server.accept()
            threading.Thread(target=self.handle, args=(client,), daemon=True).start()

    def handle(self, client):
        upstream = socket.create_connection(self.upstream)
        down, up = client.makefile("rb"), upstream.makefile("rb")
        try:
            while head := read_head(down):
                upstream.sendall(head + down.read(content_length(head)))
                head = read_head(up)
                if b"transfer-encoding: chunked" not in head.lower():
                    client.sendall(head + up.read(content_length(head)))
                    continue
                if self.dechunk:
                    body = b""
                    while size := int(up.readline(), 16):
                        body += up.read(size + 2)[:-2]
                    up.readline()
                    head = re.sub(
                        rb"(?i)transfer-encoding: chunked",
                        b"Content-Length: %d" % len(body),
                        head,
                    )
                    cut = self.cut is not None and len(body) > self.cut
                    client.sendall(head + (body[: self.cut] if cut else body))
                    if cut:
                        return
                    continue
                client.sendall(head)
                sent = 0
                while True:
                    size_line = up.readline()
                    data = up.read(int(size_line, 16) + 2)
                    client.sendall(size_line + data)
                    sent += len(data)
                    if size_line.strip() == b"0":
                        break
                    if self.cut is not None and sent > self.cut:
                        return
        finally:
            client.close()
            upstream.close()


def stream_rows(source, port):
    source.conn.data = {**source.conn.data, "port": port}
    request = DataRequest(source, "", "", T0, T0 + ROWS * STEP_MS, None, {})
    return sum(1 for _ in Fetcher.stream_data(request))


@pytest.mark.parametrize("dechunk", [False, True])
def test_a_cut_connection_is_an_error(ch_settings_dict, source, dechunk):
    host, port = ch_settings_dict["host"], ch_settings_dict["port"]
    assert stream_rows(source, CuttingProxy(host, port, dechunk=dechunk).port) == ROWS
    with pytest.raises(Exception) as err:
        stream_rows(source, CuttingProxy(host, port, 200_000, dechunk).port)
    # Cut between chunks, the driver itself sees nothing wrong.
    if not dechunk:
        assert isinstance(err.value, ConnectionError)
