import math
import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from telescope.constants import (
    CHART_AUTO_BUCKETS,
    CHART_MAX_POINTS,
    SOURCE_KIND_CLICKHOUSE,
)
from telescope.fetchers.response import ChartDataResponse

GRANULARITY_SECONDS = {
    "15s": 15,
    "30s": 30,
    "1m": 60,
    "5m": 300,
    "10m": 600,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "6h": 21600,
    "12h": 43200,
    "1d": 86400,
}
# 10m is skipped so every step is a multiple of all smaller ones, as in HyperDX.
STANDARD_STEPS = [name for name in GRANULARITY_SECONDS if name != "10m"]
GRANULARITIES = ["auto"] + list(GRANULARITY_SECONDS)

TIMESERIES_DISPLAYS = ["line", "stacked_area", "stacked_bar"]
TABLE_DISPLAYS = ["table", "bar"]
QUERY_DISPLAYS = TIMESERIES_DISPLAYS + ["number"] + TABLE_DISPLAYS
CHART_DISPLAYS = QUERY_DISPLAYS + ["text"]
CHART_AGGS = ["count", "sum", "avg", "min", "max", "quantile", "uniq"]
QUANTILE_LEVELS = [0.5, 0.75, 0.9, 0.95, 0.99]
ZERO_FILL_AGGS = {"count", "sum", "uniq"}
NONE_GROUP = "__none__"

TYPE_WRAPPER_RE = re.compile(r"^(nullable|lowcardinality)\((.*)\)$", re.IGNORECASE)
CLICKHOUSE_NUMERIC_RE = re.compile(r"^(U?Int\d+|Float\d+|Decimal.*)$", re.IGNORECASE)
STARROCKS_NUMERIC_RE = re.compile(
    r"^((tinyint|smallint|int|bigint|largeint|float|double)(\(\d+\))?|decimal.*)$",
    re.IGNORECASE,
)


def is_numeric_column_type(kind: str, column_type: str) -> bool:
    value = (column_type or "").strip()
    while True:
        match = TYPE_WRAPPER_RE.match(value)
        if not match:
            break
        value = match.group(2).strip()
    if kind == SOURCE_KIND_CLICKHOUSE:
        return bool(CLICKHOUSE_NUMERIC_RE.match(value))
    if kind == "starrocks":
        return bool(STARROCKS_NUMERIC_RE.match(value))
    return False


def _bucket_count(time_from: int, time_to: int, step_ms: int) -> int:
    aligned_from, aligned_to = align_range(time_from, time_to, step_ms)
    return (aligned_to - aligned_from) // step_ms


def pick_granularity(
    time_from: int, time_to: int, granularity: str = "auto"
) -> Tuple[str, int]:
    # Auto step ported from HyperDX convertDateRangeToGranularityString (MIT).
    if granularity == "auto":
        diff_seconds = (time_to - time_from) // 1000
        size = math.ceil(diff_seconds / CHART_AUTO_BUCKETS)
        granularity = next(
            (s for s in STANDARD_STEPS if GRANULARITY_SECONDS[s] >= size), "1d"
        )
    step_ms = GRANULARITY_SECONDS[granularity] * 1000
    if _bucket_count(time_from, time_to, step_ms) > CHART_MAX_POINTS:
        granularity = next(
            (
                s
                for s in STANDARD_STEPS
                if GRANULARITY_SECONDS[s] * 1000 > step_ms
                and _bucket_count(time_from, time_to, GRANULARITY_SECONDS[s] * 1000)
                <= CHART_MAX_POINTS
            ),
            "1d",
        )
    return granularity, GRANULARITY_SECONDS[granularity] * 1000


