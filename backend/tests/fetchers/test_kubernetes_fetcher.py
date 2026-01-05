import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

from telescope.fetchers.kubernetes.fetcher import Fetcher
from telescope.fetchers.kubernetes.api import LogEntry
from telescope.fetchers.request import DataRequest, GraphDataRequest
from telescope.constants import UTC_ZONE
from tests.data import get_kubernetes_source_data, get_kubernetes_connection_data


@pytest.fixture
def kubernetes_source():
    source_data = get_kubernetes_source_data("test-k8s")
    mock_source = MagicMock()
    mock_source.id = 1
    mock_source.slug = source_data["slug"]
    mock_source.name = source_data["name"]
    mock_source.kind = source_data["kind"]
    mock_source.description = source_data["description"]
    mock_source.time_column = source_data["time_column"]
    mock_source.date_column = source_data.get("date_column", "")
    mock_source.uniq_column = source_data["uniq_column"]
    mock_source.severity_column = source_data["severity_column"]
    mock_source.columns = source_data["columns"]
    mock_source.support_raw_query = source_data["support_raw_query"]
    mock_source.default_chosen_columns = source_data["default_chosen_columns"]
    mock_source.data = source_data["data"]
    mock_source.context_columns = source_data.get("context_columns", {})

    mock_source.conn = MagicMock()
    mock_source.conn.id = 1
    mock_source.conn.data = get_kubernetes_connection_data()["data"]

    mock_source._columns = {name: MagicMock() for name in source_data["columns"]}

    return mock_source


def test_validate_query_valid():
    source = MagicMock()
    valid, error = Fetcher.validate_query(source, 'message ~ "error"')
    assert valid is True
    assert error is None


def test_validate_query_invalid():
    source = MagicMock()
    valid, error = Fetcher.validate_query(source, "invalid (( syntax")
    assert valid is False
    assert error is not None


def test_validate_query_empty():
    source = MagicMock()
    valid, error = Fetcher.validate_query(source, "")
    assert valid is True
    assert error is None


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_connection_ng_success(mock_config_helper, mock_kube_helper):
    mock_config = MagicMock()
    mock_config.list_contexts.return_value = [
        {
            "name": "context1",
            "cluster": "cluster1",
            "user": "user1",
            "namespace": "default",
        },
        {
            "name": "context2",
            "cluster": "cluster2",
            "user": "user2",
            "namespace": "default",
        },
    ]
    mock_config_helper.return_value = mock_config

    mock_helper = MagicMock()
    mock_helper.allowed_contexts = ["context1", "context2"]
    mock_helper.test_connection.return_value = None
    mock_kube_helper.return_value = mock_helper

    conn_data = get_kubernetes_connection_data()["data"]
    resp = Fetcher.test_connection_ng(conn_data)

    assert resp.result is True
    assert resp.total_contexts == 2
    assert resp.matched_contexts == ["context1", "context2"]
    assert resp.error == ""


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_connection_ng_no_matches(mock_config_helper, mock_kube_helper):
    mock_config = MagicMock()
    mock_config.list_contexts.return_value = [
        {
            "name": "context1",
            "cluster": "cluster1",
            "user": "user1",
            "namespace": "default",
        },
    ]
    mock_config_helper.return_value = mock_config

    mock_helper = MagicMock()
    mock_helper.allowed_contexts = []
    mock_kube_helper.return_value = mock_helper

    conn_data = get_kubernetes_connection_data()["data"]
    resp = Fetcher.test_connection_ng(conn_data)

    assert resp.result is False
    assert resp.error == "No contexts matched the filter expression"


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_connection_success(mock_config_helper, mock_kube_helper):
    mock_config = MagicMock()
    mock_config_helper.return_value = mock_config

    mock_helper = MagicMock()
    mock_helper.test_connection.return_value = None
    mock_kube_helper.return_value = mock_helper

    conn_data = get_kubernetes_connection_data()["data"]
    resp = Fetcher.test_connection(conn_data)

    assert resp.reachability["result"] is True
    assert resp.schema["result"] is True
    assert len(resp.schema["data"]) == 10


