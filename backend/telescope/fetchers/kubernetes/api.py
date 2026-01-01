import os
import re
import tempfile
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import List, Dict, Set, Callable, TypeVar, Optional, Tuple, Any

from cachetools import LRUCache

from django.core.cache import cache

T = TypeVar("T")

from flyql.core.parser import parse
from flyql.matcher.evaluator import Evaluator
from flyql.matcher.record import Record

from kubernetes.config.kube_config import KubeConfigLoader
from kubernetes import config as kubernetes_config
from kubernetes import client as kubernetes_client

import yaml

logger = logging.getLogger("telescope.fetchers.kubernetes.api")

CACHE_TTL = 30
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


@dataclass
class LogEntry:
    context: str
    namespace: str
    pod: str
    container: str
    timestamp: datetime
    message: str
    node: str = ""
    labels: dict = None
    annotations: dict = None
    status: str = ""


_client_cache: LRUCache = LRUCache(maxsize=100)
_client_cache_lock = Lock()


class KubeHelperError(Exception):
    pass


class KubeConfigHelper:
    def __init__(
        self,
        kubeconfig: str,
        kubeconfig_hash: str,
        is_local: bool = False,
    ):
        self.is_local = is_local
        self.kubeconfig_path = kubeconfig
        self.kubeconfig_hash = kubeconfig_hash
        self.data = {}
        if is_local:
            path = os.path.expanduser(kubeconfig)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Kubeconfig file not found: {path}")
            with open(path, "r") as fd:
                self.data = yaml.safe_load(fd)
        else:
            self.data = yaml.safe_load(kubeconfig)
        self.loader = KubeConfigLoader(config_dict=self.data)

    def list_contexts(self) -> List[Dict]:
        result = []
        for ctx in self.loader.list_contexts():
            result.append(
                {
                    "name": ctx["name"],
                    "cluster": ctx["context"].get("cluster", ""),
                    "user": ctx["context"].get("user", ""),
                    "namespace": ctx["context"].get("namespace", "default"),
                }
            )
        return result


class KubeClient:
    def __init__(
        self, core: kubernetes_client.CoreV1Api, apps: kubernetes_client.AppsV1Api
    ):
        self.core = core
        self.apps = apps


class KubeClientHelper:
    def __init__(self, config: KubeConfigHelper):
        self.config = config
        self._temp_file = None
        self._config_path = None

    def _get_cache_key(self, context_name: str) -> str:
        return f"{self.config.kubeconfig_hash}:{context_name}"

    def _get_config_path(self) -> str:
        if self._config_path is not None:
            return self._config_path

        if self.config.is_local:
            self._config_path = os.path.expanduser(self.config.kubeconfig_path)
        else:
            self._temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".yaml",
                prefix="kubeconfig_",
                delete=False,
            )
            yaml.safe_dump(self.config.data, self._temp_file)
            self._temp_file.close()
            self._config_path = self._temp_file.name

        return self._config_path

    def get_client_for_context(self, context_name: str) -> KubeClient:
        cache_key = self._get_cache_key(context_name)
        with _client_cache_lock:
            client = _client_cache.get(cache_key)
            if client is not None:
                return client

            config_path = self._get_config_path()
            kubernetes_config.load_kube_config(
                config_file=config_path, context=context_name
            )
            cfg = kubernetes_client.Configuration.get_default_copy()
            api_client = kubernetes_client.ApiClient(cfg)
            apps = kubernetes_client.AppsV1Api(api_client)
            core = kubernetes_client.CoreV1Api(api_client)
            client = KubeClient(core, apps)
            _client_cache[cache_key] = client
            return client

    def cleanup(self):
        if self._temp_file is not None:
            try:
                os.unlink(self._temp_file.name)
            except Exception as e:
                logger.warning("Failed to cleanup temp kubeconfig: %s", e)
            self._temp_file = None
            self._config_path = None

    def __del__(self):
        self.cleanup()


