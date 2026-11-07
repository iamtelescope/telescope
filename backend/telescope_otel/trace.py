# Trace waterfall: span lookup, tree build, critical path and linked logs for OTel sources.
# Tree build and error rules adapted from HyperDX DBTraceWaterfallChart.tsx and core/spanPredicates.ts.

import time

from telescope.fetchers.clickhouse import ClickhouseConnect, _client_query

SPAN_LIMIT = 5000
LOG_LIMIT = 5000
AROUND_MS = 3600 * 1000
DEFAULT_LOOKUP_MS = 24 * 3600 * 1000
ERROR_STATUS_CODES = ("error", "status_code_error")
EMPTY_PARENTS = ("", "0000000000000000")


class TraceError(Exception):
    pass


def is_error_status(code):
    return bool(code) and str(code).lower() in ERROR_STATUS_CODES


def _q(name):
    return "`" + name.replace("`", "``") + "`"


def _ns(expr):
    return f"toUnixTimestamp64Nano(toDateTime64({expr}, 9))"


def otel_roles(source, signal, required):
    otel = (source.data or {}).get("otel") or {}
    if source.kind != "clickhouse" or otel.get("signal") != signal:
        raise TraceError(f"source {source.slug} is not an OTel {signal} source")
    roles = dict(otel.get("roles") or {})
    roles.setdefault("timestamp", source.time_column)
    missing = [r for r in required if not roles.get(r)]
    if missing:
        raise TraceError(f"source {source.slug} has no {missing[0]} role")
    return roles


def lookup_window(around_ms=None, now_ms=None):
    """[from, to] in ms: around ± 1h, or the last 24h."""
    if around_ms is not None:
        return around_ms - AROUND_MS, around_ms + AROUND_MS
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    return now_ms - DEFAULT_LOOKUP_MS, now_ms


def _settings(source):
    s = source.data.get("settings")
    return f" SETTINGS {s}" if s else ""


def _table(source):
    return f"{_q(source.data['database'])}.{_q(source.data['table'])}"


def _select_trace(source, roles, trace_id, window, select, order, limit):
    """Rows of one trace: find its min/max time inside `window`, then read that range."""
    ts = _q(roles["timestamp"])
    where = f"{_q(roles['trace_id'])} = {{trace_id:String}}"
    params = {"trace_id": trace_id, "from": window[0], "to": window[1]}
    window_clause = (
        f"{ts} BETWEEN fromUnixTimestamp64Milli({{from:Int64}})"
        " AND fromUnixTimestamp64Milli({to:Int64})"
    )
    if source.date_column:
        window_clause += (
            f" AND {_q(source.date_column)} BETWEEN toDate(fromUnixTimestamp64Milli({{from:Int64}}))"
            " AND toDate(fromUnixTimestamp64Milli({to:Int64}))"
        )
    with ClickhouseConnect(source.conn.data) as c:
        count, lo, hi = _client_query(
            c.client,
            f"SELECT count(), {_ns(f'min({ts})')}, {_ns(f'max({ts})')} FROM {_table(source)}"
            f" WHERE {where} AND {window_clause}{_settings(source)}",
            parameters=params,
        ).result_rows[0]
        if not count:
            return [], False
        params.update(lo=lo, hi=hi)
        range_clause = f"{ts} BETWEEN fromUnixTimestamp64Nano({{lo:Int64}}) AND fromUnixTimestamp64Nano({{hi:Int64}})"
        if source.date_column:
            range_clause += (
                f" AND {_q(source.date_column)} BETWEEN toDate(fromUnixTimestamp64Nano({{lo:Int64}}))"
                " AND toDate(fromUnixTimestamp64Nano({hi:Int64}))"
            )
        rows = _client_query(
            c.client,
            f"SELECT {', '.join(select)} FROM {_table(source)} WHERE {where} AND {range_clause}"
            f" ORDER BY {order} LIMIT {limit + 1}{_settings(source)}",
            parameters=params,
        ).result_rows
    return rows[:limit], len(rows) > limit


