import pytest
from unittest.mock import Mock, MagicMock, patch

from telescope.fetchers.clickhouse import Fetcher as ClickhouseFetcher
from telescope.fetchers.request import DataRequest
from telescope.models import Source
from telescope.constants import UTC_ZONE


@pytest.fixture
def mock_source():
    """ClickHouse source with no saved order_by_expression"""
    source = Mock(spec=Source)
    source.data = {"database": "test_db", "table": "test_table"}
    source.time_column = "timestamp"
    source.date_column = None
    source.order_by_expression = ""
    source._columns = {
        "timestamp": Mock(type="DateTime"),
        "message": Mock(type="String"),
    }
    mock_connection = Mock()
    mock_connection.data = {
        "host": "localhost",
        "port": 8123,
        "user": "default",
        "password": "",
        "ssl": False,
    }
    source.conn = mock_connection
    return source


@pytest.fixture
def mock_source_with_saved_order_by(mock_source):
    """ClickHouse source with a saved order_by_expression"""
    mock_source.order_by_expression = "event_time DESC, id ASC"
    return mock_source


def _make_request(source, order_by_expression=""):
    return DataRequest(
        source=source,
        time_from=1000000000000,
        time_to=2000000000000,
        limit=100,
        query=None,
        raw_query=None,
        context_columns={},
        order_by_expression=order_by_expression,
    )


def _run_fetch(source, order_by_expression=""):
    with patch("telescope.fetchers.clickhouse.ClickhouseConnect") as mock_connect:
        mock_client = MagicMock()
        mock_client.query.return_value = MagicMock(result_rows=[])
        mock_connect.return_value.__enter__.return_value.client = mock_client

        request = _make_request(source, order_by_expression)
        ClickhouseFetcher.fetch_data(request, tz=UTC_ZONE)

        assert mock_client.query.called
        return mock_client.query.call_args[0][0]


def test_fetch_data_default_order_by(mock_source):
    """When both request and source have no order_by_expression, use ORDER BY time_column DESC"""
    query = _run_fetch(mock_source)
    assert "ORDER BY timestamp DESC" in query


def test_fetch_data_uses_source_order_by_expression(mock_source_with_saved_order_by):
    """When source has a saved order_by_expression and request has none, use source's"""
    query = _run_fetch(mock_source_with_saved_order_by)
    assert "ORDER BY event_time DESC, id ASC" in query
    assert "ORDER BY timestamp DESC" not in query


def test_fetch_data_uses_request_order_by_expression(mock_source):
    """When request provides an order_by_expression, it is used"""
    query = _run_fetch(mock_source, order_by_expression="message ASC")
    assert "ORDER BY message ASC" in query
    assert "ORDER BY timestamp DESC" not in query


def test_fetch_data_request_overrides_source_order_by_expression(
    mock_source_with_saved_order_by,
):
    """Ad-hoc request order_by_expression takes priority over source's saved value"""
    query = _run_fetch(
        mock_source_with_saved_order_by, order_by_expression="message ASC"
    )
    assert "ORDER BY message ASC" in query
    assert "ORDER BY event_time DESC, id ASC" not in query


def test_fetch_data_order_by_position(mock_source):
    """ORDER BY appears before LIMIT in the generated SQL"""
    query = _run_fetch(mock_source)
    order_by_pos = query.find("ORDER BY")
    limit_pos = query.find("LIMIT 100")
    assert order_by_pos != -1
    assert limit_pos != -1
    assert order_by_pos < limit_pos, "ORDER BY must come before LIMIT"


def test_fetch_data_empty_request_expression_falls_back_to_source(
    mock_source_with_saved_order_by,
):
    """An empty string in the request does not override the source's saved expression"""
    query = _run_fetch(mock_source_with_saved_order_by, order_by_expression="")
    assert "ORDER BY event_time DESC, id ASC" in query
