"""Chart series over the OpenTelemetry exporter metric tables (gauge, sum, histogram,
exponential histogram, summary).

Adapted from HyperDX packages/common-utils/src/core/renderChartConfig.ts (translateMetricChartConfig)
and core/histogram.ts (MIT): per-series deltas with lagInFrame, bucket quantiles. Counter resets
and exponential-histogram quantiles follow Prometheus (promql/functions.go, promql/quantile.go).
"""

import math
from typing import Dict, List, Optional

from telescope.constants import CHART_QUERY_TIMEOUT_SECONDS
from telescope.fetchers.chart import ChartPlan, clean_value, group_key
from telescope.fetchers.clickhouse import (
    ClickhouseConnect,
    Fetcher,
    _client_query,
    escape_param,
)

QUANTILE_AGGS = {"p50": 0.5, "p90": 0.9, "p95": 0.95, "p99": 0.99}
GAUGE_AGGS = {
    "avg": "avg(Value)",
    "min": "min(Value)",
    "max": "max(Value)",
    "last": "argMax(Value, TimeUnix)",
}
METRIC_AGGS = {
    "gauge": list(GAUGE_AGGS),
    "sum": ["rate", "increase"] + list(GAUGE_AGGS),
    "histogram": list(QUANTILE_AGGS),
    "exponential_histogram": list(QUANTILE_AGGS),
    "summary": list(QUANTILE_AGGS),
}
METRIC_TYPES = list(METRIC_AGGS)
ALL_METRIC_AGGS = sorted({a for aggs in METRIC_AGGS.values() for a in aggs})
# A series is one OTel metric stream: resource, instrumentation scope and attributes.
SERIES_KEY = "cityHash64(ResourceAttributes, ScopeName, ScopeVersion, ScopeAttributes, Attributes)"
# Cumulative deltas need the point before the range, so reads start this much earlier.
LOOKBACK_MS = 5 * 60 * 1000
WINDOW = (
    "WINDOW w AS (PARTITION BY {key} ORDER BY TimeUnix"
    " ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)"
)


def metric_tables(source) -> Dict[str, str]:
    otel = (source.data or {}).get("otel") or {}
    if otel.get("signal") != "metrics":
        return {}
    return {k: v for k, v in (otel.get("metric_tables") or {}).items() if v}


def _ms(value: int) -> str:
    return f"fromUnixTimestamp64Milli({int(value)})"


def group_expression(column) -> str:
    """SQL for a group-by column: a plain column or a Map key such as `ResourceAttributes.k8s.pod.name`."""
    segments = column.segments or [column.name]
    if column.name == column.root_name:
        return f"toString(`{column.root_name}`)"
    if not column.is_map():
        raise ValueError(f"cannot group metrics by {column.name}")
    key = ".".join(segments[1:])
    return f"`{column.root_name}`[{escape_param(key)}]"