def _col(roles, role, default="''"):
    return _q(roles[role]) if roles.get(role) else default


def _span_select(roles):
    ts = _q(roles["timestamp"])
    events, links = roles.get("events"), roles.get("links")
    return [
        _q(roles["span_id"]),
        _q(roles["parent_span_id"]),
        _col(roles, "span_name"),
        _col(roles, "span_kind"),
        _col(roles, "service"),
        _ns(ts),
        _q(roles["duration"]),
        _col(roles, "status_code"),
        _col(roles, "status_message"),
        _col(roles, "attrs", "map()"),
        _col(roles, "resource_attrs", "map()"),
        (
            f"arrayMap(x -> {_ns('x')}, {_q(events + '.Timestamp')}), {_q(events + '.Name')},"
            f" {_q(events + '.Attributes')}"
            if events
            else "[], [], []"
        ),
        (
            f"{_q(links + '.TraceId')}, {_q(links + '.SpanId')}, {_q(links + '.TraceState')},"
            f" {_q(links + '.Attributes')}"
            if links
            else "[], [], [], []"
        ),
    ]


def _map(value):
    return {str(k): v for k, v in (value or {}).items()}


def build_tree(spans):
    """Spans in display order (depth-first, children by start) with depth, parent and
    child counts. Spans whose parent is missing go under one synthetic span per missing id.
    """
    first = {}
    for s in spans:
        first.setdefault(s["id"], s)
    children = {}
    roots, orphans = [], {}
    for s in spans:
        parent = s["parent_id"]
        if parent in EMPTY_PARENTS:
            roots.append(s)
        elif parent in first:
            children.setdefault(first[parent]["_key"], []).append(s)
        else:
            orphans.setdefault(parent, []).append(s)
    for parent, kids in orphans.items():
        start = min(k["offset_ns"] for k in kids)
        end = max(k["offset_ns"] + k["duration_ns"] for k in kids)
        node = synthetic_span(parent, start, end - start)
        node["_key"] = ("synthetic", parent)
        children[node["_key"]] = kids
        roots.append(node)

    by_start = lambda s: s["offset_ns"]
    ordered, seen = [], set()

    def walk(top):
        stack = [(top, 0, None)]
        while stack:
            node, depth, parent = stack.pop()
            if node["_key"] in seen:
                continue
            seen.add(node["_key"])
            node.update(depth=depth, parent=parent, index=len(ordered), children=0)
            ordered.append(node)
            if parent is not None:
                ordered[parent]["children"] += 1
            for kid in sorted(
                children.get(node["_key"], []), key=by_start, reverse=True
            ):
                stack.append((kid, depth + 1, node["index"]))

    for root in sorted(roots, key=by_start):
        walk(root)
    # Parent cycles leave spans unreachable from any root; show them as roots.
    for s in spans:
        if s["_key"] not in seen:
            walk(s)
    for node in ordered:
        node.pop("_key")
    critical_path(ordered)
    return ordered


def synthetic_span(span_id, offset_ns, duration_ns):
    return {
        "id": span_id,
        "parent_id": "",
        "synthetic": True,
        "name": "missing span",
        "kind": "",
        "service": "",
        "offset_ns": offset_ns,
        "duration_ns": duration_ns,
        "status_code": "",
        "status_message": "",
        "error": False,
        "attributes": {},
        "resource": {},
        "events": [],
        "links": [],
    }


