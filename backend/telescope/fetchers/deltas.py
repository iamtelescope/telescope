"""Heatmap of a numeric column over time and event deltas of a selected rectangle (ClickHouse only).

Flattening, field filtering and the semantic boost are ported from HyperDX common-utils/src/core/eventDeltas.ts
(MIT). The score differs: total variation distance over all sampled rows, so a key's coverage counts too.
"""

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from telescope.constants import CHART_QUERY_TIMEOUT_SECONDS
from telescope.fetchers.chart import (
    ChartResult,
    align_range,
    pick_granularity,
    quote_column,
)
from telescope.utils import convert_to_base_ch

HEATMAP_MAX_ROWS = 40
# Log buckets per decade, the finest that fits in HEATMAP_MAX_ROWS rows.
BUCKETS_PER_DECADE = [10, 5, 4, 2, 1]
DELTAS_DEFAULT_SAMPLE = 5000
DELTAS_MAX_SAMPLE = 20000
DELTAS_TOP_VALUES = 10
MIN_PROPERTY_OCCURENCES = 5
BOOSTED_ATTRIBUTE_SUFFIXES = [
    "service.name",
    "http.method",
    "http.request.method",
    "http.status_code",
    "http.response.status_code",
    "error",
    "error.type",
    "deployment.environment",
    "deployment.environment.name",
    "rpc.method",
    "rpc.service",
    "db.system",
    "db.operation",
    "messaging.system",
    "messaging.operation",
]
TYPE_WRAPPER_RE = re.compile(r"^(LowCardinality|Nullable)\((.*)\)$")
ARRAY_KEY_RE = re.compile(r"^([^\[]+)\[(\d+)\]$")


@dataclass
class Selection:
    """The rows a heatmap or deltas request looks at; duck-typed for patterns.fetch.clickhouse_where."""

    source: object
    time_from: int
    time_to: int
    column: str
    query: str = ""
    raw_query: str = ""
    text: str = ""
    context_columns: Dict = field(default_factory=dict)


def log_edges(low: Optional[float], high: Optional[float]) -> List[float]:
    """Bucket edges 10^(k/n) covering [low, high]; values below the first edge count in bucket 0.

    At most HEATMAP_MAX_ROWS rows up to 1e308; past that the low end is cut off into bucket 0.
    """
    if low is None or high is None or not 0 < low < math.inf or not high < math.inf:
        return [1.0, 10.0]
    high = max(high, low)
    for n in BUCKETS_PER_DECADE:
        k_hi = min(math.ceil(math.log10(high) * n), 308 * n)
        k_lo = min(math.floor(math.log10(low) * n), k_hi - 1)
        if k_hi - k_lo <= HEATMAP_MAX_ROWS or n == 1:
            k_lo = max(k_lo, k_hi - HEATMAP_MAX_ROWS)
            return [10 ** (k / n) for k in range(k_lo, k_hi + 1)]


def bucket_sql(value_sql: str, edges: List[float]) -> str:
    """0-based bucket of `edges` holding a value; below the first edge is 0, past the last the top bucket."""
    inner = ", ".join(repr(float(e)) for e in edges[1:-1])
    top = len(edges) - 2
    return (
        f"if((arrayFirstIndex(e -> {value_sql} < e, CAST([{inner}], 'Array(Float64)')) AS __i) = 0,"
        f" {top}, __i - 1)"
    )


def _time_sql(source) -> str:
    column = quote_column(source, source.time_column)
    time_type = convert_to_base_ch(source._columns[source.time_column].type.lower())
    if time_type in ["timestamp", "uint64", "int64"]:
        column = f"toDateTime({column})"
    return f"toUnixTimestamp64Milli(toDateTime64({column}, 3))"


def _where(selection: Selection, params: Dict) -> str:
    """The selection's rows with a finite value; NULL, NaN and Inf have no place on a log axis."""
    from telescope.patterns.fetch import clickhouse_where

    value = quote_column(selection.source, selection.column)
    return f"({clickhouse_where(selection, params)}) AND isFinite(toFloat64({value}))"


def _table(source) -> str:
    return f"{source.data['database']}.{source.data['table']}"


def _run(c, sql: str, params: Dict, source):
    from telescope.fetchers.clickhouse import _client_query

    if source.data.get("settings"):
        sql += f" SETTINGS {source.data['settings']}"
    return _client_query(
        c.client,
        sql,
        parameters=params,
        settings={"max_execution_time": CHART_QUERY_TIMEOUT_SECONDS},
    ).result_rows


