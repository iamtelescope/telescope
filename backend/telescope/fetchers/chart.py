import copy
import math
import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from flyql import FlyqlError, ParserError, parse
from flyql.core.expression import FunctionCall, Parameter

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
TABLE_DISPLAYS = ["table", "bar", "pie"]
QUERY_DISPLAYS = TIMESERIES_DISPLAYS + ["number"] + TABLE_DISPLAYS
CHART_DISPLAYS = QUERY_DISPLAYS + ["text"]
# Displays that draw one value per group or tile; extra series must be hidden formula operands.
SINGLE_SERIES_DISPLAYS = ["number", "bar", "pie"]
GROUPED_DISPLAYS = ["bar", "pie"]
CHART_AGGS = [
    "count",
    "sum",
    "avg",
    "min",
    "max",
    "quantile",
    "uniq",
    "last_value",
    "any",
    "formula",
]
QUANTILE_LEVELS = [0.5, 0.75, 0.9, 0.95, 0.99]
ZERO_FILL_AGGS = {"count", "sum", "uniq"}
NONE_GROUP = "__none__"
MAX_GROUP_BY = 3
GROUP_SEPARATOR = " · "

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


def chart_range_error(time_from: int, time_to: int, granularity: str = "auto"):
    _, step_ms = pick_granularity(time_from, time_to, granularity)
    if _bucket_count(time_from, time_to, step_ms) > CHART_MAX_POINTS:
        return (
            f"time range is too long for a time chart, at most {CHART_MAX_POINTS} days"
        )
    return None