class MetricQuery:
    """SQL pieces shared by every series of one metric chart request."""

    def __init__(self, request, plan: ChartPlan):
        self.request = request
        self.plan = plan
        source = request.source
        self.database = source.data["database"]
        self.tables = metric_tables(source)
        self.filters = [
            f"({Fetcher._flyql_sql(source, request.query)})",
            f"({request.raw_query or 'true'})",
        ]
        self.groups = [
            f"ifNull(toString({group_expression(g)}), '')" for g in plan.group_bys
        ]
        self.aliases = [f"`__telescope_g{i}`" for i in range(len(self.groups))]
        self.bound = False
        if plan.kind == "timeseries":
            self.step_ms = plan.step_ms
            self.bucket = (
                f"intDiv(toUnixTimestamp(TimeUnix), {plan.step_ms // 1000})"
                f" * {plan.step_ms}"
            )
            self.time_from, self.time_to = plan.time_from, plan.query_to
        else:
            self.time_from, self.time_to = request.time_from, request.time_to
            self.step_ms = max(self.time_to - self.time_from, 1)
            self.bucket = "0"

    def table(self, metric: Dict) -> str:
        table = self.tables.get(metric["type"])
        if not table:
            raise ValueError(f"source has no {metric['type']} metric table")
        return f"`{self.database}`.`{table}`"

    def where(self, metric: Dict, lookback: bool = False) -> str:
        start = self.time_from - (LOOKBACK_MS if lookback else 0)
        parts = [
            "MetricName = {metric:String}",
            f"TimeUnix >= {_ms(start)}",
            f"TimeUnix <= {_ms(self.time_to)}",
            *self.filters,
        ]
        if metric.get("attrs_filter"):
            source = self.request.source
            parts.append(f"({Fetcher._flyql_sql(source, metric['attrs_filter'])})")
        if self.bound:
            parts.append(self.restriction())
        return " AND ".join(parts)

    def restriction(self) -> str:
        """Keeps only the groups bound as the `groups` parameter."""
        if len(self.groups) == 1:
            return f"{self.groups[0]} IN {{groups:Array(String)}}"
        types = ", ".join(["String"] * len(self.groups))
        return f"tuple({', '.join(self.groups)}) IN {{groups:Array(Tuple({types}))}}"

    def top_sql(self, metric: Dict, limit: int) -> str:
        """The `limit` groups with the highest bucket value; histograms rank by observations."""
        rank = "max(`__telescope_v`)"
        if metric["type"] == "histogram":
            rank = "sum(arraySum(`__telescope_v`))"
        elif metric["type"] == "exponential_histogram":
            rank = "sum(arraySum(mapValues(`__telescope_v`)) + `__telescope_z`)"
        aliases = ", ".join(self.aliases)
        return (
            f"SELECT {aliases} FROM ({self.sql(metric)}) GROUP BY {aliases}"
            f" ORDER BY {rank} DESC, {aliases} LIMIT {int(limit)}"
        )

    def dimensions(self) -> str:
        return "".join(f", {e} AS {a}" for e, a in zip(self.groups, self.aliases))

    def group_by(self) -> str:
        return ", ".join(["`__telescope_t`"] + self.aliases)

    def sql(self, metric: Dict) -> str:
        """Rows of (bucket, *groups, value); histograms end in (bounds, counts) instead."""
        kind, agg = metric["type"], metric["agg"]
        table = self.table(metric)
        dims = self.dimensions()
        head = f"SELECT `__telescope_t`{''.join(', ' + a for a in self.aliases)}"
        tail = f" GROUP BY {self.group_by()} ORDER BY `__telescope_t`"
        if agg in GAUGE_AGGS:
            return (
                f"SELECT {self.bucket} AS `__telescope_t`{dims}, {GAUGE_AGGS[agg]} AS `__telescope_v`"
                f" FROM {table} WHERE {self.where(metric)}{tail}"
            )
        if kind == "summary":
            level = QUANTILE_AGGS[agg]
            match = f"q -> abs(q - {level}) < 1e-9"
            value = (
                f"`ValueAtQuantiles.Value`[arrayFirstIndex({match},"
                " `ValueAtQuantiles.Quantile`)]"
            )
            return (
                f"SELECT {self.bucket} AS `__telescope_t`{dims}, avg({value}) AS `__telescope_v`"
                f" FROM {table} WHERE {self.where(metric)}"
                f" AND arrayExists({match}, `ValueAtQuantiles.Quantile`){tail}"
            )
        window = WINDOW.format(key=SERIES_KEY)
        after = f"TimeUnix >= {_ms(self.time_from)}"
        if kind == "sum":
            # A monotonic counter that drops restarted from 0, as in Prometheus; up-down sums can fall.
            prev = "ifNull(lagInFrame(toNullable(Value), 1) OVER w, Value)"
            delta = (
                f"multiIf(AggregationTemporality = 1, Value, IsMonotonic AND Value < {prev},"
                f" Value, Value - {prev})"
            )
            return (
                f"{head}, sum(`__d`) AS `__telescope_v` FROM (SELECT TimeUnix, {self.bucket} AS `__telescope_t`{dims},"
                f" {delta} AS `__d` FROM {table} WHERE {self.where(metric, True)} {window})"
                f" WHERE {after}{tail}"
            )
        if kind == "histogram":
            window = WINDOW.format(key=f"{SERIES_KEY}, cityHash64(ExplicitBounds)")
            counts = "CAST(BucketCounts AS Array(Int64))"
            prev = f"lagInFrame({counts}, 1, emptyArrayInt64()) OVER w"
            # The first point of a series has no previous one; a decrease is a reset.
            delta = (
                f"multiIf(AggregationTemporality = 1, {counts},"
                f" length({prev}) != length({counts}), arrayMap(x -> toInt64(0), {counts}),"
                f" arrayExists((c, p) -> c < p, {counts}, {prev}), {counts},"
                f" arrayMap((c, p) -> c - p, {counts}, {prev}))"
            )
            return (
                f"{head}, `__b`, sumForEach(`__d`) AS `__telescope_v` FROM (SELECT TimeUnix,"
                f" {self.bucket} AS `__telescope_t`{dims}, ExplicitBounds AS `__b`,"
                f" {delta} AS `__d` FROM {table} WHERE {self.where(metric, True)} {window})"
                f" WHERE {after} GROUP BY {self.group_by()}, `__b` ORDER BY `__telescope_t`"
            )
        return self._exponential_sql(metric, table, head, dims, window, after)

    def _exponential_sql(self, metric, table, head, dims, window, after) -> str:
        # Buckets are rescaled to the coarsest scale in range; positive bucket i is key 2i, negative 2i+1.
        scale = f"(SELECT min(Scale) FROM {table} WHERE {self.where(metric, True)})"
        keys = ", ".join(
            f"arrayMap(i -> toInt64(floor(({side}Offset + i - 1) / exp2(Scale - `__s`))) * 2 + {sign},"
            f" arrayEnumerate({side}BucketCounts))"
            for side, sign in (("Positive", 0), ("Negative", 1))
        )
        keys = f"arrayConcat({keys})"
        counts = "CAST(arrayConcat(PositiveBucketCounts, NegativeBucketCounts) AS Array(Int64))"
        point = (
            f"CAST(arrayReduce('sumMap', [{keys}], [{counts}]), 'Map(Int64, Int64)')"
        )
        empty = "CAST(map(), 'Map(Int64, Int64)')"
        prev = f"lagInFrame(`__m`, 1, {empty}) OVER w"
        prev_start = "lagInFrame(toNullable(StartTimeUnix), 1) OVER w"
        prev_zero = "lagInFrame(toInt64(ZeroCount), 1) OVER w"
        reset = (
            f"(StartTimeUnix != {prev_start} OR toInt64(ZeroCount) < {prev_zero}"
            f" OR arrayExists(k -> `__m`[k] < ({prev})[k], mapKeys({prev})))"
        )
        delta = (
            f"multiIf(AggregationTemporality = 1, `__m`, {prev_start} IS NULL, {empty},"
            f" {reset}, `__m`, mapSubtract(`__m`, {prev}))"
        )
        zero = (
            f"multiIf(AggregationTemporality = 1, toInt64(ZeroCount), {prev_start} IS NULL, 0,"
            f" {reset}, toInt64(ZeroCount), toInt64(ZeroCount) - {prev_zero})"
        )
        return (
            f"{head}, any(`__s`), sumMap(`__d`) AS `__telescope_v`, sum(`__z`) AS `__telescope_z` FROM (SELECT TimeUnix,"
            f" {self.bucket} AS `__telescope_t`{dims}, {scale} AS `__s`, {point} AS `__m`,"
            f" {delta} AS `__d`, {zero} AS `__z`"
            f" FROM {table} WHERE {self.where(metric, True)} {window})"
            f" WHERE {after} GROUP BY {self.group_by()} ORDER BY `__telescope_t`"
        )

    def values(self, metric: Dict, rows) -> List:
        """(bucket, *groups, value) rows from the SQL rows of `metric`."""
        width = len(self.groups)
        kind, agg = metric["type"], metric["agg"]
        if agg == "rate":
            seconds = self.step_ms / 1000
            return [(*r[: width + 1], r[-1] / seconds) for r in rows]
        if kind == "histogram":
            best = {}
            for row in rows:
                key = tuple(row[: width + 1])
                if key not in best or sum(row[-1]) > sum(best[key][1]):
                    best[key] = (row[-2], row[-1])
            level = QUANTILE_AGGS[agg]
            return [(*k, histogram_quantile(level, b, c)) for k, (b, c) in best.items()]
        if kind == "exponential_histogram":
            level = QUANTILE_AGGS[agg]
            return [
                (*r[: width + 1], exponential_quantile(level, r[-3], r[-2], r[-1]))
                for r in rows
            ]
        return [tuple(r) for r in rows]