class KubeHelper:
    def __init__(
        self,
        conn_id: int,
        source_id: int,
        max_concurrent_requests: int,
        config: KubeConfigHelper,
        context_flyql_filter: str = "",
        namespace_label_selector: str = "",
        namespace_field_selector: str = "",
        namespace_flyql_filter: str = "",
        pods_label_selector: str = "",
        pods_field_selector: str = "",
        pods_flyql_filter: str = "",
        selected_contexts: List[str] = [],
        selected_namespaces: List[str] = [],
    ):
        self.conn_id = conn_id
        self.source_id = source_id
        self.max_concurrent_requests = max_concurrent_requests
        self.config = config
        self.context_flyql_filter = context_flyql_filter
        self.namespace_label_selector = namespace_label_selector
        self.namespace_field_selector = namespace_field_selector
        self.namespace_flyql_filter = namespace_flyql_filter
        self.pods_label_selector = pods_label_selector
        self.pods_field_selector = pods_field_selector
        self.pods_flyql_filter = pods_flyql_filter
        self.selected_contexts = set(selected_contexts)
        self.selected_namespaces = set(selected_namespaces)

        self.context_flyql_filter_ast = None
        self.namespace_flyql_filter_ast = None
        self.pods_flyql_filter_ast = None
        self.flyql_evaluator = Evaluator()

        self.client_helper = KubeClientHelper(self.config)

        if self.context_flyql_filter:
            self.context_flyql_filter_ast = parse(self.context_flyql_filter).root
        if self.namespace_flyql_filter:
            self.namespace_flyql_filter_ast = parse(self.namespace_flyql_filter).root
        if self.pods_flyql_filter:
            self.pods_flyql_filter_ast = parse(self.pods_flyql_filter).root

        self.contexts_cache_key = self._make_cache_key(
            "k8s_contexts",
            self.conn_id,
            self.source_id,
            self.context_flyql_filter,
            self.config.kubeconfig_hash,
        )
        self.namespaces_cache_key = self._make_cache_key(
            "k8s_namespaces",
            self.conn_id,
            self.source_id,
            self.namespace_label_selector,
            self.namespace_field_selector,
            self.namespace_flyql_filter,
            self.config.kubeconfig_hash,
        )
        self.pods_cache_key = self._make_cache_key(
            "k8s_pods",
            self.conn_id,
            self.source_id,
            self.namespace_label_selector,
            self.namespace_field_selector,
            self.namespace_flyql_filter,
            self.pods_label_selector,
            self.pods_field_selector,
            self.pods_flyql_filter,
            self.config.kubeconfig_hash,
        )
        self._contexts = None
        self._namespaces = None
        self._pods = None
        self._allowed_contexts = None
        self._allowed_contexts_set = None
        self._validation_called = False
        self.errors = []

    @staticmethod
    def _make_cache_key(*args) -> str:
        key_str = ":".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()

    @property
    def allowed_contexts(self) -> List[str]:
        if self._allowed_contexts is None:
            cached = cache.get(self.contexts_cache_key)
            if cached is not None:
                self._allowed_contexts = cached
            else:
                contexts = self.config.list_contexts()
                matched = []
                if self.context_flyql_filter_ast is not None:
                    for context in contexts:
                        if self.flyql_evaluator.evaluate(
                            self.context_flyql_filter_ast, Record(data=context)
                        ):
                            matched.append(context)
                    self._allowed_contexts = matched
                else:
                    self._allowed_contexts = contexts
                cache.set(self.contexts_cache_key, self._allowed_contexts, CACHE_TTL)
        return self._allowed_contexts

    @property
    def allowed_contexts_set(self) -> Set[str]:
        if self._allowed_contexts_set is None:
            self._allowed_contexts_set = set([c["name"] for c in self.allowed_contexts])
        return self._allowed_contexts_set

    @property
    def contexts(self) -> Set[str]:
        if self.selected_contexts and not self._validation_called:
            raise ValueError(
                "validation should be called when specific contexts are selected"
            )
        return self.selected_contexts or self.allowed_contexts_set

    def _get_all_namespaces(self) -> Dict[str, List[str]]:
        cached = cache.get(self.namespaces_cache_key)
        if cached is not None:
            return cached

        all_namespaces, errors = self.get_namespaces()
        if errors:
            logger.warning("Namespace fetch errors: %s", errors)
            self.store_error("get_namespaces", "warn", errors)
        else:
            cache.set(self.namespaces_cache_key, all_namespaces, CACHE_TTL)
        return all_namespaces

    @property
    def namespaces(self):
        if self._namespaces is None:
            all_namespaces = self._get_all_namespaces()
            filtered_by_ctx = {
                ctx: ns for ctx, ns in all_namespaces.items() if ctx in self.contexts
            }
            if self.selected_namespaces:
                self._namespaces = {
                    ctx: [n for n in ns if n in self.selected_namespaces]
                    for ctx, ns in filtered_by_ctx.items()
                }
            else:
                self._namespaces = filtered_by_ctx
        return self._namespaces

    def store_error(self, operation: str, sev: str, data: Dict[str, Any]):
        self.errors.append({"operation": operation, "sev": sev, "data": data})

    def get_namespaces(self) -> Tuple[Dict[str, T], Dict[str, Exception]]:
        return self.execute_parallel(
            self.get_namespaces_from_client,
            max_workers=50,
            contexts=self.allowed_contexts_set,
        )

    def get_namespaces_from_client(self, client: KubeClient) -> List[str]:
        result = []
        namespaces = client.core.list_namespace(
            field_selector=self.namespace_field_selector,
            label_selector=self.namespace_label_selector,
        )
        for ns in namespaces.items:
            if self.namespace_flyql_filter_ast:
                ns_dict = ns.to_dict()
                if self.flyql_evaluator.evaluate(
                    self.namespace_flyql_filter_ast, Record(data=ns_dict)
                ):
                    result.append(ns.metadata.name)
            else:
                result.append(ns.metadata.name)
        return result

    @property
    def pods(self):
        if self._pods is None:
            cached = cache.get(self.pods_cache_key)
            if cached is not None:
                all_pods = cached
            else:
                all_pods, errors = self.get_pods()
                if not errors:
                    cache.set(self.pods_cache_key, all_pods, CACHE_TTL)
                else:
                    self.store_error("get_pods", "warn", errors)
            filtered_by_ctx = {
                ctx: pods for ctx, pods in all_pods.items() if ctx in self.contexts
            }
            if self.selected_namespaces:
                self._pods = {
                    ctx: {
                        ns: pods_in_ns
                        for ns, pods_in_ns in namespaces.items()
                        if ns in self.selected_namespaces
                    }
                    for ctx, namespaces in filtered_by_ctx.items()
                }
            else:
                self._pods = filtered_by_ctx
        return self._pods

    def get_pods(
        self,
    ) -> Tuple[Dict[str, Dict[str, Dict[str, Dict]]], Dict[str, Any]]:

        results: Dict[str, Dict[str, Dict[str, Dict]]] = {}
        errors: Dict[str, Any] = {}

        all_namespaces = self._get_all_namespaces()

        def get_pods_for_context(
            context_name: str,
        ) -> Tuple[Dict[str, Dict[str, Dict]], Dict[str, Exception]]:
            namespaces = all_namespaces.get(context_name, [])
            client = self.client_helper.get_client_for_context(context_name)
            return self._get_pods_for_namespaces(client, namespaces)

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_context = {
                executor.submit(get_pods_for_context, ctx): ctx
                for ctx in all_namespaces.keys()
            }
            for future in as_completed(future_to_context):
                ctx = future_to_context[future]
                try:
                    ctx_results, ctx_errors = future.result()
                    results[ctx] = ctx_results
                    if ctx_errors:
                        errors[ctx] = ctx_errors
                except Exception as e:
                    errors[ctx] = e

        return results, errors

    def _get_pods_for_namespaces(
        self, client: KubeClient, namespaces: List[str]
    ) -> Tuple[Dict[str, Dict[str, Dict]], Dict[str, Exception]]:
        results: Dict[str, Dict[str, Dict]] = {}
        errors: Dict[str, Exception] = {}

        def get_pods_for_namespace(ns: str) -> Tuple[str, Dict[str, Dict]]:
            pods: Dict[str, Dict] = {}
            for pod in client.core.list_namespaced_pod(
                namespace=ns,
                field_selector=self.pods_field_selector,
                label_selector=self.pods_label_selector,
            ).items:
                if self.pods_flyql_filter_ast:
                    pod_dict = pod.to_dict()
                    if not self.flyql_evaluator.evaluate(
                        self.pods_flyql_filter_ast, Record(data=pod_dict)
                    ):
                        continue
                pods[pod.metadata.name] = {
                    "containers": [c.name for c in pod.spec.containers],
                    "status": pod.status.phase,
                    "node": pod.spec.node_name or "",
                    "labels": pod.metadata.labels or {},
                    "annotations": pod.metadata.annotations or {},
                }
            return ns, pods

        with ThreadPoolExecutor(max_workers=self.max_concurrent_requests) as executor:
            future_to_ns = {
                executor.submit(get_pods_for_namespace, ns): ns for ns in namespaces
            }
            for future in as_completed(future_to_ns):
                ns = future_to_ns[future]
                try:
                    _, pods = future.result()
                    results[ns] = pods
                except Exception as e:
                    errors[ns] = e

        return results, errors

    def validate(self):
        if not self.allowed_contexts_set:
            raise KubeHelperError("No contexts available for this connection")

        invalid_contexts = set(
            [
                name
                for name in self.selected_contexts
                if name not in self.allowed_contexts_set
            ]
        )
        if invalid_contexts:
            raise KubeHelperError(
                f"Invalid contexts: {', '.join(invalid_contexts)}. These contexts are not available for this connection."
            )

        self._validation_called = True

    def execute_parallel(
        self,
        func: Callable[[KubeClient], T],
        max_workers: Optional[int] = None,
        contexts: Optional[Set[str]] = None,
    ) -> Tuple[Dict[str, T], Dict[str, Exception]]:

        results: Dict[str, T] = {}
        errors: Dict[str, Exception] = {}

        def wrapper(context_name: str) -> T:
            client = self.client_helper.get_client_for_context(context_name)
            return func(client)

        if max_workers is None:
            max_workers = self.max_concurrent_requests

        if contexts is None:
            contexts = self.contexts

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_context = {executor.submit(wrapper, ctx): ctx for ctx in contexts}

            for future in as_completed(future_to_context):
                ctx = future_to_context[future]
                try:
                    results[ctx] = future.result()
                except Exception as e:
                    errors[ctx] = e

        return results, errors

    def get_logs(
        self,
        since_seconds: int,
        time_from: datetime,
        time_to: datetime,
        tail_lines: int = 0,
    ) -> Tuple[List[LogEntry], Dict[str, Any]]:
        all_logs: List[LogEntry] = []
        errors: Dict[str, Any] = {}

        def get_logs_for_context(
            context_name: str,
        ) -> Tuple[List[LogEntry], Dict[str, Exception]]:
            pods_by_ns = self.pods.get(context_name, {})
            client = self.client_helper.get_client_for_context(context_name)
            return self._get_logs_for_context(
                client,
                context_name,
                pods_by_ns,
                since_seconds,
                time_from,
                time_to,
                tail_lines,
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_context = {
                executor.submit(get_logs_for_context, ctx): ctx
                for ctx in self.pods.keys()
            }
            for future in as_completed(future_to_context):
                ctx = future_to_context[future]
                try:
                    ctx_logs, ctx_errors = future.result()
                    all_logs.extend(ctx_logs)
                    if ctx_errors:
                        errors[ctx] = ctx_errors
                except Exception as e:
                    errors[ctx] = e

        return all_logs, errors

    def _get_logs_for_context(
        self,
        client: KubeClient,
        context_name: str,
        pods_by_ns: Dict[str, Dict[str, Dict]],
        since_seconds: int,
        time_from: datetime,
        time_to: datetime,
        tail_lines: int = 0,
    ) -> Tuple[List[LogEntry], Dict[str, Exception]]:
        all_logs: List[LogEntry] = []
        errors: Dict[str, Exception] = {}

        fetch_tasks = []
        for namespace, pods in pods_by_ns.items():
            for pod_name, pod_data in pods.items():
                for container in pod_data.get("containers", []):
                    fetch_tasks.append((namespace, pod_name, container, pod_data))

        def fetch_container_logs(
            namespace: str, pod_name: str, container: str, pod_data: Dict
        ) -> Tuple[str, str, str, List[LogEntry]]:
            entries = self._fetch_single_container_logs(
                client,
                context_name,
                namespace,
                pod_name,
                container,
                pod_data,
                since_seconds,
                time_from,
                time_to,
                tail_lines,
            )
            return namespace, pod_name, container, entries

        with ThreadPoolExecutor(max_workers=self.max_concurrent_requests) as executor:
            future_to_task = {
                executor.submit(fetch_container_logs, ns, pod, cont, pod_data): (
                    ns,
                    pod,
                    cont,
                )
                for ns, pod, cont, pod_data in fetch_tasks
            }
            for future in as_completed(future_to_task):
                ns, pod, cont = future_to_task[future]
                try:
                    _, _, _, entries = future.result()
                    all_logs.extend(entries)
                except Exception as e:
                    error_key = f"{ns}/{pod}/{cont}"
                    errors[error_key] = e

        return all_logs, errors

    def _fetch_single_container_logs(
        self,
        client: KubeClient,
        context_name: str,
        namespace: str,
        pod_name: str,
        container: str,
        pod_data: Dict,
        since_seconds: int,
        time_from: datetime,
        time_to: datetime,
        tail_lines: int = 0,
    ) -> List[LogEntry]:
        entries = []

        node = pod_data.get("node", "")
        labels = pod_data.get("labels", {})
        annotations = pod_data.get("annotations", {})
        status = pod_data.get("status", "")

        log_params = {
            "name": pod_name,
            "namespace": namespace,
            "container": container,
            "timestamps": True,
        }
        if since_seconds > 0:
            log_params["since_seconds"] = since_seconds
        if tail_lines > 0:
            log_params["tail_lines"] = tail_lines

        try:
            raw_logs = client.core.read_namespaced_pod_log(**log_params)
            if not raw_logs and status in ("Succeeded", "Failed", "Error"):
                log_params["previous"] = True
                raw_logs = client.core.read_namespaced_pod_log(**log_params)

            if not raw_logs:
                return entries

            for line in raw_logs.splitlines():
                if not line:
                    continue

                parts = line.split(" ", 1)
                ts = self._parse_k8s_timestamp(parts[0])
                if not ts:
                    continue

                if ts < time_from or ts > time_to:
                    continue

                message = parts[1] if len(parts) > 1 else ""
                message = ANSI_ESCAPE.sub("", message)

                if message:
                    entries.append(
                        LogEntry(
                            context=context_name,
                            namespace=namespace,
                            pod=pod_name,
                            container=container,
                            timestamp=ts,
                            message=message,
                            node=node,
                            labels=labels,
                            annotations=annotations,
                            status=status,
                        )
                    )

        except Exception as e:
            logger.error(
                "Error fetching logs for %s/%s/%s/%s: %s",
                context_name,
                namespace,
                pod_name,
                container,
                e,
            )

        return entries

    @staticmethod
    def _parse_k8s_timestamp(timestamp_str: str) -> Optional[datetime]:
        try:
            from telescope.constants import UTC_ZONE

            year = int(timestamp_str[0:4])
            month = int(timestamp_str[5:7])
            day = int(timestamp_str[8:10])
            hour = int(timestamp_str[11:13])
            minute = int(timestamp_str[14:16])
            second = int(timestamp_str[17:19])

            if len(timestamp_str) > 19 and timestamp_str[19] == ".":
                frac_raw = timestamp_str[20:-1]
                micros = int((frac_raw[:6]).ljust(6, "0"))
            else:
                micros = 0

            return datetime(year, month, day, hour, minute, second, micros, UTC_ZONE)
        except (ValueError, AttributeError, IndexError):
            return None

    def get_deployments(self) -> List[Dict]:
        all_deployments = []

        def get_deployments_for_client(client: KubeClient) -> List[Dict]:
            return self._get_deployments_from_client(client)

        results, errors = self.execute_parallel(get_deployments_for_client)

        for ctx, deployments in results.items():
            all_deployments.extend(deployments)

        if errors:
            self.store_error("get_deployments", "warn", errors)

        return sorted(all_deployments, key=lambda d: (d["namespace"], d["name"]))

    def _get_deployments_from_client(self, client: KubeClient) -> List[Dict]:
        deployments = []

        namespaces = self.get_namespaces_from_client(client)

        for namespace in namespaces:
            try:
                deployment_list = client.apps.list_namespaced_deployment(
                    namespace=namespace
                )
                for deployment in deployment_list.items:
                    status = "Unknown"
                    if deployment.status.conditions:
                        for condition in deployment.status.conditions:
                            if (
                                condition.type == "Available"
                                and condition.status == "True"
                            ):
                                status = "Available"
                                break
                            elif (
                                condition.type == "Progressing"
                                and condition.status == "True"
                            ):
                                status = "Progressing"
                            elif (
                                condition.type == "ReplicaFailure"
                                and condition.status == "True"
                            ):
                                status = "Failed"

                    deployments.append(
                        {
                            "name": deployment.metadata.name,
                            "namespace": namespace,
                            "replicas_desired": deployment.spec.replicas or 0,
                            "replicas_ready": deployment.status.ready_replicas or 0,
                            "status": status,
                            "labels": deployment.metadata.labels or {},
                        }
                    )
            except Exception as e:
                logger.error(
                    "Error listing deployments in namespace %s: %s", namespace, e
                )

        return deployments

    def test_connection(self) -> bool:
        if not self.allowed_contexts:
            raise KubeHelperError("No contexts available")

        first_context = self.allowed_contexts[0]["name"]
        client = self.client_helper.get_client_for_context(first_context)
        client.core.list_namespace()
        return True
