"""Raw SQL macros, ported from HyperDX common-utils/src/macros.ts and rawSqlParams.ts (MIT).

Each macro expands to ClickHouse query parameters, so the time range is bound, never interpolated.
"""

import re

FROM_MS = "{startDateMilliseconds:Int64}"
TO_MS = "{endDateMilliseconds:Int64}"
INTERVAL_S = "{intervalSeconds:Int64}"
INTERVAL_MS = "{intervalMilliseconds:Int64}"
MACRO_PARAMS = [
    "startDateMilliseconds",
    "endDateMilliseconds",
    "intervalSeconds",
    "intervalMilliseconds",
]


def _date(ms):
    return f"toDate(fromUnixTimestamp64Milli({ms}))"


def _datetime(ms):
    return f"toDateTime(fromUnixTimestamp64Milli({ms}))"


def _datetime64(ms):
    return f"fromUnixTimestamp64Milli({ms})"


def _between(col, convert):
    return f"{col} >= {convert(FROM_MS)} AND {col} <= {convert(TO_MS)}"


# name -> (argument count, expansion)
MACROS = {
    "fromTime": (0, lambda: _datetime(FROM_MS)),
    "toTime": (0, lambda: _datetime(TO_MS)),
    "fromTime_ms": (0, lambda: _datetime64(FROM_MS)),
    "toTime_ms": (0, lambda: _datetime64(TO_MS)),
    "timeFilter": (1, lambda col: _between(col, _datetime)),
    "timeFilter_ms": (1, lambda col: _between(col, _datetime64)),
    "dateFilter": (1, lambda col: _between(col, _date)),
    "timeInterval": (
        1,
        lambda col: f"toStartOfInterval(toDateTime({col}), INTERVAL {INTERVAL_S} second)",
    ),
    "timeInterval_ms": (
        1,
        lambda col: f"toStartOfInterval(toDateTime64({col}, 3), INTERVAL {INTERVAL_MS} millisecond)",
    ),
    "interval_s": (0, lambda: INTERVAL_S),
}

MACRO_RE = re.compile(r"\$__([A-Za-z_][A-Za-z0-9_]*)")


class MacroError(Exception):
    pass


def scan(text: str, start: int):
    """Yields (index, char) outside quotes and comments, so a ')' or ';' in either does not count."""
    quote, depth, i = None, 0, start
    while i < len(text):
        c, pair = text[i], text[i : i + 2]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif pair == "/*":
            # ClickHouse nests block comments.
            depth += 1
            i += 1
        elif depth:
            if pair == "*/":
                depth -= 1
                i += 1
        elif pair in ("--", "# ", "#!"):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        elif c in "'\"`":
            quote = c
        else:
            yield i, c
        i += 1


def _split_args(text: str, start: int):
    """Arguments of the call whose '(' is at `start`, and the index after its ')'."""
    depth, args, last = 0, [], start + 1
    for i, c in scan(text, start):
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
            if depth == 0:
                args.append(text[last:i].strip())
                return ([] if args == [""] else args), i + 1
        elif c == "," and depth == 1:
            args.append(text[last:i].strip())
            last = i + 1
    raise MacroError("unbalanced parentheses in macro arguments")


def expand_macros(sql: str) -> str:
    """Replaces every `$__name` and `$__name(args)`; arguments are expanded first."""
    out, pos = [], 0
    while True:
        match = MACRO_RE.search(sql, pos)
        if not match:
            out.append(sql[pos:])
            return "".join(out)
        name = match.group(1)
        out.append(sql[pos : match.start()])
        if name not in MACROS:
            # Unknown names stay as written, as in HyperDX.
            out.append(match.group(0))
            pos = match.end()
            continue
        count, expand = MACROS[name]
        pos = match.end()
        args = []
        if pos < len(sql) and sql[pos] == "(":
            args, pos = _split_args(sql, pos)
        if len(args) != count:
            raise MacroError(
                f"macro $__{name} expects {count} argument(s), but got {len(args)}"
            )
        out.append(expand(*[expand_macros(a) for a in args]))