def fetch_heatmap(selection: Selection, granularity: str = "auto") -> ChartResult:
    """Counts per (time bucket, log bucket of `column`), as sparse [time index, bucket index, count] cells."""
    from telescope.fetchers.clickhouse import ClickhouseConnect

    source = selection.source
    granularity, step_ms = pick_granularity(
        selection.time_from, selection.time_to, granularity
    )
    grid_from, grid_to = align_range(selection.time_from, selection.time_to, step_ms)
    timestamps = list(range(grid_from, grid_to, step_ms))
    params = {}
    where = _where(selection, params)
    value = quote_column(source, selection.column)
    with ClickhouseConnect(source.conn.data) as c:
        low, high, total = _run(
            c,
            f"SELECT minIf({value}, {value} > 0), max({value}), count()"
            f" FROM {_table(source)} WHERE {where}",
            params,
            source,
        )[0]
        edges = log_edges(low if total else None, high if total else None)
        rows = (
            _run(
                c,
                f"SELECT intDiv({_time_sql(source)}, {step_ms}) * {step_ms} AS __t,"
                f" {bucket_sql(value, edges)} AS __b, count()"
                f" FROM {_table(source)} WHERE {where}"
                f" GROUP BY __t, __b ORDER BY __t, __b",
                params,
                source,
            )
            if total
            else []
        )
    index = {ts: i for i, ts in enumerate(timestamps)}
    cells = [[index[int(t)], int(b), int(n)] for t, b, n in rows if int(t) in index]
    return ChartResult(
        kind="heatmap",
        time_from=grid_from,
        time_to=grid_to,
        extra={
            "granularity": granularity,
            "step_ms": step_ms,
            "timestamps": timestamps,
            "column": selection.column,
            "y_edges": edges,
            "cells": cells,
            "total": int(total),
            "max": max((n for _, _, n in cells), default=0),
        },
    )


def flatten(data, prefix: str = "", out: Optional[Dict] = None) -> Dict:
    """Dot keys for maps, [i] for arrays; empty maps and arrays keep a {} or [] entry."""
    out = {} if out is None else out
    if isinstance(data, dict):
        for key, value in data.items():
            flatten(value, f"{prefix}.{key}" if prefix else str(key), out)
        if not data and prefix:
            out[prefix] = {}
    elif isinstance(data, (list, tuple)):
        for i, value in enumerate(data):
            flatten(value, f"{prefix}[{i}]", out)
        if not data:
            out[prefix] = []
    else:
        out[prefix] = data
    return out


def value_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value == {}:
        return "{}"
    if value == []:
        return "[]"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def property_statistics(rows: List[Dict]):
    """(key -> rows having it, key -> value -> count) of the flattened rows."""
    present, values = {}, {}
    for row in rows:
        for key, value in flatten(row).items():
            present[key] = present.get(key, 0) + 1
            counts = values.setdefault(key, {})
            text = value_text(value)
            counts[text] = counts.get(text, 0) + 1
    return present, values


def shares(counts: Dict[str, int], rows: int) -> Dict:
    """Value -> percent of all rows; rows without the key count as the value None."""
    if not rows:
        return {}
    result = {v: n / rows * 100 for v, n in counts.items()}
    missing = rows - sum(counts.values())
    if missing:
        result[None] = missing / rows * 100
    return result


def distribution_score(outlier: Dict, inlier: Dict) -> float:
    """Total variation distance, in percent, between two value distributions (0 when one is empty)."""
    if not outlier or not inlier:
        return 0.0
    keys = set(outlier) | set(inlier)
    return sum(abs(outlier.get(v, 0) - inlier.get(v, 0)) for v in keys) / 2


def semantic_boost(key: str) -> int:
    lower = key.lower()
    return int(
        any(lower == s or lower.endswith("." + s) for s in BOOSTED_ATTRIBUTE_SUFFIXES)
    )


def strip_type(column_type: str) -> str:
    value = column_type.strip()
    while True:
        match = TYPE_WRAPPER_RE.match(value)
        if not match:
            return value
        value = match.group(2).strip()


def base_column(key: str, columns: Dict[str, str]) -> Optional[str]:
    """The column a flattened key comes from, or None for keys below an array element."""
    match = ARRAY_KEY_RE.match(key)
    if match:
        return match.group(1)
    if "[" in key:
        return None
    if key in columns:
        return key
    # Map keys hang off their column with a dot: SpanAttributes.http.route.
    return next((c for c in columns if key.startswith(c + ".")), key)


