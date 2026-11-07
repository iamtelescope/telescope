"""Row samples for event patterns: one random sample per source kind, then the same Python mining."""

import random
from dataclasses import dataclass, field
from typing import Dict

from flyql import parse

from telescope.constants import CHART_QUERY_TIMEOUT_SECONDS, UTC_ZONE
from telescope.fetchers.request import DataRequest
from telescope.flyql_registry import transformer_registry
from telescope.patterns.mine import mine_patterns

KINDS = {"clickhouse", "docker", "kubernetes"}


@dataclass
class PatternRequest:
    source: object
    time_from: int
    time_to: int
    column: str
    query: str = ""
    raw_query: str = ""
    text: str = ""
    sample: int = 10_000
    context_columns: Dict = field(default_factory=dict)


def _quote(name):
    return "`" + name.replace("`", "``") + "`"


def clickhouse_where(request: PatternRequest, params: dict) -> str:
    from flyql.generators.clickhouse import to_sql_where
    from telescope.fetchers.clickhouse import (
        build_time_clause,
        flyql_clickhouse_columns,
        text_clause,
    )

    source = request.source
    clauses = [
        build_time_clause(
            source.time_column, source.date_column, request.time_from, request.time_to
        )
    ]
    if request.query:
        where = to_sql_where(
            parse(request.query).root,
            columns=flyql_clickhouse_columns(source._columns),
            registry=transformer_registry(),
        )
        clauses.append(f"({where})")
    if request.raw_query:
        clauses.append(f"({request.raw_query})")
    text = text_clause(source, request.text, params)
    if text:
        clauses.append(text)
    return " AND ".join(clauses)


def clickhouse_sample_sql(request: PatternRequest, where: str, ratio):
    """SAMPLE <ratio> when the table has a sampling key and the sample is smaller than the total, else rand()."""
    source = request.source
    table = f"{source.data['database']}.{source.data['table']}"
    sample = f" SAMPLE {ratio:.6f}" if ratio is not None else ""
    sql = (
        f"SELECT toUnixTimestamp64Milli(toDateTime64({_quote(source.time_column)}, 3)),"
        f" toString({_quote(request.column)}) FROM {table}{sample} WHERE {where}"
        f" ORDER BY rand() LIMIT {int(request.sample)}"
    )
    if source.data.get("settings"):
        sql += f" SETTINGS {source.data['settings']}"
    return sql


def fetch_clickhouse(request: PatternRequest):
    from telescope.fetchers.clickhouse import ClickhouseConnect, _client_query

    source = request.source
    params = {}
    where = clickhouse_where(request, params)
    table = f"{source.data['database']}.{source.data['table']}"
    settings = {"max_execution_time": CHART_QUERY_TIMEOUT_SECONDS}
    with ClickhouseConnect(source.conn.data) as c:
        total = _client_query(
            c.client,
            f"SELECT count() FROM {table} WHERE {where}",
            parameters=params,
            settings=settings,
        ).result_rows[0][0]
        key = _client_query(
            c.client,
            "SELECT sampling_key FROM system.tables WHERE database = {db:String} AND name = {t:String}",
            parameters={"db": source.data["database"], "t": source.data["table"]},
        ).result_rows
        ratio = None
        if key and key[0][0] and total > request.sample:
            # A little over the target so that LIMIT, not the ratio, sets the sample size.
            ratio = min(1.0, request.sample * 1.2 / total)
        rows = _client_query(
            c.client,
            clickhouse_sample_sql(request, where, ratio),
            parameters=params,
            settings=settings,
        ).result_rows
    return [(int(t), body) for t, body in rows], int(total)


def fetch_rows(request: PatternRequest, fetcher):
    """Docker and Kubernetes: every matching row the fetcher returns, then a random sample in Python."""
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
    rows, error = result if isinstance(result, tuple) else (result, None)
    if error:
        raise ValueError(error)
    pairs = [(r.time["unixtime"], r.data.get(request.column)) for r in rows]
    total = len(pairs)
    if total > request.sample:
        pairs = random.sample(pairs, request.sample)
    return pairs, total


def fetch_patterns(request: PatternRequest) -> dict:
    from telescope.fetchers import get_fetchers

    kind = request.source.kind
    if kind == "clickhouse":
        rows, total = fetch_clickhouse(request)
    elif kind in KINDS:
        rows, total = fetch_rows(request, get_fetchers()[kind])
    else:
        raise ValueError(f"patterns are not supported for {kind} sources")
    return mine_patterns(
        rows, total, request.time_from, request.time_to, request.column
    )
