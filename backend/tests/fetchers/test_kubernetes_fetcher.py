import json
import pytest
from unittest.mock import patch, MagicMock

from telescope.fetchers.kubernetes import Fetcher
from telescope.fetchers.request import DataRequest, GraphDataRequest
from telescope.models import Source
from telescope.constants import UTC_ZONE
from tests.data import get_kubernetes_source_data, get_kubernetes_connection_data


# Helper objects to mimic Kubernetes API responses
class _Meta:
    def __init__(self, name, namespace=None, labels=None):
        self.name = name
        self.namespace = namespace
        self.labels = labels or {}


class _Status:
    def __init__(self, phase="Running", pod_ip="10.0.0.1"):
        self.phase = phase
        self.pod_ip = pod_ip


class _Spec:
    def __init__(self, containers, node_name="node-1"):
        self.containers = containers
        self.node_name = node_name


class _Container:
    def __init__(self, name, image="busybox"):
        self.name = name
        self.image = image


class _Pod:
    def __init__(
        self, name, namespace, containers, status=None, node_name="node-1", labels=None
    ):
        self.metadata = _Meta(name=name, namespace=namespace, labels=labels)
        self.status = status or _Status()
        self.spec = _Spec(containers=containers, node_name=node_name)


class _NamespaceList:
    def __init__(self, items):
        self.items = items


class _PodList:
    def __init__(self, items):
        self.items = items


class _DeploymentSpec:
    def __init__(self, replicas=1):
        self.replicas = replicas


class _DeploymentStatus:
    def __init__(self, ready_replicas=1, conditions=None):
        self.ready_replicas = ready_replicas
        self.conditions = conditions or []


class _Deployment:
    def __init__(self, name, namespace, replicas=1, ready_replicas=1, labels=None):
        self.metadata = _Meta(name=name, namespace=namespace, labels=labels or {})
        self.spec = _DeploymentSpec(replicas=replicas)
        self.status = _DeploymentStatus(ready_replicas=ready_replicas)


class _DeploymentList:
    def __init__(self, items):
        self.items = items


@pytest.fixture
def kubernetes_source():
    """Create a test Kubernetes source using the data factory."""
    source_data = get_kubernetes_source_data("test-k8s")
    # Create a mock source that behaves like a Django model instance
    mock_source = MagicMock()
    mock_source.slug = source_data["slug"]
    mock_source.name = source_data["name"]
    mock_source.kind = source_data["kind"]
    mock_source.description = source_data["description"]
    mock_source.time_field = source_data["time_field"]
    mock_source.date_field = source_data.get("date_field", "")
    mock_source.uniq_field = source_data["uniq_field"]
    mock_source.severity_field = source_data["severity_field"]
    mock_source.fields = source_data["fields"]
    mock_source.support_raw_query = source_data["support_raw_query"]
    mock_source.default_chosen_fields = source_data["default_chosen_fields"]
    mock_source.data = source_data["data"]
    mock_source.context_fields = source_data.get("context_fields", {})

    # Mock the connection
    mock_source.conn = MagicMock()
    mock_source.conn.data = get_kubernetes_connection_data()["data"]

    # Mock the fields access
    mock_source._fields = {name: MagicMock() for name in source_data["fields"]}

    return mock_source


@patch("telescope.fetchers.kubernetes.client.AppsV1Api")
@patch("telescope.fetchers.kubernetes.client.CoreV1Api")
def test_connection_success(mock_core_api, mock_apps_api):
    mock_core_instance = MagicMock()
    mock_core_instance.list_namespace.return_value = _NamespaceList(items=[])
    mock_core_api.return_value = mock_core_instance

    mock_apps_instance = MagicMock()
    mock_apps_api.return_value = mock_apps_instance

    conn_data = get_kubernetes_connection_data()["data"]
    resp = Fetcher.test_connection(conn_data)
    assert resp.reachability["result"] is True
    assert resp.schema["result"] is True
    assert len(resp.schema["data"]) == 9  # 9 fields defined in schema


