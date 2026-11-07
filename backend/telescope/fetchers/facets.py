"""Top values per column over a sample of matching rows, for the explorer facet sidebar.

Sampling follows HyperDX common-utils/src/core/metadata.ts (MIT): a LIMIT-ed read capped by max_rows_to_read.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from flyql import parse

from telescope.constants import UTC_ZONE, CHART_QUERY_TIMEOUT_SECONDS
from telescope.flyql_registry import transformer_registry
from telescope.fetchers.request import DataRequest
from telescope.fetchers.search import body_column

# HyperDX DEFAULT_METADATA_MAX_ROWS_TO_READ
DEFAULT_MAX_ROWS_TO_READ = 3_000_000


@dataclass
class FacetRequest:
    source: object
    time_from: int
    time_to: int
    query: str = ""
    raw_query: str = ""
    text: str = ""
    columns: List[str] = field(default_factory=list)
    map_keys: Dict[str, List[str]] = field(default_factory=dict)
    limit: int = 10
    sample: int = 100_000
    context_columns: Dict = field(default_factory=dict)


@dataclass
class Facet:
    # kind is "value" (a column or a Map key's values) or "keys" (the keys of a Map column).
    id: str
    kind: str
    column: str
    key: Optional[str] = None


def is_map_type(type_name: str) -> bool:
    return (type_name or "").lower().replace("nullable(", "").startswith("map(")


def plan_facets(request: FacetRequest) -> List[Facet]:
    """Facet ids: a column name, `<col>` for a Map column's keys, and `<col>.<key>` for a Map key's values."""
    facets = []
    for name in request.columns:
        kind = "keys" if is_map_type(request.source._columns[name].type) else "value"
        facets.append(Facet(id=name, kind=kind, column=name))
    for name, keys in request.map_keys.items():
        for key in keys:
            facets.append(Facet(id=f"{name}.{key}", kind="value", column=name, key=key))
    return facets


def build_response(facets, counts, total_sampled, sampled, limit):
    """counts: facet id -> [(value, count)] sorted by count desc, at most limit + 1 long."""
    response = {
        "facets": {},
        "map_keys": {},
        "more": [],
        "total_sampled": total_sampled,
        "sampled": sampled,
    }
    for facet in facets:
        items = counts.get(facet.id, [])
        if len(items) > limit:
            response["more"].append(facet.id)
        values = [{"value": v, "count": int(c)} for v, c in items[:limit]]
        target = response["map_keys"] if facet.kind == "keys" else response["facets"]
        target[facet.id] = values
    return response


def _quote(name):
    return "`" + name.replace("`", "``") + "`"


def _ch_facet_array(facet: Facet, index: int, params: dict) -> str:
    col = _quote(facet.column)
    if facet.kind == "keys":
        values = f"mapKeys({col})"
    elif facet.key is not None:
        params[f"facet_key_{index}"] = facet.key
        key = f"{{facet_key_{index}:String}}"
        values = f"if(mapContains({col}, {key}), [{col}[{key}]], [])"
    else:
        values = f"[{col}]"
    return f"arrayMap(v -> ({index}, toNullable(toString(v))), {values})"


def clickhouse_sql(request: FacetRequest, where: str, facets: List[Facet]):
    """One scan: every facet becomes (index, value) pairs, ARRAY JOINed and counted with LIMIT n BY index."""
    from telescope.fetchers.clickhouse import build_time_clause

    source = request.source
    params = {}
    arrays = ["[(0, CAST(NULL, 'Nullable(String)'))]"]
    arrays += [_ch_facet_array(f, i + 1, params) for i, f in enumerate(facets)]
    clauses = [
        build_time_clause(
            source.time_column, source.date_column, request.time_from, request.time_to
        ),
        f"({where})",
    ]
    if request.raw_query:
        clauses.append(f"({request.raw_query})")
    if request.text:
        params["facet_text"] = request.text
        clauses.append(
            f"positionCaseInsensitive(toString({_quote(body_column(source))}), {{facet_text:String}}) > 0"
        )
    table = f"{source.data['database']}.{source.data['table']}"
    sql = (
        f"SELECT pair.1 AS idx, pair.2 AS value, count() AS cnt FROM ("
        f"SELECT arrayConcat({', '.join(arrays)}) AS pairs FROM {table}"
        f" WHERE {' AND '.join(clauses)}"
        f" ORDER BY {_quote(source.time_column)} DESC LIMIT {int(request.sample)}"
        f") ARRAY JOIN pairs AS pair GROUP BY idx, value"
        f" ORDER BY idx, cnt DESC, value LIMIT {int(request.limit) + 1} BY idx"
    )
    if source.data.get("settings"):
        sql += f" SETTINGS {source.data['settings']}"
    return sql, params


def max_rows_to_read(request: FacetRequest) -> int:
    return max(DEFAULT_MAX_ROWS_TO_READ, int(request.sample))


def fetch_clickhouse(request: FacetRequest) -> dict:
    from telescope.fetchers.clickhouse import (
        ClickhouseConnect,
        _client_query,
        flyql_clickhouse_columns,
    )
    from flyql.generators.clickhouse import to_sql_where

    source = request.source
    where = "true"
    if request.query:
        where = to_sql_where(
            parse(request.query).root,
            columns=flyql_clickhouse_columns(source._columns),
            registry=transformer_registry(),
        )
    facets = plan_facets(request)
    sql, params = clickhouse_sql(request, where, facets)
    max_read = max_rows_to_read(request)
    with ClickhouseConnect(source.conn.data) as c:
        result = _client_query(
            c.client,
            sql,
            parameters=params,
            settings={
                "max_rows_to_read": max_read,
                "read_overflow_mode": "break",
                "max_execution_time": CHART_QUERY_TIMEOUT_SECONDS,
            },
        )
    total, counts = 0, {}
    for idx, value, cnt in result.result_rows:
        if idx == 0:
            total = int(cnt)
        else:
            counts.setdefault(facets[idx - 1].id, []).append((value, cnt))
    read_rows = int((getattr(result, "summary", None) or {}).get("read_rows", 0))
    sampled = total >= request.sample or read_rows >= max_read
    return build_response(facets, counts, total, sampled, request.limit)


def _sr_facet_query(facet: Facet, index: int, limit: int) -> str:
    from telescope.fetchers.starrocks import escape_param

    col = _quote(facet.column)
    if facet.kind == "keys":
        return (
            f"SELECT {index}, k, count(*) AS cnt FROM s, unnest(map_keys(s.{col})) AS t(k)"
            f" GROUP BY k ORDER BY cnt DESC, k LIMIT {limit + 1}"
        )
    expr = f"cast(s.{col} as string)"
    filter_clause = ""
    if facet.key is not None:
        key = escape_param(facet.key)
        expr = f"element_at(s.{col}, {key})"
        filter_clause = f" WHERE {expr} IS NOT NULL"
    return (
        f"SELECT {index}, {expr} AS v, count(*) AS cnt FROM s{filter_clause}"
        f" GROUP BY v ORDER BY cnt DESC, v LIMIT {limit + 1}"
    )


def starrocks_sql(request: FacetRequest, where: str, facets: List[Facet]):
    """A sampled CTE, then one statement per facet (StarRocks has no LIMIT BY)."""
    from telescope.fetchers.starrocks import build_time_clause, escape_param

    source = request.source
    clauses = [
        build_time_clause(
            source.time_column, source.date_column, request.time_from, request.time_to
        ),
        f"({where})",
    ]
    if request.raw_query:
        clauses.append(f"({request.raw_query})")
    if request.text:
        body = _quote(body_column(source))
        clauses.append(
            f"instr(lower(cast({body} as string)), lower({escape_param(request.text)})) > 0"
        )
    hint_vars = f"query_timeout={CHART_QUERY_TIMEOUT_SECONDS}"
    if source.data.get("settings"):
        hint_vars += f", {source.data['settings']}"
    columns = sorted({f.column for f in facets})
    select = ", ".join(_quote(c) for c in columns) or "1 AS one"
    table = f"{source.data['catalog']}.{source.data['database']}.{source.data['table']}"
    cte = (
        f"WITH s AS (SELECT {select} FROM {table} WHERE {' AND '.join(clauses)}"
        f" ORDER BY {_quote(source.time_column)} DESC LIMIT {int(request.sample)}) "
    )
    statements = [f"{cte}SELECT /*+ SET_VAR({hint_vars}) */ count(*) FROM s"]
    for i, facet in enumerate(facets):
        statements.append(
            f"{cte}SELECT /*+ SET_VAR({hint_vars}) */ * FROM ("
            f"{_sr_facet_query(facet, i + 1, int(request.limit))}) f"
        )
    return statements


def fetch_starrocks(request: FacetRequest) -> dict:
    from telescope.fetchers.starrocks import StarrocksConnect, flyql_starrocks_columns
    from flyql.generators.starrocks import to_sql_where

    source = request.source
    where = "true"
    if request.query:
        where = to_sql_where(
            parse(request.query).root,
            columns=flyql_starrocks_columns(source._columns),
            registry=transformer_registry(),
        )
    facets = plan_facets(request)
    statements = starrocks_sql(request, where, facets)
    counts = {}
    with StarrocksConnect(source.conn.data) as c:
        cur = c.client.cursor()
        cur.execute(statements[0])
        total = int(cur.fetchall()[0][0])
        for facet, sql in zip(facets, statements[1:]):
            cur = c.client.cursor()
            cur.execute(sql)
            counts[facet.id] = [(v, cnt) for _, v, cnt in cur.fetchall()]
    sampled = total >= request.sample
    return build_response(facets, counts, total, sampled, request.limit)


def _row_value(value):
    if value is None:
        return None
    return str(value)


def count_rows(request: FacetRequest, rows) -> dict:
    """Python counting for Docker and Kubernetes rows (newest `sample` rows)."""
    rows = sorted(rows, key=lambda r: r.time["unixtime"], reverse=True)
    if request.text:
        body, needle = body_column(request.source), request.text.lower()
        rows = [r for r in rows if needle in str(r.data.get(body, "")).lower()]
    sampled = len(rows) > request.sample
    rows = rows[: request.sample]
    facets = plan_facets(request)
    counts = {}
    for facet in facets:
        counter = Counter()
        for row in rows:
            value = row.data.get(facet.column)
            if facet.kind == "keys":
                counter.update(str(k) for k in (value or {}))
            elif facet.key is not None:
                if isinstance(value, dict) and facet.key in value:
                    counter[_row_value(value[facet.key])] += 1
            else:
                counter[_row_value(value)] += 1
        ordered = sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))
        counts[facet.id] = ordered[: request.limit + 1]
    return build_response(facets, counts, len(rows), sampled, request.limit)


def fetch_rows_counted(request: FacetRequest, fetcher) -> dict:
    data_request = DataRequest(
        source=request.source,
        query=request.query,
        raw_query="",
        time_from=request.time_from,
        time_to=request.time_to,
        limit=request.sample,
        context_columns=request.context_columns or {},
    )
    result = fetcher._collect_rows(data_request, UTC_ZONE)
    if isinstance(result, tuple):
        rows, error = result
        if error:
            raise ValueError(error)
    else:
        rows = result
    return count_rows(request, rows)


def fetch_facets(request: FacetRequest) -> dict:
    from telescope.fetchers import get_fetchers

    kind = request.source.kind
    if kind == "clickhouse":
        return fetch_clickhouse(request)
    if kind == "starrocks":
        return fetch_starrocks(request)
    return fetch_rows_counted(request, get_fetchers()[kind])