def histogram_quantile(level: float, bounds, counts) -> Optional[float]:
    """Linear interpolation inside the bucket holding the rank, as in HyperDX and Prometheus."""
    total = sum(counts)
    if total <= 0 or len(counts) != len(bounds) + 1:
        return None
    rank = level * total
    seen = 0
    for i, count in enumerate(counts):
        if seen + count >= rank and count > 0:
            if i == len(bounds):
                # The +Inf bucket: the largest finite bound is the best estimate.
                return float(bounds[-1]) if bounds else None
            upper = float(bounds[i])
            lower = float(bounds[i - 1]) if i > 0 else min(0.0, upper)
            return lower + (upper - lower) * (rank - seen) / count
        seen += count
    return None


def exponential_quantile(level: float, scale, buckets, zero_count) -> Optional[float]:
    """Key 2i is positive bucket i, (base^i, base^(i+1)] with base = 2^(2^-scale), and 2i+1 its
    negative mirror; zeros sit at 0. Interpolates on a log2 scale, as Prometheus does.
    """
    width = 2.0 ** -int(scale)
    # (value order, index order, negative, count): negatives, then zero, then positives.
    spans = [(1, 0, 0, max(int(zero_count or 0), 0))]
    for key, count in (buckets or {}).items():
        index, negative = int(key) >> 1, int(key) & 1
        spans.append((0, -index, 1, count) if negative else (2, index, 0, count))
    spans = [span for span in sorted(spans) if span[3] > 0]
    total = sum(span[3] for span in spans)
    if total <= 0:
        return None
    rank = level * total
    seen = 0
    for side, order, negative, count in spans:
        if seen + count >= rank:
            fraction = (rank - seen) / count
            if side == 1:
                return 0.0
            if negative:
                return -(2 ** (-order * width + width * (1 - fraction)))
            return 2 ** (order * width + width * fraction)
        seen += count
    return None


