"""P1.3: the CONTEXT tab's "same container" request on Docker and Kubernetes sources, through /data."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from telescope.fetchers.kubernetes.api import LogEntry
from telescope.models import Source
from tests.context.contextjs import context_for
from tests.data import get_docker_source_data, get_kubernetes_source_data

T = datetime(2026, 1, 1, 12, 0, 0, 500000, tzinfo=timezone.utc)
T_MS = int(T.timestamp() * 1000)
AT_T = {"from": T_MS, "to": T_MS}
OFFSETS = [-30, -6, -4.9, -1, 0, 0.1, 4.9, 6, 30]


def post_data(user, source, query, window, context_columns):
    client = APIClient()
    client.force_login(user)
    body = {
        "columns": "body",
        "from": window["from"],
        "to": window["to"],
        "query": query,
        "limit": 500,
        "context_columns": context_columns,
    }
    res = client.post(f"/ui/v1/sources/{source.slug}/data", body, format="json")
    doc = res.json()
    assert doc["result"] and doc["validation"]["result"], doc
    return doc["data"]["rows"]


def column(suggest=True):
    return {
        "display_name": "",
        "type": "string",
        "autocomplete": False,
        "suggest": suggest,
        "jsonstring": False,
        "group_by": False,
        "values": [],
    }


@pytest.fixture
def docker_ctx_source(docker_connection):
    data = get_docker_source_data("docker-ctx")
    del data["kind"], data["connection"]
    names = ["time", "stream", "status", "container_id", "container_short_id"]
    names += ["container_name", "body"]
    data["columns"] = {name: column() for name in names}
    data["columns"]["labels"] = {**column(False), "type": "object"}
    data["default_chosen_columns"] = "container_name, body"
    data["conn"] = docker_connection
    return Source.create(kind="docker", data=data)


def docker_container(name):
    container = MagicMock()
    container.name, container.id, container.short_id = name, f"{name}-id", name[:3]
    container.status, container.labels = "running", {}

    def logs(timestamps, since, until, stdout, stderr):
        if not stdout:
            return b""
        lines = []
        for off in OFFSETS:
            ts = T + timedelta(seconds=off)
            if since <= ts.timestamp() <= until:
                stamp = ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                lines.append(f"{stamp} {name} line {off}")
        return "\n".join(lines).encode()

    container.logs.side_effect = logs
    return container


@pytest.mark.django_db
@patch("telescope.fetchers.docker.docker.DockerClient")
def test_docker_same_container_5s(mock_client, tmp_path, root_user, docker_ctx_source):
    containers = [docker_container("web"), docker_container("db")]
    mock_client.return_value.containers.list.return_value = containers
    selected = {"container": ["web", "db"]}

    rows = post_data(root_user, docker_ctx_source, "", AT_T, selected)
    row = next(r for r in rows if r["data"]["container_name"] == "web")
    ctx = context_for(tmp_path, docker_ctx_source, row, "container", 5000)
    assert "container" in ctx["presets"]
    assert ctx["query"] == "container_name = 'web'"
    assert ctx["window"] == {"from": T_MS - 5000, "to": T_MS + 5000}

    rows = post_data(
        root_user, docker_ctx_source, ctx["query"], ctx["window"], selected
    )
    assert {r["data"]["container_name"] for r in rows} == {"web"}
    assert sorted(r["data"]["body"]["message"] for r in rows) == sorted(
        f"web line {off}" for off in OFFSETS if abs(off) <= 5
    )
    assert row in rows
    for call in mock_client.return_value.containers.list.call_args_list:
        assert call.kwargs["filters"] == {"name": ["web", "db"]}


@pytest.fixture
def k8s_ctx_source(kubernetes_connection):
    data = get_kubernetes_source_data("k8s-ctx")
    del data["kind"], data["connection"]
    data["conn"] = kubernetes_connection
    return Source.create(kind="kubernetes", data=data)


def k8s_entries():
    entries = []
    for pod in ["web-1", "web-2"]:
        for container in ["app", "sidecar"]:
            for off in OFFSETS:
                entries.append(
                    LogEntry(
                        context="prod",
                        namespace="shop",
                        pod=pod,
                        container=container,
                        timestamp=T + timedelta(seconds=off),
                        message=f"{pod}/{container} {off}",
                        node="n1",
                        labels={},
                        annotations={},
                        status="Running",
                    )
                )
    return entries


@pytest.mark.django_db
@pytest.mark.parametrize(
    "preset,expected",
    [
        ("pod", "(context = 'prod') and (namespace = 'shop') and (pod = 'web-1')"),
        (
            "container",
            "(context = 'prod') and (namespace = 'shop') and (pod = 'web-1') and (container = 'app')",
        ),
    ],
)
@patch("telescope.fetchers.kubernetes.fetcher.KubeHelper")
@patch("telescope.fetchers.kubernetes.fetcher.KubeConfigHelper")
def test_kubernetes_same_pod_and_container_5s(
    _config, mock_helper_cls, tmp_path, root_user, k8s_ctx_source, preset, expected
):
    helper = MagicMock()
    helper.contexts = ["prod"]
    helper.namespaces = {"prod": ["shop"]}
    helper.pods = {"prod": {"shop": {"web-1": {}, "web-2": {}}}}
    helper.errors = []
    helper.get_logs.side_effect = lambda since, frm, to: (
        [e for e in k8s_entries() if frm <= e.timestamp <= to],
        [],
    )
    mock_helper_cls.return_value = helper
    selected = {"contexts": ["prod"], "namespaces": ["shop"]}

    rows = post_data(root_user, k8s_ctx_source, "", AT_T, selected)
    row = next(
        r
        for r in rows
        if r["data"]["pod"] == "web-1" and r["data"]["container"] == "app"
    )
    ctx = context_for(tmp_path, k8s_ctx_source, row, preset, 5000)
    assert ctx["query"] == expected

    rows = post_data(root_user, k8s_ctx_source, ctx["query"], ctx["window"], selected)
    want = [e for e in k8s_entries() if abs((e.timestamp - T).total_seconds()) <= 5]
    want = [
        e
        for e in want
        if e.pod == "web-1" and (preset == "pod" or e.container == "app")
    ]
    assert sorted(r["data"]["body"]["message"] for r in rows) == sorted(
        e.message for e in want
    )
    assert row in rows
    assert mock_helper_cls.call_args.kwargs["selected_namespaces"] == ["shop"]
