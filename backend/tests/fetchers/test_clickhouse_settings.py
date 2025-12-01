import pytest
from unittest.mock import Mock, MagicMock, patch

from telescope.fetchers.clickhouse import Fetcher as ClickhouseFetcher
from telescope.fetchers.request import DataRequest, GraphDataRequest
from telescope.models import Source
from telescope.constants import UTC_ZONE


@pytest.fixture
def mock_clickhouse_source():
    """Create a mock ClickHouse source with settings"""
    source = Mock(spec=Source)
    source.data = {
        "database": "test_db",
        "table": "test_table",
        "settings": "use_query_cache = true, max_parallel_replicas = 1",
    }
    source.time_field = "timestamp"
    source.date_field = None
    source._fields = {
        "timestamp": Mock(type="DateTime"),
        "message": Mock(type="String"),
    }

    # Mock connection
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
def mock_clickhouse_source_no_settings():
    """Create a mock ClickHouse source without settings"""
    source = Mock(spec=Source)
    source.data = {"database": "test_db", "table": "test_table"}
    source.time_field = "timestamp"
    source.date_field = None
    source._fields = {
        "timestamp": Mock(type="DateTime"),
        "message": Mock(type="String"),
    }

    # Mock connection
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


@patch("telescope.fetchers.clickhouse.ClickhouseConnect")
def test_fetch_data_includes_settings(mock_clickhouse_connect, mock_clickhouse_source):
    """Test that fetch_data() includes SETTINGS clause when configured"""
    # Setup mock
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.result_rows = []
    mock_client.query.return_value = mock_result

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_clickhouse_connect.return_value = mock_context

    # Create request
    request = DataRequest(
        source=mock_clickhouse_source,
        time_from=1000000000000,
        time_to=2000000000000,
        limit=100,
        query=None,
        raw_query=None,
        context_fields={},
    )

    # Execute
    ClickhouseFetcher.fetch_data(request, tz=UTC_ZONE)

    # Verify query was called
    assert mock_client.query.called
    query = mock_client.query.call_args[0][0]

    # Assert SETTINGS clause is present
    assert "SETTINGS" in query
    assert "use_query_cache = true" in query
    assert "max_parallel_replicas = 1" in query

    # Assert SETTINGS is at the end of the query
    assert query.rstrip().endswith("use_query_cache = true, max_parallel_replicas = 1")


@patch("telescope.fetchers.clickhouse.ClickhouseConnect")
def test_fetch_data_without_settings(
    mock_clickhouse_connect, mock_clickhouse_source_no_settings
):
    """Test that fetch_data() works without SETTINGS clause"""
    # Setup mock
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.result_rows = []
    mock_client.query.return_value = mock_result

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_clickhouse_connect.return_value = mock_context

    # Create request
    request = DataRequest(
        source=mock_clickhouse_source_no_settings,
        time_from=1000000000000,
        time_to=2000000000000,
        limit=100,
        query=None,
        raw_query=None,
        context_fields={},
    )

    # Execute
    ClickhouseFetcher.fetch_data(request, tz=UTC_ZONE)

    # Verify query was called
    assert mock_client.query.called
    query = mock_client.query.call_args[0][0]

    # Assert SETTINGS clause is NOT present
    assert "SETTINGS" not in query


@patch("telescope.fetchers.clickhouse.ClickhouseConnect")
def test_fetch_graph_data_includes_settings(
    mock_clickhouse_connect, mock_clickhouse_source
):
    """Test that fetch_graph_data() includes SETTINGS clause when configured"""
    # Setup mock
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.result_rows = []
    mock_client.query.return_value = mock_result

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_clickhouse_connect.return_value = mock_context

    # Create request
    request = GraphDataRequest(
        source=mock_clickhouse_source,
        time_from=1000000000000,
        time_to=2000000000000,
        query=None,
        raw_query=None,
        group_by=[],
        context_fields={},
    )

    # Execute
    ClickhouseFetcher.fetch_graph_data(request)

    # Verify query was called
    assert mock_client.query.called
    query = mock_client.query.call_args[0][0]

    # Assert SETTINGS clause is present
    assert "SETTINGS" in query
    assert "use_query_cache = true" in query
    assert "max_parallel_replicas = 1" in query


@patch("telescope.fetchers.clickhouse.ClickhouseConnect")
def test_autocomplete_includes_settings(
    mock_clickhouse_connect, mock_clickhouse_source
):
    """Test that autocomplete() includes SETTINGS clause when configured"""
    # Setup mock
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.result_rows = []
    mock_client.query.return_value = mock_result

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_clickhouse_connect.return_value = mock_context

    # Execute
    ClickhouseFetcher.autocomplete(
        source=mock_clickhouse_source,
        field="message",
        time_from=1000000000000,
        time_to=2000000000000,
        value="test",
    )

    # Verify query was called
    assert mock_client.query.called
    query = mock_client.query.call_args[0][0]

    # Assert SETTINGS clause is present
    assert "SETTINGS" in query
    assert "use_query_cache = true" in query
    assert "max_parallel_replicas = 1" in query


@patch("telescope.fetchers.clickhouse.ClickhouseConnect")
def test_settings_empty_string_not_added(
    mock_clickhouse_connect, mock_clickhouse_source_no_settings
):
    """Test that empty settings string doesn't add SETTINGS clause"""
    # Setup mock
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.result_rows = []
    mock_client.query.return_value = mock_result

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_clickhouse_connect.return_value = mock_context

    # Set empty settings
    mock_clickhouse_source_no_settings.data["settings"] = ""

    # Create request
    request = DataRequest(
        source=mock_clickhouse_source_no_settings,
        time_from=1000000000000,
        time_to=2000000000000,
        limit=100,
        query=None,
        raw_query=None,
        context_fields={},
    )

    # Execute
    ClickhouseFetcher.fetch_data(request, tz=UTC_ZONE)

    # Verify query was called
    assert mock_client.query.called
    query = mock_client.query.call_args[0][0]

    # Assert SETTINGS clause is NOT present for empty string
    assert "SETTINGS" not in query


@patch("telescope.fetchers.clickhouse.ClickhouseConnect")
def test_settings_query_position(mock_clickhouse_connect, mock_clickhouse_source):
    """Test that SETTINGS clause is positioned correctly at the end of query"""
    # Setup mock
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.result_rows = []
    mock_client.query.return_value = mock_result

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_clickhouse_connect.return_value = mock_context

    # Create request
    request = DataRequest(
        source=mock_clickhouse_source,
        time_from=1000000000000,
        time_to=2000000000000,
        limit=100,
        query=None,
        raw_query=None,
        context_fields={},
    )

    # Execute
    ClickhouseFetcher.fetch_data(request, tz=UTC_ZONE)

    # Verify query structure
    query = mock_client.query.call_args[0][0]

    # Assert query structure: SELECT ... FROM ... WHERE ... ORDER BY ... LIMIT ... SETTINGS ...
    assert "SELECT" in query
    assert "FROM test_db.test_table" in query
    assert "WHERE" in query
    assert "ORDER BY" in query
    assert "LIMIT 100" in query

    # SETTINGS should come after LIMIT
    limit_pos = query.find("LIMIT 100")
    settings_pos = query.find("SETTINGS")
    assert settings_pos > limit_pos, "SETTINGS clause should come after LIMIT"