def align_range(time_from: int, time_to: int, step_ms: int) -> Tuple[int, int]:
    return (time_from // step_ms) * step_ms, -(-time_to // step_ms) * step_ms


def quote_column(source, name: str) -> str:
    if name not in source._columns:
        raise ValueError(f"unknown column {name}")
    return "`" + name.replace("`", "``") + "`"


def quantile_level(level) -> float:
    return QUANTILE_LEVELS[QUANTILE_LEVELS.index(float(level))]


def agg_expression(
    templates: Dict[str, str], source, series: Dict, where: Optional[str] = None
) -> str:
    """`where` is the series' own condition as SQL; it picks the `<agg>_if` template."""
    agg = series["agg"]
    key = f"{agg}_if" if where else agg
    if agg == "count":
        return templates[key].format(w=where)
    level = repr(quantile_level(series["level"])) if agg == "quantile" else ""
    return templates[key].format(
        c=quote_column(source, series["column"]),
        l=level,
        t=quote_column(source, source.time_column),
        w=where,
    )


def series_label(series: Dict) -> str:
    if series.get("alias"):
        return series["alias"]
    agg = series["agg"]
    if agg == "count":
        return "count()"
    if agg == "formula":
        return series["formula"]
    if agg == "quantile":
        return f"p{round(float(series['level']) * 100)}({series['column']})"
    return f"{agg}({series['column']})"


def visible_index(series: List[Dict]) -> int:
    """The series a single-value display shows: the first not hidden one."""
    return next((i for i, s in enumerate(series) if not s.get("hidden")), 0)


def series_name(label: str, group, count: int) -> str:
    if group is None:
        return label
    return group if count == 1 else f"{label}{GROUP_SEPARATOR}{group}"


class ChartResult(ChartDataResponse):
    """A chart response with v2 fields; `extra` keys are only sent when set."""

    def __init__(self, *args, extra: Optional[Dict] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra = extra or {}

    def as_dict(self) -> Dict:
        data = super().as_dict()
        data.update(self.extra)
        return data


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


def group_key(parts) -> str:
    return GROUP_SEPARATOR.join(group_name(p) for p in parts)


class ChartPlan:
    """Time range, step and response shaping for one chart data request."""

    def __init__(self, request):
        self.request = request
        self.series = request.series
        self.limit = request.limit
        self.group_bys = list(request.group_by or [])
        self.group_by = self.group_bys[0] if self.group_bys else None
        # Width of the group key in result rows.
        self.group_width = len(self.group_bys)
        self.granularity = None
        self.step_ms = None
        self.time_from = request.time_from
        self.time_to = request.time_to
        self.query_to = request.time_to
        if request.display in TIMESERIES_DISPLAYS:
            self.kind = "timeseries"
            error = chart_range_error(
                request.time_from, request.time_to, request.granularity
            )
            if error:
                raise ValueError(error)
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
        """Group values to bind for the main query: plain for one column, tuples for several."""
        if self.group_width > 1:
            groups = [tuple(row[: self.group_width]) for row in rows]
        else:
            groups = [row[0] for row in rows]
        return groups[: self.limit], len(groups) > self.limit

    def _split_group(self, row, start: int):
        """(key, parts, values) of a row whose group columns start at `start`."""
        width = self.group_width
        if not width:
            return None, None, row[start:]
        parts = row[start : start + width]
        return group_key(parts), parts, row[start + width :]

    def _group_parts(self, group) -> List[str]:
        return [group_name(p) for p in (group if self.group_width > 1 else [group])]

    def timeseries(
        self, rows, groups: Optional[List] = None, truncated: bool = False
    ) -> ChartDataResponse:
        timestamps = list(range(self.time_from, self.time_to, self.step_ms))
        index = {ts: i for i, ts in enumerate(timestamps)}
        if self.group_by:
            order = [group_key(self._group_parts(g)) for g in groups or []]
            parts_of = {
                group_key(self._group_parts(g)): self._group_parts(g)
                for g in groups or []
            }
        else:
            order = [None]
            parts_of = {}
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
            group, parts, row_values = self._split_group(row, 1)
            if group not in values:
                values[group] = empty()
                if group not in order:
                    order.append(group)
                    if parts is not None:
                        parts_of[group] = [group_name(p) for p in parts]
            for i, value in enumerate(row_values):
                values[group][i][index[ts]] = self._value(self.series[i], value)

        series = []
        for group in order:
            group_values = values.get(group) or empty()
            for i, item in enumerate(self.series):
                entry = {
                    "name": series_name(series_label(item), group, len(self.series)),
                    "group": group,
                    "series_index": i,
                    "values": group_values[i],
                }
                if self.group_width > 1:
                    entry["groups"] = parts_of.get(group, [])
                series.append(entry)
        return ChartResult(
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
        row = rows[0] if rows else [None] * len(self.series)
        values = [self._value(s, row[i]) for i, s in enumerate(self.series)]
        extra = {"values": values} if len(values) > 1 else {}
        return ChartResult(
            kind="number",
            time_from=self.time_from,
            time_to=self.time_to,
            value=values[visible_index(self.series)],
            extra=extra,
        )

    def table(self, rows) -> ChartDataResponse:
        rows = list(rows)
        truncated = len(rows) > self.limit
        result = []
        for row in rows[: self.limit]:
            group, parts, row_values = self._split_group(row, 0)
            item = {
                "group": "" if group is None else group,
                "values": [
                    self._value(self.series[i], v) for i, v in enumerate(row_values)
                ],
            }
            if self.group_width > 1:
                item["groups"] = [group_name(p) for p in parts]
            result.append(item)
        group_column = {"name": "", "kind": "group"}
        if self.group_bys:
            group_column["name"] = GROUP_SEPARATOR.join(g.name for g in self.group_bys)
        if self.group_width > 1:
            group_column["names"] = [g.name for g in self.group_bys]
        columns = [group_column]
        columns += [{"name": series_label(s), "kind": "value"} for s in self.series]
        return ChartResult(
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
            return self.number([(len(rows),) * n])

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


# Formula grammar and missing-data semantics adapted from HyperDX common-utils/src/core/formula.ts (MIT):
# expression := term (('+'|'-') term)*; term := factor (('*'|'/') factor)*; factor := '-' factor | primary.
FORMULA_MAX_LENGTH = 1024
FORMULA_MAX_DEPTH = 64
FORMULA_TOKEN_RE = re.compile(
    r"\s*(?:(\d+(?:\.\d*)?|\.\d+)|([A-Za-z_][A-Za-z0-9_]*)|([-+*/()]))"
)


class FormulaError(ValueError):
    pass


def _tokenize_formula(text: str) -> List[Tuple[str, object]]:
    tokens, pos = [], 0
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        match = FORMULA_TOKEN_RE.match(text, pos)
        if not match:
            raise FormulaError(f"unexpected character {text[pos:].strip()[0]!r}")
        number, name, op = match.groups()
        if number is not None:
            tokens.append(("num", float(number)))
        elif name is not None:
            tokens.append(("ref", name))
        else:
            tokens.append(("op", op))
        pos = match.end()
    return tokens


def parse_formula(text: str, names) -> Tuple:
    """A validated AST over series `names`: ("num", v), ("ref", name), ("neg", a) or (op, a, b)."""
    if not text or not text.strip():
        raise FormulaError("formula is empty")
    if len(text) > FORMULA_MAX_LENGTH:
        raise FormulaError(f"formula is longer than {FORMULA_MAX_LENGTH} characters")
    tokens = _tokenize_formula(text)
    pos = 0
    refs = set()

    def peek():
        return tokens[pos] if pos < len(tokens) else (None, None)

    def take():
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def binary(next_level, ops, depth):
        node = next_level(depth)
        while peek() in [("op", o) for o in ops]:
            op = take()[1]
            node = (op, node, next_level(depth))
        return node

    def expression(depth):
        if depth > FORMULA_MAX_DEPTH:
            raise FormulaError("formula is nested too deeply")
        return binary(term, "+-", depth)

    def term(depth):
        return binary(factor, "*/", depth)

    def factor(depth):
        kind, value = peek()
        if (kind, value) == ("op", "-"):
            take()
            if depth > FORMULA_MAX_DEPTH:
                raise FormulaError("formula is nested too deeply")
            return ("neg", factor(depth + 1))
        if kind == "num":
            take()
            return ("num", value)
        if kind == "ref":
            take()
            if value not in names:
                raise FormulaError(f"unknown series {value}, use a series alias")
            refs.add(value)
            return ("ref", value)
        if (kind, value) == ("op", "("):
            take()
            node = expression(depth + 1)
            if peek() != ("op", ")"):
                raise FormulaError("missing )")
            take()
            return node
        raise FormulaError(
            "unexpected end of formula" if kind is None else f"unexpected {value}"
        )

    ast = expression(0)
    if pos != len(tokens):
        raise FormulaError(f"unexpected {tokens[pos][1]}")
    if not refs:
        raise FormulaError("formula must reference at least one series")
    return ast


def eval_formula(ast, env: Dict) -> Optional[float]:
    """A missing operand counts as 0; a zero or missing divisor makes the result null."""

    def run(node):
        kind = node[0]
        if kind == "num":
            return node[1]
        if kind == "ref":
            value = env.get(node[1])
            return 0.0 if value is None else float(value)
        if kind == "neg":
            value = run(node[1])
            return None if value is None else -value
        left, right = run(node[1]), run(node[2])
        if left is None or right is None:
            return None
        if kind == "+":
            return left + right
        if kind == "-":
            return left - right
        if kind == "*":
            return left * right
        return None if right == 0 else left / right

    return clean_value(run(ast))


def formula_names(series: List[Dict]) -> Dict[str, int]:
    """Alias -> index of the query series a formula may reference."""
    return {
        s["alias"]: i
        for i, s in enumerate(series)
        if s["agg"] != "formula" and s.get("alias")
    }


def with_formulas(request, run) -> ChartDataResponse:
    """Runs the query series through `run` and adds formula series over the aligned result."""
    series = request.series
    query_index = [i for i, s in enumerate(series) if s["agg"] != "formula"]
    if len(query_index) == len(series):
        return run(request)
    names = formula_names(series)
    asts = {
        i: parse_formula(s["formula"], names)
        for i, s in enumerate(series)
        if s["agg"] == "formula"
    }
    sub = copy.copy(request)
    sub.series = [series[i] for i in query_index]
    result = run(sub)

    def full(values):
        """All series values in request order, from the query series values."""
        out = [None] * len(series)
        for k, i in enumerate(query_index):
            out[i] = values[k]
        env = {name: out[i] for name, i in names.items()}
        for i, ast in asts.items():
            out[i] = eval_formula(ast, env)
        return out

    if result.kind == "number":
        values = full(result.extra.get("values") or [result.value])
        result.value = values[visible_index(series)]
        result.extra["values"] = values
    elif result.kind == "table":
        for row in result.rows:
            row["values"] = full(row["values"])
        result.columns = result.columns[:1] + [
            {"name": series_label(s), "kind": "value"} for s in series
        ]
    else:
        by_group = {}
        for item in result.series:
            by_group.setdefault(item["group"], []).append(item)
        out = []
        for group, items in by_group.items():
            width = len(result.timestamps)
            columns = [full([it["values"][t] for it in items]) for t in range(width)]
            for i, item in enumerate(series):
                entry = {
                    **{k: v for k, v in items[0].items() if k == "groups"},
                    "name": series_name(series_label(item), group, len(series)),
                    "group": group,
                    "series_index": i,
                    "values": [columns[t][i] for t in range(width)],
                }
                out.append(entry)
        result.series = out
    return result


def _shifted(request, span: int, **changes):
    shifted = copy.copy(request)
    shifted.time_from = request.time_from - span
    shifted.time_to = request.time_to - span
    for key, value in changes.items():
        setattr(shifted, key, value)
    return shifted


def _extra(result) -> Dict:
    if not hasattr(result, "extra"):
        result.extra = {}
    return result.extra


def fetch_chart(fetcher, request, compare: bool = False, sparkline: bool = False):
    """The chart response plus the previous period (`compare`) and a number tile's `sparkline`."""
    result = fetcher.fetch_chart_data(request)
    if compare and result.kind == "timeseries":
        span = result.time_to - result.time_from
        previous = fetcher.fetch_chart_data(
            _shifted(request, span, granularity=result.granularity)
        )
        empty = [None] * len(result.timestamps)
        by_key = {(s["group"], s["series_index"]): s["values"] for s in previous.series}
        result.series = result.series + [
            {
                **s,
                "name": f"{s['name']} (previous)",
                "values": (by_key.get((s["group"], s["series_index"])) or empty)[
                    : len(empty)
                ],
                "previous": True,
            }
            for s in result.series
        ]
        _extra(result)["previous_offset_ms"] = span
    elif compare and result.kind == "number":
        span = request.time_to - request.time_from
        previous = fetcher.fetch_chart_data(_shifted(request, span))
        _extra(result).update(previous_value=previous.value, previous_offset_ms=span)
    if sparkline and result.kind == "number":
        line = copy.copy(request)
        line.display, line.granularity, line.group_by = "line", "auto", []
        try:
            points = fetcher.fetch_chart_data(line)
        except ValueError:
            return result
        index = visible_index(request.series)
        values = next(
            (s["values"] for s in points.series if s["series_index"] == index), []
        )
        _extra(result)["sparkline"] = {
            "timestamps": points.timestamps,
            "values": values,
        }
    return result


VARIABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
MULTI_VALUE_OPERATORS = {"=": "in", "!=": "not in"}


class VariableError(ValueError):
    def __init__(self, name: str, message: str):
        super().__init__(message)
        self.name = name
        self.message = message


def flyql_literal(name: str, value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value)
    # FlyQL strings drop line breaks and read a trailing backslash as an escape.
    if "\n" in text or "\r" in text or text.endswith("\\"):
        raise VariableError(
            name, "a value cannot contain a line break or end with a backslash"
        )
    return "'" + text.replace("'", "\\'") + "'"


def _param_values(param: Parameter, params: Dict) -> List:
    if param.positional or param.name not in params:
        raise VariableError(param.name, f"no value for ${param.name}")
    value = params[param.name]
    values = value if isinstance(value, list) else [value]
    return [v for v in values if v is not None and v != ""]


def _bind_expression(text: str, expr, params: Dict) -> Optional[str]:
    """Bound text of one expression, or None when an empty variable drops it."""
    start, end = expr.key.range.start, expr.range.end
    edits = []
    if isinstance(expr.value, Parameter):
        name = expr.value.name
        values = _param_values(expr.value, params)
        if not values:
            return None
        literals = [flyql_literal(name, v) for v in values]
        if len(literals) == 1:
            edits.append((expr.value_range.start, expr.value_range.end, literals[0]))
        elif expr.operator in MULTI_VALUE_OPERATORS:
            operator = MULTI_VALUE_OPERATORS[expr.operator]
            edits.append(
                (
                    expr.operator_range.start,
                    expr.value_range.end,
                    f"{operator} [{', '.join(literals)}]",
                )
            )
        else:
            raise VariableError(
                name, f"several values need = or != instead of {expr.operator}"
            )
    elif isinstance(expr.value, FunctionCall) and expr.value.parameter_args:
        name = expr.value.parameter_args[0].name
        raise VariableError(name, f"${name} cannot be used inside a function")
    elif expr.values and any(isinstance(v, Parameter) for v in expr.values):
        items = []
        for value, value_range in zip(expr.values, expr.value_ranges):
            if isinstance(value, Parameter):
                items += [
                    flyql_literal(value.name, v) for v in _param_values(value, params)
                ]
            else:
                items.append(text[value_range.start : value_range.end])
        if not items:
            return None
        first, last = expr.value_ranges[0], expr.value_ranges[-1]
        edits.append((first.start, last.end, ", ".join(items)))
    result = text[start:end]
    for edit_start, edit_end, replacement in sorted(edits, reverse=True):
        result = result[: edit_start - start] + replacement + result[edit_end - start :]
    return result


def _bind_node(text: str, node, params: Dict) -> Optional[str]:
    if node.expression is not None:
        body = _bind_expression(text, node.expression, params)
    else:
        parts = [
            part
            for part in (
                _bind_node(text, child, params)
                for child in (node.left, node.right)
                if child is not None
            )
            if part is not None
        ]
        if not parts:
            return None
        body = (
            parts[0]
            if len(parts) == 1
            else f"({parts[0]} {node.bool_operator} {parts[1]})"
        )
    if body is None:
        return None
    return f"not {body}" if node.negated else body


def _has_params(node) -> bool:
    if node is None:
        return False
    expr = node.expression
    if expr is not None:
        return (
            isinstance(expr.value, Parameter)
            or (
                isinstance(expr.value, FunctionCall) and bool(expr.value.parameter_args)
            )
            or any(isinstance(v, Parameter) for v in expr.values or [])
        )
    return _has_params(node.left) or _has_params(node.right)


def bind_query(query: str, params: Dict) -> str:
    """Substitutes `$name` values into a FlyQL query and returns FlyQL text.

    A list binds as `in [...]`; an empty value drops the expression that uses it.
    """
    if not query or "$" not in query:
        return query
    try:
        root = parse(query).root
    except (ParserError, FlyqlError):
        return query
    if not _has_params(root):
        return query
    return _bind_node(query, root, params or {}) or ""
