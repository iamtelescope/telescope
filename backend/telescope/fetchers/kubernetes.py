import json
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from telescope.constants import UTC_ZONE

from kubernetes import client, config

from flyql.core.parser import parse, ParserError
from flyql.core.exceptions import FlyqlError
from flyql.matcher.evaluator import Evaluator
from flyql.matcher.record import Record

from telescope.utils import get_telescope_field
from telescope.fetchers.request import (
    AutocompleteRequest,
    DataRequest,
    GraphDataRequest,
)
from telescope.fetchers.response import (
    AutocompleteResponse,
    DataResponse,
    GraphDataResponse,
)
from telescope.fetchers.fetcher import BaseFetcher
from telescope.fetchers.models import Row

from django.conf import settings

logger = logging.getLogger("telescope.fetchers.kubernetes")

def parse_k8s_timestamp(timestamp_str, tz):
    try:
        year   = int(timestamp_str[0:4])
        month  = int(timestamp_str[5:7])
        day    = int(timestamp_str[8:10])
        hour   = int(timestamp_str[11:13])
        minute = int(timestamp_str[14:16])
        second = int(timestamp_str[17:19])

        if timestamp_str[19] == '.':
            frac_raw = timestamp_str[20:-1]
            micros   = int((frac_raw[:6]).ljust(6, '0'))
        else:
            micros = 0
        return datetime(year, month, day, hour, minute, second, micros, UTC_ZONE)
    except (ValueError, AttributeError):
        return None

class ConnectionTestResponseNg:
    def __init__(self):
        self.result = False
        self.error = ""

    def as_dict(self) -> dict:
        return {"result": self.result, "error": self.error}


class ConnectionTestResponse:
    def __init__(self):
        self.reachability = {"result": False, "error": ""}
        self.schema = {"result": False, "error": "", "data": []}

    def as_dict(self) -> dict:
        return {"reachability": self.reachability, "schema": self.schema}