def critical_path(ordered):
    """Set node["critical"] to the [start, end] offsets on the trace's critical path: from the
    end backwards, each span hands its time to the child that finished last before it.
    """
    kids_of = {}
    for node in ordered:
        node["critical"] = []
        if node["parent"] is not None:
            kids_of.setdefault(node["parent"], []).append(node)
    end = lambda n: n["offset_ns"] + n["duration_ns"]
    # One walk from the real root that ends last, so orphan groups get no second path.
    roots = [n for n in ordered if n["parent"] is None]
    roots = [n for n in roots if not n.get("synthetic")] or roots
    stack = [(max(roots, key=end), None)] if roots else []
    while stack:
        node, limit = stack.pop()
        start = node["offset_ns"]
        cursor = end(node) if limit is None else min(limit, end(node))
        for kid in sorted(kids_of.get(node["index"], []), key=end, reverse=True):
            if cursor <= start:
                break
            if kid["offset_ns"] >= cursor:
                continue
            kid_end = min(end(kid), cursor)
            if kid_end < cursor:
                node["critical"].append([kid_end, cursor])
            stack.append((kid, kid_end))
            cursor = max(kid["offset_ns"], start)
        if cursor > start:
            node["critical"].append([start, cursor])
        node["critical"].sort()


def fetch_trace(source, trace_id, around_ms=None, now_ms=None):
    roles = otel_roles(
        source, "traces", ("trace_id", "span_id", "parent_span_id", "duration")
    )
    precision = int(roles.get("duration_precision", 9))
    scale = 10 ** (9 - precision)
    window = lookup_window(around_ms, now_ms)
    rows, truncated = _select_trace(
        source,
        roles,
        trace_id,
        window,
        _span_select(roles),
        _q(roles["timestamp"]),
        SPAN_LIMIT,
    )
    if not rows:
        return {"trace_id": trace_id, "found": False, "window": list(window)}

    start_ns = min(r[5] for r in rows)
    spans = []
    for i, r in enumerate(rows):
        span_id, parent, name, kind, service, ts, duration, code, message = r[:9]
        attrs, resource, ev_ts, ev_names, ev_attrs = r[9:14]
        ln_trace, ln_span, ln_state, ln_attrs = r[14:18]
        spans.append(
            {
                "_key": ("span", i),
                "id": span_id,
                "parent_id": parent,
                "synthetic": False,
                "name": name,
                "kind": kind,
                "service": service,
                "offset_ns": ts - start_ns,
                "duration_ns": int(duration) * scale,
                "status_code": code,
                "status_message": message,
                "error": is_error_status(code),
                "attributes": _map(attrs),
                "resource": _map(resource),
                "events": [
                    {"offset_ns": t - start_ns, "name": n, "attributes": _map(a)}
                    for t, n, a in zip(ev_ts, ev_names, ev_attrs)
                ],
                "links": [
                    {
                        "trace_id": t,
                        "span_id": s,
                        "trace_state": st,
                        "attributes": _map(a),
                    }
                    for t, s, st, a in zip(ln_trace, ln_span, ln_state, ln_attrs)
                ],
            }
        )
    ordered = build_tree(spans)
    end_ns = max(s["offset_ns"] + s["duration_ns"] for s in spans)
    return {
        "trace_id": trace_id,
        "found": True,
        "start_ns": str(start_ns),
        "start_ms": start_ns // 1_000_000,
        "duration_ns": end_ns,
        "spans": ordered,
        "span_count": len(spans),
        "services": sorted({s["service"] for s in spans if s["service"]}),
        "error_count": sum(1 for s in spans if s["error"]),
        "truncated": truncated,
        "window": list(window),
    }


def fetch_trace_logs(source, trace_id, around_ms=None, now_ms=None):
    roles = otel_roles(source, "logs", ("trace_id",))
    ts = _q(roles["timestamp"])
    select = [
        _ns(ts),
        _col(roles, "severity_text"),
        _col(roles, "service"),
        f"toString({_col(roles, 'body')})",
        _col(roles, "span_id"),
    ]
    window = lookup_window(around_ms, now_ms)
    rows, truncated = _select_trace(
        source, roles, trace_id, window, select, ts, LOG_LIMIT
    )
    return {
        "source": source.slug,
        "trace_id_column": roles["trace_id"],
        "span_id_column": roles.get("span_id", ""),
        "logs": [
            {
                "ts_ns": str(t),
                "time_ms": t // 1_000_000,
                "severity": sev,
                "service": svc,
                "body": body,
                "span_id": span,
            }
            for t, sev, svc, body, span in rows
        ],
        "truncated": truncated,
        "window": list(window),
    }
