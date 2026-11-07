# Service map: client->server edges from a parent/child span join, with node and edge rows
# from one GROUPING SETS query. SQL and sampling adapted from HyperDX hooks/useServiceMap.tsx.

from telescope.fetchers.clickhouse import ClickhouseConnect, Fetcher, _client_query
from telescope_otel.trace import (
    ERROR_STATUS_CODES,
    TraceError,
    _q,
    _settings,
    _table,
    otel_roles,
)

SERVER_KINDS = ("Server", "Consumer", "SPAN_KIND_SERVER", "SPAN_KIND_CONSUMER")
CLIENT_KINDS = ("Client", "Producer", "SPAN_KIND_CLIENT", "SPAN_KIND_PRODUCER")
REQUIRED_ROLES = ("trace_id", "span_id", "parent_span_id", "span_kind", "service")
# As in HyperDX: bounded time, and a join that may spill to disk instead of running out of memory.
QUERY_SETTINGS = {"max_execution_time": 60, "join_algorithm": "auto"}


def _in(values):
    return ", ".join("'" + v + "'" for v in values)


def service_map_sql(source, roles, query, sampling, trace_id):
    """`query` is FlyQL applied to both span sides, as in HyperDX."""
    ts = _q(roles["timestamp"])
    where = [
        f"{ts} BETWEEN fromUnixTimestamp64Milli({{from:Int64}}) AND fromUnixTimestamp64Milli({{to:Int64}})",
        f"({Fetcher._flyql_sql(source, query)})",
        f"cityHash64({_q(roles['trace_id'])}) % {sampling} = 0",
    ]
    if source.date_column:
        where.append(
            f"{_q(source.date_column)} BETWEEN toDate(fromUnixTimestamp64Milli({{from:Int64}}))"
            " AND toDate(fromUnixTimestamp64Milli({to:Int64}))"
        )
    if trace_id:
        where.append(f"{_q(roles['trace_id'])} = {{trace_id:String}}")
    where = " AND ".join(where)
    kind = _q(roles["span_kind"])
    status = (
        f"lower(toString({_q(roles['status_code'])}))"
        if roles.get("status_code")
        else "''"
    )
    duration = _q(roles["duration"]) if roles.get("duration") else "0"
    # Aliases are prefixed so they never shadow a source column used by the FlyQL filter.
    side = (
        f"SELECT {_q(roles['trace_id'])} AS __sm_trace, {_q(roles['span_id'])} AS __sm_span,"
        f" {_q(roles['parent_span_id'])} AS __sm_parent, toString({_q(roles['service'])}) AS __sm_service,"
        f" {status} AS __sm_status, toFloat64({duration}) AS __sm_duration FROM {_table(source)} WHERE {where}"
    )
    return f"""
WITH
    S AS ({side} AND {kind} IN ({_in(SERVER_KINDS)})),
    C AS ({side} AND {kind} IN ({_in(CLIENT_KINDS)}))
SELECT
    S.__sm_service AS server,
    C.__sm_service AS client,
    GROUPING(C.__sm_service) AS node_level,
    count() AS requests,
    countIf(S.__sm_status IN ({_in(ERROR_STATUS_CODES)})) AS errors,
    quantiles(0.5, 0.95, 0.99)(S.__sm_duration) AS q
FROM S LEFT JOIN C ON S.__sm_trace = C.__sm_trace AND S.__sm_parent = C.__sm_span
WHERE S.__sm_service != C.__sm_service
GROUP BY GROUPING SETS ((S.__sm_service, C.__sm_service), (S.__sm_service))
ORDER BY server, node_level, client{_settings(source)}"""


def _stats(requests, errors, q, sampling, to_ms):
    has_latency = requests > 0 and to_ms is not None
    return {
        "requests": requests * sampling,
        "errors": errors * sampling,
        "error_rate": errors / requests if requests else 0.0,
        "p50": q[0] * to_ms if has_latency else None,
        "p95": q[1] * to_ms if has_latency else None,
        "p99": q[2] * to_ms if has_latency else None,
    }


def fetch_service_map(source, time_from, time_to, query="", sampling=1, trace_id=None):
    """Nodes {service, requests, errors, error_rate, p50, p95, p99} (latency in ms, over the
    service's server spans) and edges {client, server, ...same stats}. A trace is never sampled.
    """
    roles = otel_roles(source, "traces", REQUIRED_ROLES)
    valid, error = Fetcher.validate_query(source, query)
    if not valid:
        raise TraceError(error)
    sampling = 1 if trace_id else int(sampling)
    # Latency in ms; None without a duration role.
    to_ms = (
        10.0 ** (3 - int(roles.get("duration_precision", 9)))
        if roles.get("duration")
        else None
    )
    sql = service_map_sql(source, roles, query, sampling, trace_id)
    params = {"from": time_from, "to": time_to, "trace_id": trace_id or ""}
    with ClickhouseConnect(source.conn.data) as c:
        rows = _client_query(
            c.client, sql, parameters=params, settings=QUERY_SETTINGS
        ).result_rows

    nodes, edges = {}, []
    for server, client, node_level, requests, errors, q in rows:
        stats = _stats(requests, errors, q, sampling, to_ms)
        if node_level:
            nodes[server] = {"service": server, **stats}
        elif client:
            # Calls from uninstrumented callers count in the node row but draw no edge.
            edges.append({"client": client, "server": server, **stats})
    for edge in edges:
        nodes.setdefault(
            edge["client"],
            {"service": edge["client"], **_stats(0, 0, None, sampling, to_ms)},
        )
    return {
        "nodes": sorted(nodes.values(), key=lambda n: n["service"]),
        "edges": edges,
        "sampling": sampling,
        "from": time_from,
        "to": time_to,
        "trace_id": trace_id,
    }
