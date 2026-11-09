"""/ui/v1/sources/<slug>/export: access checks, the request handed to the fetcher and the streamed file."""

import json
import time
from unittest.mock import patch

import pytest
from django.http import StreamingHttpResponse
from django.middleware.csrf import _get_new_csrf_string
from rest_framework.test import APIClient

from telescope.fetchers.fetcher import BaseFetcher
from telescope.fetchers.request import DataRequest
from telescope.fetchers.response import DataResponse
from telescope.fetchers.starrocks import EXPORT_PAGE_ROWS, Fetcher as StarrocksFetcher
from telescope.rbac.manager import RBACManager
from telescope.rbac.roles import SourceRole

rbac_manager = RBACManager()
T0 = 1762423200000
STREAM = "telescope.fetchers.clickhouse.Fetcher.stream_data"


class FakeRow:
    def __init__(self, i, data=None):
        self.time = {
            "unixtime": T0 + i,
            "datetime": "2025-11-06 10:00:00",
            "microseconds": f"{i:06d}",
        }
        self.data = data or {"hostname": f"h{i}"}

    def as_dict(self):
        return {"time": self.time, "severity": "", "data": self.data}


def gen(rows):
    return (row for row in rows)


def body(**changes):
    data = {
        "columns": "hostname",
        "from": str(T0),
        "to": str(T0 + 3600000),
        "context_columns": {},
        "format": "json",
    }
    data.update(changes)
    return data


def client_for(user, **kwargs):
    client = APIClient(**kwargs)
    client.force_login(user)
    return client


@pytest.fixture
def client(test_user, clickhouse_source):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    return client_for(test_user)


def export(client, slug, data):
    return client.post(f"/ui/v1/sources/{slug}/export", data, format="json")


def content(response):
    return b"".join(response.streaming_content).decode()


@pytest.mark.django_db
def test_streams_every_row_without_a_limit(client, clickhouse_source):
    rows = [FakeRow(i) for i in range(3)]
    with patch(STREAM, return_value=gen(rows)) as stream:
        response = export(
            client,
            clickhouse_source.slug,
            body(query="hostname='h1'", text="refused", limit=50, before={"time": 1}),
        )
        assert isinstance(response, StreamingHttpResponse)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"
        assert response["Content-Disposition"] == (
            f'attachment; filename="{clickhouse_source.slug}'
            '_20251106T100000Z_20251106T110000Z.json"'
        )
        assert json.loads(content(response)) == [r.as_dict() for r in rows]
    request = stream.call_args[0][0]
    assert isinstance(request, DataRequest)
    assert request.limit is None and request.before is None
    assert (request.query, request.text, request.raw_query) == (
        "hostname='h1'",
        "refused",
        "",
    )
    assert (request.time_from, request.time_to) == (T0, T0 + 3600000)


@pytest.mark.django_db
def test_relative_range_is_resolved_once_into_the_filename(client, clickhouse_source):
    with patch(STREAM, return_value=gen([])) as stream:
        before = int(time.time() * 1000)
        response = export(
            client, clickhouse_source.slug, body(**{"from": "now-1h", "to": "now"})
        )
        after = int(time.time() * 1000)
        assert content(response) == "[\n]\n"
    request = stream.call_args[0][0]
    assert before - 3600000 - 1000 <= request.time_from <= after - 3600000
    # parse_time() rounds 'now' down to the second.
    assert 3599000 < request.time_to - request.time_from <= 3600000
    assert "now" not in response["Content-Disposition"]


@pytest.mark.django_db
def test_csv_has_the_visible_columns(client, clickhouse_source):
    rows = [
        FakeRow(0, {"hostname": 'a,"b"', "thread_id": 7}),
        FakeRow(1, {"hostname": None, "thread_id": 8}),
    ]
    with patch(STREAM, return_value=gen(rows)):
        response = export(
            client,
            clickhouse_source.slug,
            body(format="csv", columns="thread_id, hostname"),
        )
        assert response["Content-Type"] == "text/csv; charset=utf-8"
        assert response["Content-Disposition"].endswith('.csv"')
        assert content(response) == (
            "Time,thread_id,hostname\r\n"
            '2025-11-06T10:00:00.000000Z,7,"a,""b"""\r\n'
            "2025-11-06T10:00:00.000001Z,8,\r\n"
        )


@pytest.mark.django_db
def test_needs_source_use(hacker_user, clickhouse_source):
    with patch(STREAM) as stream:
        response = export(client_for(hacker_user), clickhouse_source.slug, body())
    assert not stream.called
    assert response.status_code == 404
    assert response.json()["errors"] == ["source not found"]