@patch("telescope.fetchers.kubernetes.client.CoreV1Api")
@patch("telescope.fetchers.kubernetes.client.AppsV1Api")
def test_get_context_field_data_deployment(
    mock_apps_api, mock_core_api, kubernetes_source
):
    """Test getting deployment context field data."""
    mock_apps_instance = MagicMock()
    mock_deployment = MagicMock()
    mock_deployment.metadata.name = "test-deployment"
    mock_deployment.metadata.labels = {"app": "test"}
    mock_deployment.spec.replicas = 3
    mock_deployment.status.ready_replicas = 2
    mock_deployment.status.conditions = []

    mock_apps_instance.list_namespaced_deployment.return_value = MagicMock(
        items=[mock_deployment]
    )
    mock_apps_api.return_value = mock_apps_instance

    kubernetes_source.data = {"namespace": "test-namespace"}

    deployments = Fetcher.get_context_field_data(kubernetes_source, "deployment")
    assert len(deployments) == 1
    assert deployments[0]["name"] == "test-deployment"
    assert deployments[0]["replicas_desired"] == 3
    assert deployments[0]["replicas_ready"] == 2


def test_get_context_field_data_unsupported_fields(kubernetes_source):
    """Test that unsupported fields raise ValueError."""
    kubernetes_source.data = {"namespace": "test-namespace"}

    with pytest.raises(ValueError) as excinfo:
        Fetcher.get_context_field_data(kubernetes_source, "namespace")
    assert "Unsupported context field: namespace" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        Fetcher.get_context_field_data(kubernetes_source, "pod")
    assert "Unsupported context field: pod" in str(excinfo.value)


@patch("telescope.fetchers.kubernetes.config.load_kube_config")
@patch("telescope.fetchers.kubernetes.client.CoreV1Api")
def test_fetch_data_simple(mock_api, mock_load_config, kubernetes_source):
    mock_instance = MagicMock()
    # Mock pod list
    pod = _Pod(
        name="mypod",
        namespace="default",
        containers=[_Container(name="app", image="busybox")],
    )
    mock_instance.list_namespaced_pod.return_value = _PodList(items=[pod])
    # Mock log output (timestamp + message)
    mock_instance.read_namespaced_pod_log.return_value = (
        "2025-01-01T00:00:01Z Log line 1\n2025-01-01T00:00:02Z Log line 2"
    )
    mock_instance.read_namespaced_pod.return_value = pod
    mock_api.return_value = mock_instance

    request = DataRequest(
        source=kubernetes_source,
        query="",
        raw_query="",
        time_from=1000000000000,
        time_to=2000000000000,
        limit=10,
        context_fields={"deployment": []},  # Empty deployment list to fetch all pods
    )
    response = Fetcher.fetch_data(request, tz=UTC_ZONE)
    assert len(response.rows) == 2
    # Verify that the message field is correctly parsed
    assert response.rows[0].data["message"] == "Log line 2"
    assert response.rows[1].data["message"] == "Log line 1"


@patch("telescope.fetchers.kubernetes.config.load_kube_config")
@patch("telescope.fetchers.kubernetes.client.CoreV1Api")
def test_fetch_graph_data_group_by_namespace(
    mock_api, mock_load_config, kubernetes_source
):
    mock_instance = MagicMock()
    pod = _Pod(
        name="podx",
        namespace="ns1",
        containers=[_Container(name="c", image="img")],
    )
    mock_instance.list_namespaced_pod.return_value = _PodList(items=[pod])
    mock_instance.read_namespaced_pod_log.return_value = (
        "2025-01-01T00:00:01Z entry\n2025-01-01T00:00:02Z entry"
    )
    mock_instance.read_namespaced_pod.return_value = pod
    mock_api.return_value = mock_instance

    # Build a dummy ParsedField for grouping (simulating FlyQL field)
    class DummyParsedField:
        def __init__(self, name):
            self.name = name

    request = GraphDataRequest(
        source=kubernetes_source,
        query="",
        raw_query="",
        time_from=1000000000000,
        time_to=2000000000000,
        group_by=[DummyParsedField(name="namespace")],
        context_fields={"deployment": []},  # Empty deployment list to fetch all pods
    )
    graph_resp = Fetcher.fetch_graph_data(request)
    # Two timestamps should be present (including the start/end markers)
    assert len(graph_resp.timestamps) >= 2
    # Data should contain a single group key "ns1"
    assert "ns1" in graph_resp.data
    # Each timestamp bucket should have a count of 2 (two log lines)
    assert sum(graph_resp.data["ns1"]) == 2