def _rank_value(value) -> float:
    return -math.inf if value is None else value


def fetch_metric_chart(request):
    """Runs every metric series of `request` and shapes the result like any chart."""
    plan = ChartPlan(request)
    query = MetricQuery(request, plan)
    width = len(query.groups)
    source = request.source
    settings = (
        f" SETTINGS {source.data['settings']}" if source.data.get("settings") else ""
    )
    merged: Dict = {}
    with ClickhouseConnect(source.conn.data) as c:

        def run(sql, parameters):
            return _client_query(
                c.client,
                sql + settings,
                parameters=parameters,
                settings={"max_execution_time": CHART_QUERY_TIMEOUT_SECONDS},
            ).result_rows

        params = {}
        if width:
            # Only the top limit + 1 groups of the first series are read, as for column charts.
            first = request.series[0]["metric"]
            top = run(query.top_sql(first, plan.limit + 1), {"metric": first["name"]})
            params["groups"] = [tuple(r) if width > 1 else r[0] for r in top]
            query.bound = True
        for i, series in enumerate(request.series):
            if query.bound and not params["groups"]:
                break
            metric = series["metric"]
            rows = run(query.sql(metric), {**params, "metric": metric["name"]})
            for row in query.values(metric, rows):
                key = tuple(row[: width + 1])
                merged.setdefault(key, [None] * len(request.series))[i] = clean_value(
                    row[-1]
                )

    empty = [None] * len(request.series)
    if plan.kind == "number" or (plan.kind == "table" and not width):
        values = next(iter(merged.values()), empty)
        return plan.number([values]) if plan.kind == "number" else plan.table([values])
    ranked = sorted(
        merged.items(), key=lambda kv: (-_rank_value(kv[1][0]), group_key(kv[0][1:]))
    )
    if plan.kind == "table":
        return plan.table([(*k[1:], *v) for k, v in ranked])
    rows = [(*k, *v) for k, v in sorted(merged.items(), key=lambda kv: kv[0][0])]
    if not width:
        return plan.timeseries(rows)
    best = {}
    for key, values in ranked:
        best.setdefault(key[1:], _rank_value(values[0]))
    order = sorted(best, key=lambda g: (-best[g], group_key(g)))
    groups, truncated = plan.top_groups(order)
    kept = set(groups) if width > 1 else {(g,) for g in groups}
    return plan.timeseries(
        [r for r in rows if tuple(r[1 : width + 1]) in kept], groups, truncated
    )