@pytest.mark.django_db
def test_raw_where_needs_raw_query_permission(client, test_user, clickhouse_source):
    with patch(STREAM, return_value=gen([])) as stream:
        response = export(client, clickhouse_source.slug, body(raw_query="1 = 1"))
        assert not stream.called
        assert response.status_code == 400
        assert response.json()["validation"]["result"] is False
        rbac_manager.grant_source_role(
            clickhouse_source, SourceRole.RAW_QUERY_USER.value, user=test_user
        )
        response = export(client, clickhouse_source.slug, body(raw_query="1 = 1"))
        assert response.status_code == 200
    assert stream.call_args[0][0].raw_query == "1 = 1"


@pytest.mark.django_db
def test_bad_format_is_refused(client, clickhouse_source):
    with patch(STREAM) as stream:
        response = export(client, clickhouse_source.slug, body(format="xml"))
    assert not stream.called
    assert response.status_code == 400
    assert "format" in response.json()["validation"]["columns"]


@pytest.mark.django_db
def test_error_before_the_first_row_is_an_error_response(client, clickhouse_source):
    def failing(*args, **kwargs):
        raise ValueError("Code: 47. Unknown identifier")
        yield

    with patch(STREAM, side_effect=failing):
        response = export(client, clickhouse_source.slug, body())
    assert response.status_code == 400
    assert response.json()["errors"] == ["Code: 47. Unknown identifier"]


@pytest.mark.django_db
def test_error_mid_stream_raises_so_the_file_is_not_complete(client, clickhouse_source):
    def failing(*args, **kwargs):
        for i in range(2000):
            yield FakeRow(i)
        raise ConnectionError("ClickHouse ended the result early")

    with patch(STREAM, side_effect=failing):
        response = export(client, clickhouse_source.slug, body())
        chunks = iter(response.streaming_content)
        first = next(chunks)
        assert first.startswith(b"[\n")
        with pytest.raises(ConnectionError):
            for _ in chunks:
                pass


@pytest.mark.django_db
def test_closing_the_response_closes_the_rows(client, clickhouse_source):
    closed = []

    def endless(*args, **kwargs):
        try:
            i = 0
            while True:
                yield FakeRow(i)
                i += 1
        finally:
            closed.append(True)

    with patch(STREAM, side_effect=endless):
        response = export(client, clickhouse_source.slug, body())
        next(iter(response.streaming_content))
        assert not closed
        response.close()
    assert closed == [True]


@pytest.mark.django_db
def test_form_post_needs_the_csrf_token(test_user, clickhouse_source):
    rbac_manager.grant_source_role(
        clickhouse_source, SourceRole.USER.value, user=test_user
    )
    client = client_for(test_user, enforce_csrf_checks=True)
    token = _get_new_csrf_string()
    client.cookies["csrftoken"] = token
    url = f"/ui/v1/sources/{clickhouse_source.slug}/export"
    form = {"params": json.dumps(body())}
    with patch(STREAM, return_value=gen([FakeRow(0)])):
        assert client.post(url, form).status_code == 403
        response = client.post(url, {**form, "csrfmiddlewaretoken": token})
        assert response.status_code == 200
        assert len(json.loads(content(response))) == 1


def test_starrocks_pages_by_the_keyset_cursor_until_the_end():
    pages = [
        DataResponse(rows=[1, 2], cursor={"time": "2", "skip": 1}),
        DataResponse(rows=[3, 4], cursor={"time": "4", "skip": 1}),
        DataResponse(rows=[5], cursor=None),
    ]
    seen = []

    def fetch_data(request, tz=None):
        seen.append((request.limit, request.before))
        return pages[len(seen) - 1]

    request = DataRequest(None, "", "", 0, 1, None, {})
    with patch.object(StarrocksFetcher, "fetch_data", side_effect=fetch_data):
        assert list(StarrocksFetcher.stream_data(request)) == [1, 2, 3, 4, 5]
    assert seen == [
        (EXPORT_PAGE_ROWS, None),
        (EXPORT_PAGE_ROWS, {"time": "2", "skip": 1}),
        (EXPORT_PAGE_ROWS, {"time": "4", "skip": 1}),
    ]
    assert request.limit is None and request.before is None


def test_log_sources_export_one_unlimited_fetch():
    calls = []

    class Logs(BaseFetcher):
        @classmethod
        def fetch_data(cls, request, tz=None):
            calls.append(request.limit)
            return DataResponse(rows=list(range(30000)))

    request = DataRequest(None, "", "", 0, 1, None, {})
    assert len(list(Logs.stream_data(request))) == 30000
    assert calls == [None]


def test_log_source_error_is_raised():
    class Logs(BaseFetcher):
        @classmethod
        def fetch_data(cls, request, tz=None):
            return DataResponse(rows=[], error="No pods found matching the filters")

    with pytest.raises(ValueError, match="No pods found"):
        list(Logs.stream_data(DataRequest(None, "", "", 0, 1, None, {})))