def align_range(time_from: int, time_to: int, step_ms: int) -> Tuple[int, int]:
    return (time_from // step_ms) * step_ms, -(-time_to // step_ms) * step_ms


def quote_column(source, name: str) -> str:
    if name not in source._columns:
        raise ValueError(f"unknown column {name}")
    return "`" + name.replace("`", "``") + "`"


def quantile_level(level) -> float:
    return QUANTILE_LEVELS[QUANTILE_LEVELS.index(float(level))]


def agg_expression(templates: Dict[str, str], source, series: Dict) -> str:
    agg = series["agg"]
    if agg == "count":
        return templates["count"]
    level = repr(quantile_level(series["level"])) if agg == "quantile" else ""
    return templates[agg].format(c=quote_column(source, series["column"]), l=level)


def series_label(series: Dict) -> str:
    if series.get("alias"):
        return series["alias"]
    agg = series["agg"]
    if agg == "count":
        return "count()"
    if agg == "quantile":
        return f"p{round(float(series['level']) * 100)}({series['column']})"
    return f"{agg}({series['column']})"


def clean_value(value):
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def group_name(value) -> str:
    if value is None or value == "":
        return NONE_GROUP
    return str(value)


class ChartPlan:
    """Time range, step and response shaping for one chart data request."""

    def __init__(self, request):
        self.request = request
        self.series = request.series
        self.limit = request.limit
        self.group_by = request.group_by[0] if request.group_by else None
        self.granularity = None
        self.step_ms = None
        self.time_from = request.time_from
        self.time_to = request.time_to
        self.query_to = request.time_to
        if request.display in TIMESERIES_DISPLAYS:
            self.kind = "timeseries"
            self.granularity, self.step_ms = pick_granularity(
                request.time_from, request.time_to, request.granularity
            )
            self.time_from, self.time_to = align_range(
                request.time_from, request.time_to, self.step_ms
            )
            # Buckets are half-open, so the last millisecond belongs to the grid.
            self.query_to = self.time_to - 1
        elif request.display == "number":
            self.kind = "number"
        else:
            self.kind = "table"

    def _value(self, series: Dict, value):
        value = clean_value(value)
        if value is None and series["agg"] in ZERO_FILL_AGGS:
            return 0
        return value

    def top_groups(self, rows) -> Tuple[List, bool]:
        groups = [row[0] for row in rows]
        return groups[: self.limit], len(groups) > self.limit

    def timeseries(
        self, rows, groups: Optional[List] = None, truncated: bool = False
    ) -> ChartDataResponse:
        timestamps = list(range(self.time_from, self.time_to, self.step_ms))
        index = {ts: i for i, ts in enumerate(timestamps)}
        if self.group_by:
            order = [group_name(g) for g in groups or []]
        else:
            order = [None]
        values = {}

        def empty():
            return [
                [0 if s["agg"] in ZERO_FILL_AGGS else None for _ in timestamps]
                for s in self.series
            ]

        for row in rows:
            ts = int(row[0]) // self.step_ms * self.step_ms
            if ts not in index:
                continue
            if self.group_by:
                group, row_values = group_name(row[1]), row[2:]
            else:
                group, row_values = None, row[1:]
            if group not in values:
                values[group] = empty()
                if group not in order:
                    order.append(group)
            for i, value in enumerate(row_values):
                values[group][i][index[ts]] = self._value(self.series[i], value)

        series = []
        for group in order:
            group_values = values.get(group) or empty()
            for i, item in enumerate(self.series):
                label = series_label(item)
                if group is None:
                    name = label
                elif len(self.series) == 1:
                    name = group
                else:
                    name = f"{label} · {group}"
                series.append(
                    {
                        "name": name,
                        "group": group,
                        "series_index": i,
                        "values": group_values[i],
                    }
                )
        return ChartDataResponse(
            kind="timeseries",
            time_from=self.time_from,
            time_to=self.time_to,
            granularity=self.granularity,
            step_ms=self.step_ms,
            timestamps=timestamps,
            series=series,
            truncated=truncated,
        )

    def number(self, rows) -> ChartDataResponse:
        value = rows[0][0] if rows else None
        return ChartDataResponse(
            kind="number",
            time_from=self.time_from,
            time_to=self.time_to,
            value=self._value(self.series[0], value),
        )

    def table(self, rows) -> ChartDataResponse:
        rows = list(rows)
        truncated = len(rows) > self.limit
        result = []
        for row in rows[: self.limit]:
            if self.group_by:
                group, row_values = group_name(row[0]), row[1:]
            else:
                group, row_values = "", row
            result.append(
                {
                    "group": group,
                    "values": [
                        self._value(self.series[i], v) for i, v in enumerate(row_values)
                    ],
                }
            )
        columns = [
            {"name": self.group_by.name if self.group_by else "", "kind": "group"}
        ]
        columns += [{"name": series_label(s), "kind": "value"} for s in self.series]
        return ChartDataResponse(
            kind="table",
            time_from=self.time_from,
            time_to=self.time_to,
            columns=columns,
            rows=result,
            truncated=truncated,
        )

    def count_rows(self, rows, group_value) -> ChartDataResponse:
        """Count-only charts over rows already fetched in Python (docker, kubernetes)."""
        for item in self.series:
            if item["agg"] != "count":
                raise ValueError(
                    f"aggregation {item['agg']} is not supported for {self.request.source.kind} sources"
                )
        n = len(self.series)
        if self.kind == "number":
            return self.number([(len(rows),)])

        totals = {}
        buckets = {}
        for row in rows:
            group = group_value(row) if self.group_by else None
            totals[group] = totals.get(group, 0) + 1
            if self.kind == "timeseries":
                ts = row.time["unixtime"] // self.step_ms * self.step_ms
                buckets[(ts, group)] = buckets.get((ts, group), 0) + 1
        ranked = sorted(totals, key=lambda g: (-totals[g], str(g)))

        if self.kind == "table":
            if not self.group_by:
                return self.table([(len(rows),) * n])
            return self.table([(g,) + (totals[g],) * n for g in ranked])

        if not self.group_by:
            return self.timeseries(
                [(ts, *(count,) * n) for (ts, _), count in buckets.items()]
            )
        groups, truncated = self.top_groups([(g,) for g in ranked])
        kept = set(groups)
        return self.timeseries(
            [(ts, g, *(count,) * n) for (ts, g), count in buckets.items() if g in kept],
            groups,
            truncated,
        )