CATALOG_LIMIT = 500
VALUES_LIMIT = 100
ATTRIBUTE_COLUMNS = ("Attributes", "ResourceAttributes")


def _catalog_query(source, sql, parameters):
    with ClickhouseConnect(source.conn.data) as c:
        return _client_query(
            c.client,
            sql,
            parameters=parameters,
            settings={"max_execution_time": CHART_QUERY_TIMEOUT_SECONDS},
        ).result_rows


def _time_range(time_from: int, time_to: int) -> str:
    return f"TimeUnix >= {_ms(time_from)} AND TimeUnix <= {_ms(time_to)}"


def metric_names(source, time_from: int, time_to: int) -> List[Dict]:
    """Metric names seen in the range, per table kind, as in HyperDX useMetricCatalog."""
    database = source.data["database"]
    result = []
    for kind, table in metric_tables(source).items():
        rows = _catalog_query(
            source,
            f"SELECT MetricName, any(MetricUnit), any(MetricDescription)"
            f" FROM `{database}`.`{table}` WHERE {_time_range(time_from, time_to)}"
            f" GROUP BY MetricName ORDER BY MetricName LIMIT {CATALOG_LIMIT}",
            {},
        )
        result += [
            {"name": n, "type": kind, "unit": u, "description": d} for n, u, d in rows
        ]
    return sorted(result, key=lambda m: (m["name"], m["type"]))


def metric_attributes(source, metric: Dict, time_from: int, time_to: int, key=None):
    """Attribute keys of one metric, or the values of `key` (e.g. `Attributes.http.route`)."""
    tables = metric_tables(source)
    if metric["type"] not in tables:
        raise ValueError(f"source has no {metric['type']} metric table")
    table = f"`{source.data['database']}`.`{tables[metric['type']]}`"
    where = f"MetricName = {{metric:String}} AND {_time_range(time_from, time_to)}"
    params = {"metric": metric["name"]}
    if key is not None:
        column, _, name = key.partition(".")
        if column not in ATTRIBUTE_COLUMNS or not name:
            raise ValueError(f"unknown attribute {key}")
        rows = _catalog_query(
            source,
            f"SELECT DISTINCT `{column}`[{{key:String}}] AS v FROM {table}"
            f" WHERE {where} AND mapContains(`{column}`, {{key:String}})"
            f" ORDER BY v LIMIT {VALUES_LIMIT}",
            {**params, "key": name},
        )
        return {"values": [r[0] for r in rows]}
    selects = " UNION ALL ".join(
        f"SELECT DISTINCT '{c}' AS c, arrayJoin(mapKeys(`{c}`)) AS k FROM {table} WHERE {where}"
        for c in ATTRIBUTE_COLUMNS
    )
    rows = _catalog_query(
        source,
        f"SELECT c, k FROM ({selects}) ORDER BY c, k LIMIT {CATALOG_LIMIT}",
        params,
    )
    return {"keys": [{"column": c, "key": k, "path": f"{c}.{k}"} for c, k in rows]}
