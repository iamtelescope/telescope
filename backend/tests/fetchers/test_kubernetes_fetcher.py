import json
import unittest
from unittest.mock import patch, MagicMock

from telescope.fetchers.kubernetes import Fetcher
from telescope.fetchers.request import DataRequest, GraphDataRequest
from telescope.models import Source

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
    def __init__(self, name, namespace, containers, status=None, node_name="node-1", labels=None):
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

class DummySource:
    """A minimal Source-like class for testing that doesn't inherit from Django model."""
    def __init__(self, conn_data):
        # Mock the attributes needed by the fetcher
        self.conn = MagicMock()
        self.conn.data = conn_data
        self.time_field = "time"
        self._fields = {
            "time": MagicMock(type="datetime"),
            "namespace": MagicMock(),
            "pod_name": MagicMock(),
            "deployment": MagicMock(),
            "node_name": MagicMock(),
            "labels": MagicMock(),
            "message": MagicMock(),
            "stream": MagicMock(),
            "status": MagicMock(),
        }
        self._record_pseudo_id_field = "id"
        self.uniq_field = "id"

class TestKubernetesFetcher(unittest.TestCase):
    def setUp(self):
        # Sample connection data for kubeconfig mode
        self.conn_data = {
            "mode": "kubeconfig",
            "kubeconfig": "apiVersion: v1\nclusters: []\ncontexts: []\nusers: []",
        }
        self.source = DummySource(self.conn_data)

    @patch("telescope.fetchers.kubernetes.client.CoreV1Api")
    def test_connection_success(self, mock_api):
        mock_instance = MagicMock()
        mock_instance.list_namespace.return_value = _NamespaceList(items=[])
        mock_api.return_value = mock_instance

        resp = Fetcher.test_connection(self.conn_data)
        self.assertTrue(resp.reachability["result"])
        self.assertTrue(resp.schema["result"])
        self.assertEqual(len(resp.schema["data"]), 10)  # 10 fields defined in schema

    @patch("telescope.fetchers.kubernetes.client.CoreV1Api")
    def test_get_context_namespaces(self, mock_api):
        mock_instance = MagicMock()
        mock_instance.list_namespace.return_value = _NamespaceList(
            items=[_Meta(name="default"), _Meta(name="kube-system")]
        )
        mock_api.return_value = mock_instance

        namespaces = Fetcher.get_context_field_data(self.source, "namespace")
        self.assertListEqual(sorted(namespaces), ["default", "kube-system"])

    @patch("telescope.fetchers.kubernetes.client.CoreV1Api")
    def test_get_context_pods(self, mock_api):
        mock_instance = MagicMock()
        pod1 = _Pod(
            name="pod-1",
            namespace="default",
            containers=[_Container(name="c1")],
            labels={"app": "demo"},
        )
        pod2 = _Pod(
            name="pod-2",
            namespace="default",
            containers=[_Container(name="c2")],
            status=_Status(phase="Pending"),
        )
        mock_instance.list_namespaced_pod.return_value = _PodList(items=[pod1, pod2])
        mock_api.return_value = mock_instance

        # Simulate that the source connection data includes the namespace filter
        self.source.conn.data["namespaces"] = ["default"]
        pods = Fetcher.get_context_field_data(self.source, "pod")
        self.assertEqual(len(pods), 2)
        self.assertEqual(pods[0]["status"], "Pending")  # sorted by status

    @patch("telescope.fetchers.kubernetes.client.CoreV1Api")
    def test_fetch_data_simple(self, mock_api):
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
        mock_api.return_value = mock_instance

        request = DataRequest(
            source=self.source,
            query="",
            raw_query="",
            time_from=0,
            time_to=10_000,
            limit=10,
            context_fields={"namespace": ["default"]},
        )
        response = Fetcher.fetch_data(request, tz="UTC")
        self.assertEqual(len(response.rows), 2)
        # Verify that the message field is correctly parsed
        self.assertEqual(response.rows[0].data["message"], "Log line 2")
        self.assertEqual(response.rows[1].data["message"], "Log line 1")

    @patch("telescope.fetchers.kubernetes.client.CoreV1Api")
    def test_fetch_graph_data_group_by_namespace(self, mock_api):
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
        mock_api.return_value = mock_instance

        # Build a dummy ParsedField for grouping (simulating FlyQL field)
        class DummyParsedField:
            def __init__(self, name):
                self.name = name

        request = GraphDataRequest(
            source=self.source,
            query="",
            raw_query="",
            time_from=0,
            time_to=10_000,
            group_by=[DummyParsedField(name="namespace")],
            context_fields={"namespace": ["ns1"]},
        )
        graph_resp = Fetcher.fetch_graph_data(request)
        # Two timestamps should be present (including the start/end markers)
        self.assertTrue(len(graph_resp.timestamps) >= 2)
        # Data should contain a single group key "ns1"
        self.assertIn("ns1", graph_resp.data)
        # Each timestamp bucket should have a count of 2 (two log lines)
        self.assertEqual(sum(graph_resp.data["ns1"]), 2)

if __name__ == "__main__":
    unittest.main()