def test_get_schema():
    schema = Fetcher.get_schema({})
    assert len(schema) == 10
    column_names = [column["name"] for column in schema]
    assert "time" in column_names
    assert "context" in column_names
    assert "namespace" in column_names
    assert "pod" in column_names
    assert "container" in column_names
    assert "node" in column_names
    assert "labels" in column_names
    assert "annotations" in column_names
    assert "message" in column_names
    assert "status" in column_names


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_get_all_context_columns_data(
    mock_config_helper, mock_kube_helper, kubernetes_source
):
    mock_config = MagicMock()
    mock_config_helper.return_value = mock_config

    mock_helper = MagicMock()
    mock_helper.allowed_contexts_set = {"context1", "context2"}
    mock_helper.namespaces = {
        "context1": ["default", "kube-system"],
        "context2": ["default", "app-namespace"],
    }
    mock_kube_helper.return_value = mock_helper

    result = Fetcher.get_all_context_columns_data(kubernetes_source)

    assert "contexts" in result
    assert "namespaces" in result
    assert set(result["contexts"]) == {"context1", "context2"}
    assert set(result["namespaces"]) == {"default", "kube-system", "app-namespace"}


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_get_context_column_data_contexts(
    mock_config_helper, mock_kube_helper, kubernetes_source
):
    mock_config = MagicMock()
    mock_config_helper.return_value = mock_config

    mock_helper = MagicMock()
    mock_helper.allowed_contexts_set = {"context1", "context2"}
    mock_kube_helper.return_value = mock_helper

    result = Fetcher.get_context_column_data(kubernetes_source, "context")
    assert result == ["context1", "context2"] or set(result) == {"context1", "context2"}


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_get_context_column_data_namespaces(
    mock_config_helper, mock_kube_helper, kubernetes_source
):
    mock_config = MagicMock()
    mock_config_helper.return_value = mock_config

    mock_helper = MagicMock()
    mock_helper.allowed_contexts_set = {"context1"}
    mock_helper.namespaces = {
        "context1": ["default", "kube-system"],
    }
    mock_kube_helper.return_value = mock_helper

    result = Fetcher.get_context_column_data(kubernetes_source, "namespace")
    assert set(result) == {"default", "kube-system"}


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_get_context_column_data_pods(
    mock_config_helper, mock_kube_helper, kubernetes_source
):
    mock_config = MagicMock()
    mock_config_helper.return_value = mock_config

    mock_helper = MagicMock()
    mock_helper.pods = {
        "context1": {
            "default": {
                "pod1": {
                    "containers": ["container1", "container2"],
                    "status": "Running",
                    "labels": {"app": "myapp"},
                    "annotations": {},
                }
            }
        }
    }
    mock_helper.validate.return_value = None
    mock_kube_helper.return_value = mock_helper

    params = {"contexts": ["context1"], "namespaces": ["default"]}
    result = Fetcher.get_context_column_data(kubernetes_source, "pods", params)

    assert len(result) == 1
    assert result[0]["context"] == "context1"
    assert result[0]["namespace"] == "default"
    assert result[0]["pod_name"] == "pod1"
    assert result[0]["containers"] == ["container1", "container2"]
    assert result[0]["status"] == "Running"


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_fetch_data_simple(mock_config_helper, mock_kube_helper, kubernetes_source):
    mock_config = MagicMock()
    mock_config_helper.return_value = mock_config

    log_entries = [
        LogEntry(
            context="context1",
            namespace="default",
            pod="pod1",
            container="container1",
            timestamp=datetime(2025, 1, 1, 0, 0, 1, tzinfo=UTC_ZONE),
            message="Log line 1",
            node="node1",
            labels={"app": "myapp"},
            annotations={},
            status="Running",
        ),
        LogEntry(
            context="context1",
            namespace="default",
            pod="pod1",
            container="container1",
            timestamp=datetime(2025, 1, 1, 0, 0, 2, tzinfo=UTC_ZONE),
            message="Log line 2",
            node="node1",
            labels={"app": "myapp"},
            annotations={},
            status="Running",
        ),
    ]

    mock_helper = MagicMock()
    mock_helper.contexts = ["context1"]
    mock_helper.namespaces = {"context1": ["default"]}
    mock_helper.pods = {
        "context1": {"default": {"pod1": {"containers": ["container1"]}}}
    }
    mock_helper.get_logs.return_value = (log_entries, [])
    mock_helper.validate.return_value = None
    mock_helper.errors = []
    mock_kube_helper.return_value = mock_helper

    request = DataRequest(
        source=kubernetes_source,
        query="",
        raw_query="",
        time_from=1000000000000,
        time_to=2000000000000,
        limit=10,
        context_columns={},
    )
    response = Fetcher.fetch_data(request, tz=UTC_ZONE)

    assert len(response.rows) == 2
    assert response.rows[0].data["message"] == "Log line 2"
    assert response.rows[1].data["message"] == "Log line 1"
    assert response.rows[0].data["context"] == "context1"
    assert response.rows[0].data["namespace"] == "default"
    assert response.rows[0].data["pod"] == "pod1"


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_fetch_data_with_query(mock_config_helper, mock_kube_helper, kubernetes_source):
    mock_config = MagicMock()
    mock_config_helper.return_value = mock_config

    log_entries = [
        LogEntry(
            context="context1",
            namespace="default",
            pod="pod1",
            container="container1",
            timestamp=datetime(2025, 1, 1, 0, 0, 1, tzinfo=UTC_ZONE),
            message="Error: something went wrong",
            node="node1",
            labels={},
            annotations={},
            status="Running",
        ),
        LogEntry(
            context="context1",
            namespace="default",
            pod="pod1",
            container="container1",
            timestamp=datetime(2025, 1, 1, 0, 0, 2, tzinfo=UTC_ZONE),
            message="Info: everything is fine",
            node="node1",
            labels={},
            annotations={},
            status="Running",
        ),
    ]

    mock_helper = MagicMock()
    mock_helper.contexts = ["context1"]
    mock_helper.namespaces = {"context1": ["default"]}
    mock_helper.pods = {
        "context1": {"default": {"pod1": {"containers": ["container1"]}}}
    }
    mock_helper.get_logs.return_value = (log_entries, [])
    mock_helper.validate.return_value = None
    mock_helper.errors = []
    mock_kube_helper.return_value = mock_helper

    request = DataRequest(
        source=kubernetes_source,
        query='message ~ "Error"',
        raw_query="",
        time_from=1000000000000,
        time_to=2000000000000,
        limit=10,
        context_columns={},
    )
    response = Fetcher.fetch_data(request, tz=UTC_ZONE)

    assert len(response.rows) == 1
    assert "Error" in response.rows[0].data["message"]


@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_fetch_data_no_pods(mock_config_helper, mock_kube_helper, kubernetes_source):
    mock_config = MagicMock()
    mock_config_helper.return_value = mock_config

    mock_helper = MagicMock()
    mock_helper.contexts = ["context1"]
    mock_helper.namespaces = {"context1": ["default"]}
    mock_helper.pods = {}
    mock_helper.validate.return_value = None
    mock_helper.errors = []
    mock_kube_helper.return_value = mock_helper

    request = DataRequest(
        source=kubernetes_source,
        query="",
        raw_query="",
        time_from=1000000000000,
        time_to=2000000000000,
        limit=10,
        context_columns={},
    )
    response = Fetcher.fetch_data(request, tz=UTC_ZONE)

    assert len(response.rows) == 0
    assert response.error == "No pods found matching the filters"


def test_autocomplete(kubernetes_source):
    """Test autocomplete functionality."""
    response = Fetcher.autocomplete(kubernetes_source, "message", 0, 1000, "test")
    assert response.items == []
    assert response.incomplete is False
