import pytest
from unittest.mock import Mock, MagicMock, patch

from telescope.fetchers.starrocks import Fetcher as StarrocksFetcher
from telescope.fetchers.request import DataRequest, GraphDataRequest
from telescope.models import Source
from telescope.constants import UTC_ZONE


@pytest.fixture
def mock_starrocks_source():
    """Create a mock Starrocks source with settings"""
    source = Mock(spec=Source)
    source.data = {
        "catalog": "default_catalog",
        "database": "test_db",
        "table": "test_table",
        "settings": "query_timeout=60, time_zone='UTC'",
    }
    source.time_column = "timestamp"
    source.date_column = None
    source._columns = {
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
def mock_starrocks_source_no_settings():
    """Create a mock Starrocks source without settings"""
    source = Mock(spec=Source)
    source.data = {"catalog": "default_catalog", "database": "test_db", "table": "test_table"}
    source.time_column = "timestamp"
    source.date_column = None
    source._columns = {
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


@patch("telescope.fetchers.starrocks.StarrocksConnect")
def test_fetch_data_includes_settings(mock_starrocks_connect, mock_starrocks_source):
    """Test that fetch_data() includes SET_VAR clause when configured"""
    # Setup mock
    mock_client = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = []
    mock_client.cursor.return_value = mock_cursor

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_starrocks_connect.return_value = mock_context

    # Create request
    request = DataRequest(
        source=mock_starrocks_source,
        time_from=1000000000000,
        time_to=2000000000000,
        limit=100,
        query=None,
        raw_query=None,
        context_columns={},
    )

    # Execute
    StarrocksFetcher.fetch_data(request, tz=UTC_ZONE)

    # Verify execute was called
    assert mock_cursor.execute.called
    query = mock_cursor.execute.call_args[0][0]

    # Assert SET_VAR clause is present
    assert "SET_VAR" in query
    assert "query_timeout=60" in query
    assert "time_zone='UTC'" in query

    # Assert SET_VAR is at the start of the query
    assert query.lstrip().startswith("SELECT /*+ SET_VAR(query_timeout=60, time_zone='UTC'")

@patch("telescope.fetchers.starrocks.StarrocksConnect")
def test_fetch_data_without_settings(
    mock_starrocks_connect, mock_starrocks_source_no_settings
):
    """Test that fetch_data() works without SET_VAR clause"""
    # Setup mock
    mock_client = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = []
    mock_client.cursor.return_value = mock_cursor

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_starrocks_connect.return_value = mock_context

    # Create request
    request = DataRequest(
        source=mock_starrocks_source_no_settings,
        time_from=1000000000000,
        time_to=2000000000000,
        limit=100,
        query=None,
        raw_query=None,
        context_columns={},
    )

    # Execute
    StarrocksFetcher.fetch_data(request, tz=UTC_ZONE)

    # Verify execute was called
    assert mock_cursor.execute.called
    query = mock_cursor.execute.call_args[0][0]

    # Assert SET_VAR clause is NOT present
    assert "SET_VAR" not in query


@patch("telescope.fetchers.starrocks.StarrocksConnect")
def test_fetch_graph_data_includes_settings(
    mock_starrocks_connect, mock_starrocks_source
):
    """Test that fetch_graph_data() includes SET_VAR clause when configured"""
    # Setup mock
    mock_client = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = []
    mock_client.cursor.return_value = mock_cursor

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_starrocks_connect.return_value = mock_context

    # Create request
    request = GraphDataRequest(
        source=mock_starrocks_source,
        time_from=1000000000000,
        time_to=2000000000000,
        query=None,
        raw_query=None,
        group_by=[],
        context_columns={},
    )

    # Execute
    StarrocksFetcher.fetch_graph_data(request)

    # Verify execute was called
    assert mock_cursor.execute.called
    query = mock_cursor.execute.call_args[0][0]

    # Assert SET_VAR clause is present
    assert "SET_VAR" in query
    assert "query_timeout=60" in query
    assert "time_zone='UTC'" in query


@patch("telescope.fetchers.starrocks.StarrocksConnect")
def test_autocomplete_includes_settings(
    mock_starrocks_connect, mock_starrocks_source
):
    """Test that autocomplete() includes SET_VAR clause when configured"""
    # Setup mock
    mock_client = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = []
    mock_client.cursor.return_value = mock_cursor

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_starrocks_connect.return_value = mock_context

    # Execute
    StarrocksFetcher.autocomplete(
        source=mock_starrocks_source,
        column="message",
        time_from=1000000000000,
        time_to=2000000000000,
        value="test",
    )

    assert mock_cursor.execute.called
    query = mock_cursor.execute.call_args[0][0]

    # Assert SET_VAR clause is present
    assert "SET_VAR" in query
    assert "query_timeout=60" in query
    assert "time_zone='UTC'" in query


@patch("telescope.fetchers.starrocks.StarrocksConnect")
def test_settings_empty_string_not_added(
    mock_starrocks_connect, mock_starrocks_source_no_settings
):
    """Test that empty settings string doesn't add SET_VAR clause"""
    # Setup mock
    mock_client = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = []
    mock_client.cursor.return_value = mock_cursor

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_starrocks_connect.return_value = mock_context

    # Set empty settings
    mock_starrocks_source_no_settings.data["settings"] = ""

    # Create request
    request = DataRequest(
        source=mock_starrocks_source_no_settings,
        time_from=1000000000000,
        time_to=2000000000000,
        limit=100,
        query=None,
        raw_query=None,
        context_columns={},
    )

    # Execute
    StarrocksFetcher.fetch_data(request, tz=UTC_ZONE)

    # Verify execute was called
    assert mock_cursor.execute.called
    query = mock_cursor.execute.call_args[0][0]

    # Assert SET_VAR clause is NOT present for empty string
    assert "SET_VAR" not in query


@patch("telescope.fetchers.starrocks.StarrocksConnect")
def test_settings_query_position(mock_starrocks_connect, mock_starrocks_source):
    """Test that SET_VAR clause is positioned correctly at the start of query"""
    # Setup mock
    mock_client = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = []
    mock_client.cursor.return_value = mock_cursor

    mock_context = MagicMock()
    mock_context.__enter__.return_value.client = mock_client
    mock_starrocks_connect.return_value = mock_context

    # Create request
    request = DataRequest(
        source=mock_starrocks_source,
        time_from=1000000000000,
        time_to=2000000000000,
        limit=100,
        query=None,
        raw_query=None,
        context_columns={},
    )

    # Execute
    StarrocksFetcher.fetch_data(request, tz=UTC_ZONE)

    # Verify query structure
    query = mock_cursor.execute.call_args[0][0]

    # Assert query structure: SELECT SET_VAR ... FROM ... WHERE ... ORDER BY ... LIMIT ...
    assert "SELECT" in query
    assert "FROM default_catalog.test_db.test_table" in query
    assert "WHERE" in query
    assert "ORDER BY" in query
    assert "LIMIT 100" in query

    # SET_VAR should come before FROM but after SELECT
    select_pos = query.find("SELECT")
    settings_pos = query.find("SET_VAR")
    from_pos = query.find("FROM")
    assert select_pos < settings_pos < from_pos, "SET_VAR clause should come after SELECT"