class KubernetesClient:
    _config_cache = {}  # Class-level cache shared across all instances
    
    def __init__(self, data: dict):
        self.data = data
        self._core = None
        self._apps = None
        self._temp_dir = None
        self._key = data["kubeconfig_hash"]

    @property
    def core(self):
        if self._core is None:
            logger.debug("Lazy-initializing CoreV1Api for KubernetesClient.")
            cfg = self._load_config()
            self._init_clients(cfg)
        return self._core

    @property
    def apps(self):
        if self._apps is None:
            logger.debug("Lazy-initializing AppsV1Api for KubernetesClient.")
            cfg = self._load_config()
            self._init_clients(cfg)
        return self._apps

    def _load_config(self, force_reload=False):
        """Load or reuse cached Kubernetes config."""
        if not force_reload and self._key in self._config_cache:
            return self._config_cache[self._key]

        # Determine source
        if self.data.get("kubeconfig_is_local"):
            path = self.data["kubeconfig"]
        else:
            self._temp_dir = tempfile.TemporaryDirectory()
            path = f"{self._temp_dir.name}/kubeconfig.yaml"
            with open(path, "w") as fd:
                fd.write(self.data["kubeconfig"])

        # Load config from file
        try:
            config.load_kube_config(config_file=path)
            cfg = client.Configuration.get_default_copy()
            self._config_cache[self._key] = cfg
        finally:
            # Clean temp dir immediately if not local
            if not self.data.get("kubeconfig_is_local") and self._temp_dir:
                try:
                    self._temp_dir.cleanup()
                except Exception as err:
                    logger.warning("Failed to cleanup temp dir: %s", err)
                self._temp_dir = None

        return cfg
    def _init_clients(self, cfg):
        api_client = client.ApiClient(cfg)
        self._core = client.CoreV1Api(api_client)
        self._apps = client.AppsV1Api(api_client)

    def __enter__(self):
        cfg = self._load_config()
        self._init_clients(cfg)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Fetcher(BaseFetcher):
    @classmethod
    def validate_query(cls, source, query):
        if not query:
            return True, None
        try:
            parser = parse(query)
        except ParserError as err:
            return False, err.message
        else:
            try:
                return True, None
            except FlyqlError as err:
                return False, err.message

    @classmethod
    def get_context_field_data(cls, source, field):
        if field == "deployment":
            namespace = source.data.get("namespace")
            if not namespace:
                raise ValueError("Namespace is required in source configuration")
            
            with KubernetesClient(source.conn.data) as client:
                deployments = []
                try:
                    deployment_list = client.apps.list_namespaced_deployment(namespace=namespace)
                    for deployment in deployment_list.items:
                        status = "Unknown"
                        if deployment.status.conditions:
                            for condition in deployment.status.conditions:
                                if condition.type == "Available" and condition.status == "True":
                                    status = "Available"
                                    break
                                elif condition.type == "Progressing" and condition.status == "True":
                                    status = "Progressing"
                                elif condition.type == "ReplicaFailure" and condition.status == "True":
                                    status = "Failed"
                        
                        deployments.append({
                            "name": deployment.metadata.name,
                            "replicas_desired": deployment.spec.replicas or 0,
                            "replicas_ready": deployment.status.ready_replicas or 0,
                            "status": status,
                            "labels": deployment.metadata.labels or {},
                        })
                except Exception as err:
                    logger.error(f"Error listing deployments: {err}")
                    raise ValueError(f"Failed to list deployments: {err}")
                
                return sorted(deployments, key=lambda d: d["name"])
        else:
            raise ValueError(f"Unsupported context field: {field}")

    @classmethod
    def test_connection_ng(cls, data: dict) -> ConnectionTestResponseNg:
        response = ConnectionTestResponseNg()
        try:
            with KubernetesClient(data) as client:
                client.core.list_namespace()
        except Exception as err:
            response.error = str(err)
        else:
            response.result = True
        return response

    @classmethod
    def get_schema(cls, data: dict):
        return [
            get_telescope_field("time", "datetime"),
            get_telescope_field("namespace", "string"),
            get_telescope_field("pod_name", "string"),
            get_telescope_field("container_name", "string"),
            get_telescope_field("node_name", "string"),
            get_telescope_field("labels", "string"),
            get_telescope_field("message", "string"),
            get_telescope_field("stream", "string"),
            get_telescope_field("status", "string"),
        ]

    @classmethod
    def test_connection(cls, data: dict) -> ConnectionTestResponse:
        response = ConnectionTestResponse()
        try:
            with KubernetesClient(data) as client:
                client.core.list_namespace()
        except Exception as err:
            response.reachability["error"] = str(err)
        else:
            response.reachability["result"] = True

        try:
            response.schema["result"] = True
            response.schema["data"] = cls.get_schema(data)
        except Exception as err:
            response.schema["error"] = str(err)
        return response

    @classmethod
    def autocomplete(cls, source, field, time_from, time_to, value):
        return AutocompleteResponse(items=[], incomplete=False)

    @staticmethod
    def remove_ansi_escape_codes(text):
        import re

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    @classmethod
    def get_pods_for_deployments(cls, client, namespace, selected_deployments):
        if not selected_deployments:
            return []
            
        pods = []
        
        try:
            deployment_list = client.apps.list_namespaced_deployment(namespace=namespace)
        except Exception as err:
            logger.error(f"Error listing deployments: {err}")
            return []
        
        for deployment in deployment_list.items:
            if deployment.metadata.name not in selected_deployments:
                continue
                
            selector = deployment.spec.selector.match_labels
            if selector:
                label_selector_str = ",".join(f"{k}={v}" for k, v in selector.items())
                
                try:
                    dep_pods = client.core.list_namespaced_pod(
                        namespace=namespace,
                        label_selector=label_selector_str
                    ).items
                    pods.extend(dep_pods)
                except Exception as err:
                    logger.error(f"Error fetching pods for deployment {deployment.metadata.name}: {err}")
        
        seen_names = set()
        unique_pods = []
        for pod in pods:
            if pod.metadata.name not in seen_names:
                seen_names.add(pod.metadata.name)
                unique_pods.append(pod)
        
        return unique_pods

    @classmethod
    def has_previous_container(cls, pod, container_name):
        if not pod.status or not pod.status.container_statuses:
            return False
        
        for container_status in pod.status.container_statuses:
            if container_status.name == container_name:
                return (
                    container_status.last_state and
                    container_status.last_state.terminated and
                    container_status.last_state.terminated.finished_at
                )
        return False

    @classmethod
    def fetch_container_logs_with_previous(cls, client, namespace, pod_name, container_name, log_params):
        logs = []
        
        try:
            current_params = log_params.copy()
            current_params["previous"] = False
            current_logs = client.core.read_namespaced_pod_log(**current_params)
            if current_logs:
                logs.append(("current", current_logs))
        except client.exceptions.ApiException as e:
            if e.status not in [403, 404]:
                logger.error(f"Error fetching current logs for {namespace}/{pod_name}/{container_name}: {e}")
        
        try:
            pod = client.core.read_namespaced_pod(name=pod_name, namespace=namespace)
            if cls.has_previous_container(pod, container_name):
                previous_params = log_params.copy()
                previous_params["previous"] = True
                previous_logs = client.core.read_namespaced_pod_log(**previous_params)
                if previous_logs:
                    logs.append(("previous", previous_logs))
        except client.exceptions.ApiException as e:
            if e.status not in [403, 404]:
                logger.error(f"Error fetching previous logs for {namespace}/{pod_name}/{container_name}: {e}")
        except Exception as err:
            logger.error(f"Error checking container status for {namespace}/{pod_name}/{container_name}: {err}")
        
        return logs

    @classmethod
    def fetch_data(cls, request: DataRequest, tz):
        rows = []
        with KubernetesClient(request.source.conn.data) as client:
            time_from_dt = datetime.fromtimestamp(request.time_from / 1000, tz)
            time_to_dt = datetime.fromtimestamp(request.time_to / 1000, tz)

            namespace = request.source.data.get("namespace")
            if not namespace:
                raise ValueError("Namespace is required in source configuration")

            evaluator = Evaluator()
            root = None
            if request.query:
                parser = parse(request.query)
                root = parser.root

            selected_deployments = request.context_fields.get("deployment", [])
            
            if selected_deployments:
                filtered_pods = cls.get_pods_for_deployments(client, namespace, selected_deployments)
            else:
                filtered_pods = client.core.list_namespaced_pod(namespace=namespace).items

            fetch_tasks = []
            total_pods = len(filtered_pods)
            for pod in filtered_pods:
                for container in pod.spec.containers:
                    fetch_tasks.append((pod, container))

            def fetch_container_logs(pod, container):
                pod_name = pod.metadata.name
                pod_status = pod.status.phase
                node_name = pod.spec.node_name or ""
                labels = json.dumps(pod.metadata.labels or {})
                container_name = container.name
                container_rows = []
                
                try:
                    since_seconds = int((datetime.now(tz) - time_from_dt).total_seconds())
                    if since_seconds < 0:
                        since_seconds = 0
                    base_tail = request.limit
                    if request.limit > 100 and total_pods > 1:
                        base_tail = int(max(1, (request.limit / total_pods) * 1.3))
                    
                    log_params = {
                        "name": pod_name,
                        "namespace": namespace,
                        "container": container_name,
                        "timestamps": True,
                        "tail_lines": base_tail,
                    }
                    
                    if since_seconds > 0:
                        log_params["since_seconds"] = since_seconds
                    
                    log_sources = cls.fetch_container_logs_with_previous(client, namespace, pod_name, container_name, log_params)
                    
                except client.exceptions.ApiException as e:
                    if e.status == 403:
                        logger.error(f"RBAC error: Insufficient permissions for {namespace}/{pod_name}/{container_name}")
                    elif e.status == 404:
                        logger.warning(f"Resource not found: {namespace}/{pod_name}/{container_name}")
                    else:
                        logger.error(f"Log fetch error {namespace}/{pod_name}/{container_name}: {e}")
                    return container_rows
                except Exception as err:
                    logger.error(
                        "Log fetch error %s/%s/%s: %s",
                        namespace,
                        pod_name,
                        container_name,
                        err,
                    )
                    return container_rows

                for log_type, logs in log_sources:
                    for line in logs.splitlines():
                        if not line:
                            continue
                        parts = line.split(" ", 1)
                        
                        ts = parse_k8s_timestamp(parts[0], tz)
                        if not ts:
                            continue
                        
                        if ts < time_from_dt or ts > time_to_dt:
                            continue
                        
                        message = parts[1] if len(parts) > 1 else ""
                        message = cls.remove_ansi_escape_codes(message)
                        
                        if log_type == "previous" and message:
                            message = f"[PREVIOUS CONTAINER] {message}"
                        
                        if message:
                            row = Row(
                                source=request.source,
                                selected_fields=[
                                    "time",
                                    "namespace",
                                    "pod_name",
                                    "container_name",
                                    "node_name",
                                    "labels",
                                    "message",
                                    "stream",
                                    "status",
                                ],
                                values=[
                                    ts,
                                    namespace,
                                    pod_name,
                                    container_name,
                                    node_name,
                                    labels,
                                    message,
                                    "stdout",
                                    pod_status,
                                ],
                                tz=tz,
                            )
                            if not root:
                                container_rows.append(row)
                            else:
                                if evaluator.evaluate(root, Record(data=row.data)):
                                    container_rows.append(row)
                
                return container_rows
            
            with ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_REQUESTS) as executor:
                futures = {
                    executor.submit(fetch_container_logs, pod, container): (pod, container)
                    for pod, container in fetch_tasks
                }
                
                for future in as_completed(futures):
                    try:
                        container_rows = future.result()
                        rows.extend(container_rows)
                    except Exception as err:
                        pod, container = futures[future]
                        logger.error(f"Concurrent fetch error for {pod.metadata.name}/{container.name}: {err}")

        rows = sorted(rows, key=lambda r: r.time["unixtime"], reverse=True)[
            : request.limit
        ]
        return DataResponse(rows=rows)

    @classmethod
    def fetch_graph_data(cls, request: GraphDataRequest):
        with KubernetesClient(request.source.conn.data) as client:
            time_from_dt = datetime.fromtimestamp(request.time_from / 1000, UTC_ZONE)
            time_to_dt = datetime.fromtimestamp(request.time_to / 1000, UTC_ZONE)
            graph_tail_limit = 2000
            
            namespace = request.source.data.get("namespace")
            if not namespace:
                raise ValueError("Namespace is required in source configuration")

            evaluator = Evaluator()
            root = None
            if request.query:
                parser = parse(request.query)
                root = parser.root

            stats_by_ts = {}
            unique_ts = {request.time_from, request.time_to}
            group_by = request.group_by[0] if request.group_by else None
            total = 0

            selected_deployments = request.context_fields.get("deployment", [])
            
            if selected_deployments:
                filtered_pods = cls.get_pods_for_deployments(client, namespace, selected_deployments)
            else:
                filtered_pods = client.core.list_namespaced_pod(namespace=namespace).items

            fetch_tasks = []
            total_pods = len(filtered_pods)
            for pod in filtered_pods:
                for container in pod.spec.containers:
                    fetch_tasks.append((pod, container))
            
            def fetch_container_graph_logs(pod, container):
                pod_name = pod.metadata.name
                node_name = pod.spec.node_name or ""
                labels = json.dumps(pod.metadata.labels or {})
                container_name = container.name
                container_stats = {}
                container_total = 0
                
                try:
                    since_seconds = int((datetime.now(UTC_ZONE) - time_from_dt).total_seconds())
                    if since_seconds < 0:
                        since_seconds = 0
                    base_tail = graph_tail_limit
                    if graph_tail_limit > 100 and total_pods > 1:
                        base_tail = int(max(1, (graph_tail_limit / total_pods) * 1.3))
                    
                    log_params = {
                        "name": pod_name,
                        "namespace": namespace,
                        "container": container_name,
                        "timestamps": True,
                        "tail_lines": base_tail,
                    }
                    if since_seconds > 0:
                        log_params["since_seconds"] = since_seconds
                    
                    log_sources = cls.fetch_container_logs_with_previous(client, namespace, pod_name, container_name, log_params)
                    
                except client.exceptions.ApiException as e:
                    if e.status == 403:
                        logger.error(f"RBAC error: Insufficient permissions for {namespace}/{pod_name}/{container_name}")
                    elif e.status == 404:
                        logger.warning(f"Resource not found: {namespace}/{pod_name}/{container_name}")
                    else:
                        logger.error(f"Graph log fetch error {namespace}/{pod_name}/{container_name}: {e}")
                    return container_stats, container_total, set()
                except Exception as err:
                    logger.error(
                        "Graph log fetch error %s/%s/%s: %s",
                        namespace,
                        pod_name,
                        container_name,
                        err,
                    )
                    return container_stats, container_total, set()

                local_unique_ts = set()
                
                for log_type, logs in log_sources:
                    for line in logs.splitlines():
                        if not line:
                            continue
                        parts = line.split(" ", 1)
                        
                        ts = parse_k8s_timestamp(parts[0], UTC_ZONE)
                        if not ts:
                            continue
                        
                        if ts < time_from_dt or ts > time_to_dt:
                            continue
                        
                        ts_key = int(ts.timestamp() * 1000)
                        local_unique_ts.add(ts_key)
                        container_total += 1

                        if not group_by:
                            groupper = "Rows"
                        else:
                            if group_by.name == "namespace":
                                groupper = namespace
                            elif group_by.name == "pod_name":
                                groupper = pod_name
                            elif group_by.name == "node_name":
                                groupper = node_name
                            elif group_by.name == "container_name":
                                groupper = container_name
                            else:
                                pseudo_row = {
                                    "namespace": namespace,
                                    "pod_name": pod_name,
                                    "container_name": container_name,
                                    "node_name": node_name,
                                    "labels": json.loads(labels) if labels else {},
                                }
                                groupper = str(pseudo_row.get(group_by.name, "__none__"))

                        container_stats.setdefault(groupper, {})
                        container_stats[groupper][ts_key] = (
                            container_stats[groupper].get(ts_key, 0) + 1
                        )
                
                return container_stats, container_total, local_unique_ts
            
            with ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_REQUESTS) as executor:
                futures = {
                    executor.submit(fetch_container_graph_logs, pod, container): (pod, container)
                    for pod, container in fetch_tasks
                }
                
                for future in as_completed(futures):
                    try:
                        container_stats, container_total, local_unique_ts = future.result()
                        total += container_total
                        unique_ts.update(local_unique_ts)
                        
                        for groupper, ts_counts in container_stats.items():
                            stats_by_ts.setdefault(groupper, {})
                            for ts_key, count in ts_counts.items():
                                stats_by_ts[groupper][ts_key] = (
                                    stats_by_ts[groupper].get(ts_key, 0) + count
                                )
                    except Exception as err:
                        pod, container = futures[future]
                        logger.error(f"Concurrent graph fetch error for {pod.metadata.name}/{container.name}: {err}")

            timestamps = sorted(unique_ts)
            data = {name: [] for name in stats_by_ts.keys()}
            for ts in timestamps:
                for name in stats_by_ts.keys():
                    data[name].append(stats_by_ts[name].get(ts, 0))

            return GraphDataResponse(
                timestamps=timestamps,
                data=data,
                total=total,
            )