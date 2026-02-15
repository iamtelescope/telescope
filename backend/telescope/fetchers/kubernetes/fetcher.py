import logging
from datetime import datetime

from flyql.core.parser import parse, ParserError
from flyql.core.exceptions import FlyqlError
from flyql.matcher.evaluator import Evaluator
from flyql.matcher.record import Record

from telescope.constants import UTC_ZONE, SOURCE_BODY_COL_NAME
from telescope.utils import get_telescope_column
from telescope.fetchers.fetcher import BaseFetcher
import json
from telescope.fetchers.models import Row
from telescope.fetchers.request import DataRequest, GraphDataRequest
from telescope.fetchers.response import (
    AutocompleteResponse,
    DataResponse,
    GraphDataResponse,
)
from telescope.fetchers.kubernetes.api import (
    KubeConfigHelper,
    KubeHelper,
    KubeHelperError,
)
from telescope.fetchers.kubernetes.models import (
    ConnectionTestResponse,
    ConnectionTestResponseNg,
)


def ensure_list(val):
    if not val:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [v.strip() for v in val.split(",") if v.strip()]
    return []


logger = logging.getLogger("telescope.fetchers.kubernetes")


class Fetcher(BaseFetcher):
    @classmethod
    def validate_query(cls, source, query):
        if not query:
            return True, None
        try:
            parse(query)
            return True, None
        except ParserError as err:
            return False, err.message
        except FlyqlError as err:
            return False, err.message

    @classmethod
    def test_connection_ng(cls, data: dict) -> ConnectionTestResponseNg:
        response = ConnectionTestResponseNg()
        try:
            config = KubeConfigHelper(
                kubeconfig=data["kubeconfig"],
                kubeconfig_hash=data.get("kubeconfig_hash", ""),
                is_local=data.get("kubeconfig_is_local", False),
            )
            all_contexts = config.list_contexts()
            response.total_contexts = len(all_contexts)

            helper = KubeHelper(
                conn_id=0,
                source_id=0,
                max_concurrent_requests=1,
                config=config,
                context_flyql_filter=data.get("context_filter", ""),
            )

            response.matched_contexts = helper.allowed_contexts

            if not helper.allowed_contexts:
                response.error = "No contexts matched the filter expression"
                return response

            helper.test_connection()
            response.result = True

        except Exception as err:
            response.error = str(err)

        return response

    @classmethod
    def test_connection(cls, data: dict) -> ConnectionTestResponse:
        response = ConnectionTestResponse()
        try:
            config = KubeConfigHelper(
                kubeconfig=data["kubeconfig"],
                kubeconfig_hash=data.get("kubeconfig_hash", ""),
                is_local=data.get("kubeconfig_is_local", False),
            )
            helper = KubeHelper(
                conn_id=0,
                source_id=0,
                max_concurrent_requests=1,
                config=config,
                context_flyql_filter=data.get("context_filter", ""),
            )
            helper.test_connection()
            response.reachability["result"] = True
        except Exception as err:
            response.reachability["error"] = str(err)

        try:
            response.schema["result"] = True
            response.schema["data"] = cls.get_schema(data)
        except Exception as err:
            response.schema["error"] = str(err)

        return response

    @classmethod
    def get_schema(cls, data: dict):
        return [
            get_telescope_column("time", "datetime"),
            get_telescope_column("severity", "string", autocomplete=False),
            get_telescope_column("context", "string", autocomplete=False),
            get_telescope_column("namespace", "string", autocomplete=False),
            get_telescope_column("pod", "string", autocomplete=False),
            get_telescope_column("container", "string", autocomplete=False),
            get_telescope_column("node", "string", autocomplete=False),
            get_telescope_column("labels", "json", autocomplete=False),
            get_telescope_column("annotations", "json", autocomplete=False),
            get_telescope_column(SOURCE_BODY_COL_NAME, "json", autocomplete=False),
            get_telescope_column("status", "string", autocomplete=False),
        ]

    @classmethod
    def get_all_context_columns_data(cls, source):
        conn_data = source.conn.data
        source_data = source.data

        helper = KubeHelper(
            conn_id=source.conn.id,
            source_id=source.id,
            max_concurrent_requests=conn_data.get("max_concurrent_requests", 20),
            config=KubeConfigHelper(
                kubeconfig=conn_data["kubeconfig"],
                kubeconfig_hash=conn_data.get("kubeconfig_hash", ""),
                is_local=conn_data.get("kubeconfig_is_local", False),
            ),
            context_flyql_filter=conn_data.get("context_filter", ""),
            namespace_label_selector=source_data.get("namespace_label_selector", ""),
            namespace_field_selector=source_data.get("namespace_field_selector", ""),
            namespace_flyql_filter=source_data.get("namespace", ""),
        )

        all_namespaces = set()
        for ctx_namespaces in helper.namespaces.values():
            all_namespaces.update(ctx_namespaces)

        return {
            "contexts": list(helper.allowed_contexts_set),
            "namespaces": sorted(all_namespaces),
        }

    @classmethod
    def _get_pods_preview(cls, source, params):
        conn_data = source.conn.data
        source_data = source.data

        helper = KubeHelper(
            conn_id=source.conn.id,
            source_id=source.id,
            max_concurrent_requests=conn_data.get("max_concurrent_requests", 20),
            config=KubeConfigHelper(
                kubeconfig=conn_data["kubeconfig"],
                kubeconfig_hash=conn_data.get("kubeconfig_hash", ""),
                is_local=conn_data.get("kubeconfig_is_local", False),
            ),
            context_flyql_filter=conn_data.get("context_filter", ""),
            namespace_label_selector=source_data.get("namespace_label_selector", ""),
            namespace_field_selector=source_data.get("namespace_field_selector", ""),
            namespace_flyql_filter=source_data.get("namespace", ""),
            pods_label_selector=params.get("pods_label_selector", ""),
            pods_field_selector=params.get("pods_field_selector", ""),
            pods_flyql_filter=params.get("pods_flyql_filter", ""),
            selected_contexts=ensure_list(params.get("contexts", [])),
            selected_namespaces=ensure_list(params.get("namespaces", [])),
        )

        try:
            helper.validate()
        except KubeHelperError:
            return []

        result = []
        for context, namespaces in helper.pods.items():
            for namespace, pods in namespaces.items():
                for pod_name, pod_data in pods.items():
                    result.append(
                        {
                            "context": context,
                            "namespace": namespace,
                            "pod_name": pod_name,
                            "containers": pod_data.get("containers", []),
                            "status": pod_data.get("status", ""),
                            "labels": pod_data.get("labels", {}),
                            "annotations": pod_data.get("annotations", {}),
                        }
                    )

        return result

    @classmethod
    def get_context_column_data(cls, source, column, params=None):
        params = params or {}
        conn_data = source.conn.data
        source_data = source.data

        if column == "pods":
            return cls._get_pods_preview(source, params)

        helper = KubeHelper(
            conn_id=source.conn.id,
            source_id=source.id,
            max_concurrent_requests=conn_data.get("max_concurrent_requests", 20),
            config=KubeConfigHelper(
                kubeconfig=conn_data["kubeconfig"],
                kubeconfig_hash=conn_data.get("kubeconfig_hash", ""),
                is_local=conn_data.get("kubeconfig_is_local", False),
            ),
            context_flyql_filter=conn_data.get("context_filter", ""),
            namespace_label_selector=source_data.get("namespace_label_selector", ""),
            namespace_field_selector=source_data.get("namespace_field_selector", ""),
            namespace_flyql_filter=source_data.get("namespace", ""),
        )

        if column == "context":
            return list(helper.allowed_contexts_set)

        elif column == "namespace":
            if not helper.allowed_contexts_set:
                return []

            all_namespaces = set()
            for ctx_namespaces in helper.namespaces.values():
                all_namespaces.update(ctx_namespaces)

            return sorted(all_namespaces)

        elif column == "deployment":
            if not helper.allowed_contexts_set:
                logger.warning("No contexts available")
                return []

            return helper.get_deployments()

        else:
            raise ValueError(f"Unsupported context column: {column}")

    @classmethod
    def autocomplete(cls, source, column, time_from, time_to, value):
        return AutocompleteResponse(items=[], incomplete=False)

    @classmethod
    def fetch_data(cls, request: DataRequest, tz):
        conn_data = request.source.conn.data
        source_data = request.source.data

        time_from_dt = datetime.fromtimestamp(request.time_from / 1000, UTC_ZONE)
        time_to_dt = datetime.fromtimestamp(request.time_to / 1000, UTC_ZONE)
        now = datetime.now(UTC_ZONE)
        since_seconds = int((now - time_from_dt).total_seconds())
        if since_seconds < 0:
            since_seconds = 0

        helper = KubeHelper(
            conn_id=request.source.conn.id,
            source_id=request.source.id,
            max_concurrent_requests=conn_data.get("max_concurrent_requests", 20),
            config=KubeConfigHelper(
                kubeconfig=conn_data["kubeconfig"],
                kubeconfig_hash=conn_data.get("kubeconfig_hash", ""),
                is_local=conn_data.get("kubeconfig_is_local", False),
            ),
            context_flyql_filter=conn_data.get("context_filter", ""),
            namespace_label_selector=source_data.get("namespace_label_selector", ""),
            namespace_field_selector=source_data.get("namespace_field_selector", ""),
            namespace_flyql_filter=source_data.get("namespace", ""),
            pods_label_selector=request.context_columns.get(
                "pods_label_selector", ""
            ).strip(),
            pods_field_selector=request.context_columns.get(
                "pods_field_selector", ""
            ).strip(),
            pods_flyql_filter=request.context_columns.get("pods_flyql_filter", ""),
            selected_contexts=ensure_list(request.context_columns.get("contexts", [])),
            selected_namespaces=ensure_list(
                request.context_columns.get("namespaces", [])
            ),
        )

        try:
            helper.validate()
        except KubeHelperError as e:
            return DataResponse(rows=[], error=str(e))

        if not helper.contexts:
            return DataResponse(rows=[], error="No contexts available")

        total_namespaces = sum(len(ns) for ns in helper.namespaces.values())
        if total_namespaces == 0:
            if helper.errors:
                error_details = "; ".join(
                    f"{err['operation']}: {err['data']}" for err in helper.errors
                )
                return DataResponse(
                    rows=[], error=f"Failed to fetch namespaces: {error_details}"
                )
            return DataResponse(
                rows=[], error="No namespaces found matching the filters"
            )

        total_pods = sum(
            len(pods) for ns_pods in helper.pods.values() for pods in ns_pods.values()
        )
        if total_pods == 0:
            return DataResponse(rows=[], error="No pods found matching the filters")

        logger.info(
            "Fetching logs: contexts=%d, namespaces=%d, pods=%d",
            len(helper.contexts),
            total_namespaces,
            total_pods,
        )

        log_entries, log_errors = helper.get_logs(
            since_seconds, time_from_dt, time_to_dt
        )

        if log_errors:
            logger.warning("Log fetch errors: %s", log_errors)

        logger.info("Total log entries fetched: %d", len(log_entries))

        evaluator = Evaluator()
        query_ast = None
        if request.query:
            parser = parse(request.query)
            query_ast = parser.root

        rows = []
        for entry in log_entries:
            row = Row(
                source=request.source,
                selected_columns=[
                    "time",
                    "context",
                    "namespace",
                    "pod",
                    "container",
                    "node",
                    "labels",
                    "annotations",
                    SOURCE_BODY_COL_NAME,
                    "status",
                ],
                values=[
                    entry.timestamp,
                    entry.context,
                    entry.namespace,
                    entry.pod,
                    entry.container,
                    entry.node,
                    entry.labels,
                    entry.annotations,
                    entry.message,
                    entry.status,
                ],
                tz=tz,
            )

            if query_ast:
                if evaluator.evaluate(query_ast, Record(data=row.data)):
                    rows.append(row)
            else:
                rows.append(row)

        rows = sorted(rows, key=lambda r: r.time["unixtime"], reverse=True)
        total_rows = len(rows)
        rows = rows[: request.limit]

        message = None
        if total_rows > request.limit:
            message = f"Displaying limited results: Only {request.limit} out of {total_rows} matching entries are shown."

        return DataResponse(rows=rows, message=message)

    @classmethod
    def fetch_graph_data(cls, request: GraphDataRequest):
        return GraphDataResponse(
            timestamps=[],
            data={},
            total=0,
        )

    @classmethod
    def fetch_data_and_graph(cls, request, tz):
        from telescope.fetchers.utils import generate_graph_from_rows
        from telescope.fetchers.response import DataAndGraphDataResponse
        from telescope.constants import UTC_ZONE

        conn_data = request.source.conn.data
        source_data = request.source.data

        time_from_dt = datetime.fromtimestamp(request.time_from / 1000, UTC_ZONE)
        time_to_dt = datetime.fromtimestamp(request.time_to / 1000, UTC_ZONE)
        now = datetime.now(UTC_ZONE)
        since_seconds = int((now - time_from_dt).total_seconds())
        if since_seconds < 0:
            since_seconds = 0

        helper = KubeHelper(
            conn_id=request.source.conn.id,
            source_id=request.source.id,
            max_concurrent_requests=conn_data.get("max_concurrent_requests", 20),
            config=KubeConfigHelper(
                kubeconfig=conn_data["kubeconfig"],
                kubeconfig_hash=conn_data.get("kubeconfig_hash", ""),
                is_local=conn_data.get("kubeconfig_is_local", False),
            ),
            context_flyql_filter=conn_data.get("context_filter", ""),
            namespace_label_selector=source_data.get("namespace_label_selector", ""),
            namespace_field_selector=source_data.get("namespace_field_selector", ""),
            namespace_flyql_filter=source_data.get("namespace", ""),
            pods_label_selector=request.context_columns.get(
                "pods_label_selector", ""
            ).strip(),
            pods_field_selector=request.context_columns.get(
                "pods_field_selector", ""
            ).strip(),
            pods_flyql_filter=request.context_columns.get("pods_flyql_filter", ""),
            selected_contexts=ensure_list(request.context_columns.get("contexts", [])),
            selected_namespaces=ensure_list(
                request.context_columns.get("namespaces", [])
            ),
        )

        try:
            helper.validate()
        except KubeHelperError as e:
            return DataAndGraphDataResponse(
                rows=[], graph_timestamps=[], graph_data={}, graph_total=0, error=str(e)
            )

        if not helper.contexts:
            return DataAndGraphDataResponse(
                rows=[],
                graph_timestamps=[],
                graph_data={},
                graph_total=0,
                error="No contexts available",
            )

        total_namespaces = sum(len(ns) for ns in helper.namespaces.values())
        if total_namespaces == 0:
            if helper.errors:
                error_details = "; ".join(
                    f"{err['operation']}: {err['data']}" for err in helper.errors
                )
                return DataAndGraphDataResponse(
                    rows=[],
                    graph_timestamps=[],
                    graph_data={},
                    graph_total=0,
                    error=f"Failed to fetch namespaces: {error_details}",
                )
            return DataAndGraphDataResponse(
                rows=[],
                graph_timestamps=[],
                graph_data={},
                graph_total=0,
                error="No namespaces found matching the filters",
            )

        total_pods = sum(
            len(pods) for ns_pods in helper.pods.values() for pods in ns_pods.values()
        )
        if total_pods == 0:
            return DataAndGraphDataResponse(
                rows=[],
                graph_timestamps=[],
                graph_data={},
                graph_total=0,
                error="No pods found matching the filters",
            )

        logger.info(
            "Fetching logs: contexts=%d, namespaces=%d, pods=%d",
            len(helper.contexts),
            total_namespaces,
            total_pods,
        )

        log_entries, log_errors = helper.get_logs(
            since_seconds, time_from_dt, time_to_dt
        )

        if log_errors:
            logger.warning("Log fetch errors: %s", log_errors)

        logger.info("Total log entries fetched: %d", len(log_entries))

        evaluator = Evaluator()
        query_ast = None
        if request.query:
            parser = parse(request.query)
            query_ast = parser.root

        all_rows = []
        for entry in log_entries:
            row = Row(
                source=request.source,
                selected_columns=[
                    "time",
                    "context",
                    "namespace",
                    "pod",
                    "container",
                    "node",
                    "labels",
                    "annotations",
                    SOURCE_BODY_COL_NAME,
                    "status",
                ],
                values=[
                    entry.timestamp,
                    entry.context,
                    entry.namespace,
                    entry.pod,
                    entry.container,
                    entry.node,
                    entry.labels,
                    entry.annotations,
                    entry.message,
                    entry.status,
                ],
                tz=tz,
            )

            if query_ast:
                if evaluator.evaluate(query_ast, Record(data=row.data)):
                    all_rows.append(row)
            else:
                all_rows.append(row)

        group_by_field = request.group_by[0] if request.group_by else None
        use_severity_grouping = not group_by_field
        graph_timestamps, graph_data, graph_total = generate_graph_from_rows(
            all_rows,
            request.time_from,
            request.time_to,
            group_by_field,
            group_by_severity=use_severity_grouping,
        )

        all_rows = sorted(all_rows, key=lambda r: r.time["unixtime"], reverse=True)
        limited_rows = all_rows[: request.limit]

        return DataAndGraphDataResponse(
            rows=limited_rows,
            graph_timestamps=graph_timestamps,
            graph_data=graph_data,
            graph_total=graph_total,
        )