def is_denylisted(key: str, columns: Dict[str, str]) -> bool:
    """String id columns (or arrays of them) and per-index timestamp array elements."""
    name = base_column(key, columns)
    if name is None or name not in columns:
        return False
    if name != key and not ARRAY_KEY_RE.match(key):
        return False
    base = strip_type(columns[name])
    inner = strip_type(base[6:-1]) if base.startswith("Array(") else None
    if re.search(r"(Id|ID)$", name) and (base == "String" or inner == "String"):
        return True
    return bool(inner and inner.startswith("DateTime64("))


def is_high_cardinality(key, out_present, in_present, out_values, in_values) -> bool:
    out_total, in_total = out_present.get(key, 0), in_present.get(key, 0)
    if out_total + in_total <= 20:
        return False
    ratios = [
        len(values.get(key, {})) / total
        for values, total in ((out_values, out_total), (in_values, in_total))
        if total
    ]
    return bool(ratios) and min(ratios) > 0.9


def rank_properties(
    outlier_rows: List[Dict], inlier_rows: List[Dict], columns: Dict[str, str]
) -> List[Dict]:
    """Properties seen in at least 5 rows, most different first, hidden ones last."""
    out_present, out_values = property_statistics(outlier_rows)
    in_present, in_values = property_statistics(inlier_rows)
    keys = {
        k
        for k in set(out_present) | set(in_present)
        if max(out_present.get(k, 0), in_present.get(k, 0)) >= MIN_PROPERTY_OCCURENCES
    }
    ranked = []
    for key in keys:
        out_share = shares(out_values.get(key, {}), len(outlier_rows))
        in_share = shares(in_values.get(key, {}), len(inlier_rows))
        base = distribution_score(out_share, in_share)
        boost = semantic_boost(key) if base > 0 else 0
        hidden_reason = None
        if is_denylisted(key, columns):
            hidden_reason = "denylist"
        elif is_high_cardinality(key, out_present, in_present, out_values, in_values):
            hidden_reason = "high_cardinality"
        values = [
            {"value": v, "outlier": out_share.get(v, 0), "inlier": in_share.get(v, 0)}
            for v in set(out_share) | set(in_share)
        ]
        values.sort(key=lambda x: (-max(x["outlier"], x["inlier"]), x["value"] or ""))
        ranked.append(
            {
                "key": key,
                "score": base + boost * 0.1,
                "hidden": hidden_reason is not None,
                "hidden_reason": hidden_reason,
                "values": values[:DELTAS_TOP_VALUES],
                "distinct": len(values),
            }
        )
    ranked.sort(key=lambda p: (p["hidden"], -p["score"], p["key"]))
    return ranked


def _sample_order(source) -> str:
    span_id = ((source.data.get("otel") or {}).get("roles") or {}).get("span_id")
    if span_id and span_id in source._columns:
        return f"cityHash64({quote_column(source, span_id)})"
    return "rand()"


def fetch_deltas(selection: Selection, outlier: Dict, sample: int) -> Dict:
    """Samples rows inside and outside the outlier rectangle and ranks their properties."""
    from telescope.fetchers.clickhouse import ClickhouseConnect

    source = selection.source
    params = {}
    where = _where(selection, params)
    value = quote_column(source, selection.column)
    bounds = [
        f"{_time_sql(source)} >= {int(outlier['t_min'])}",
        f"{_time_sql(source)} <= {int(outlier['t_max'])}",
    ]
    # As in heatmap cells: y_max is exclusive, and a missing bound is open.
    if outlier.get("y_min") is not None:
        bounds.append(f"{value} >= {float(outlier['y_min'])!r}")
    if outlier.get("y_max") is not None:
        bounds.append(f"{value} < {float(outlier['y_max'])!r}")
    inside = f"({' AND '.join(bounds)})"
    names = list(source._columns)
    select = ", ".join(quote_column(source, n) for n in names)
    order = _sample_order(source)
    table = _table(source)
    with ClickhouseConnect(source.conn.data) as c:
        out_total, in_total = _run(
            c,
            f"SELECT countIf({inside}), countIf(NOT {inside}) FROM {table} WHERE {where}",
            params,
            source,
        )[0]

        def rows(condition):
            result = _run(
                c,
                f"SELECT {select} FROM {table} WHERE {where} AND {condition}"
                f" ORDER BY {order} LIMIT {int(sample)}",
                params,
                source,
            )
            return [dict(zip(names, r)) for r in result]

        outliers = rows(inside)
        inliers = rows(f"NOT {inside}")
    columns = {n: source._columns[n].type for n in names}
    return {
        "column": selection.column,
        "outlier": {"total": int(out_total), "sample": len(outliers)},
        "inlier": {"total": int(in_total), "sample": len(inliers)},
        "properties": rank_properties(outliers, inliers, columns),
    }
