#!/usr/bin/env python3
"""Deterministic OpenTelemetry test data for Telescope.

Writes 24h of logs, traces and metrics for six services into ClickHouse, with the planted facts listed in
dev/otel/README.md, and records them in dev/otel/facts.json. Same --seed and --start give the same rows.
"""

import argparse
import bisect
import datetime as dt
import hashlib
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_DIR = HERE / "schema"
VARIANTS = {
    "compat": ["compat_logs", "compat_traces", "compat_metrics"],
    "exporter": ["exporter_logs", "exporter_traces", "exporter_metrics"],
    "k8s": ["k8s_logs", "compat_traces", "compat_metrics"],
}
TABLES = [
    "otel_logs",
    "otel_traces",
    "otel_metrics_gauge",
    "otel_metrics_sum",
    "otel_metrics_histogram",
    "otel_metrics_exponential_histogram",
    "otel_metrics_summary",
]

NS = 1_000_000_000
MS = 1_000_000
MIN = 60 * NS
HOUR = 60 * MIN
DAY = 24 * HOUR

N_TRACES = 40_000
SPIKE_AT, SPIKE_LEN, SPIKE_FACTOR = 12 * HOUR, 10 * MIN, 20
RESET_AT = 6 * HOUR
DEPLOY_AT = 16 * HOUR
BIG_TRACE_AT = 9 * HOUR + 17 * MIN
REFUSED_AT, REFUSED_ROWS = 20 * HOUR, 25
RESTART_EVERY = 30 * MIN
CHARGE_FAIL, CHARGE_FAIL_SPIKE = 0.02, 0.02 * SPIKE_FACTOR

SERVICES = ["frontend", "checkout", "payment", "cart", "ad", "postgres"]
VERSIONS = {
    "frontend": "2.3.1",
    "checkout": "1.4.0",
    "payment": "3.0.2",
    "cart": "1.9.0",
    "ad": "0.8.4",
}
VERSIONS["postgres"] = "16.4"
DEPLOY_VERSION = "1.5.0"
NAMESPACES = {
    "frontend": "shop",
    "checkout": "shop",
    "cart": "shop",
    "payment": "payments",
    "ad": "ads",
}
NAMESPACES["postgres"] = "data"
POD_COUNTS = {
    "frontend": 4,
    "checkout": 4,
    "cart": 4,
    "payment": 3,
    "ad": 3,
    "postgres": 2,
}
NODES = ["k8s-node-1", "k8s-node-2", "k8s-node-3"]
CLUSTER = "prod-eu-1"
LANG = {
    "frontend": "nodejs",
    "checkout": "go",
    "payment": "java",
    "cart": "dotnet",
    "ad": "python",
}
LANG["postgres"] = "cpp"

ROOT_MEDIAN_MS = 60  # lognormal median; with sigma 0.42 the p95 is ~120ms
CHECKOUT_MEDIAN_MS = 900  # p95 ~1.8s
SIGMA = 0.42
BOUNDS = [
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
]
SEVERITY = {"DEBUG": 5, "INFO": 9, "WARN": 13, "ERROR": 17}

# The only bodies cart ever logs: 7 Drain clusters, one token count each, variables always contain a digit.
CART_TEMPLATES = [
    ("cart service started pid={} port=8080", "cart service started <*> port=8080"),
    ("loaded cart for user user_{} items={}", "loaded cart for user <*> <*>"),
    ("added item SKU-{} qty={} to cart cart_{}", "added item <*> <*> to cart <*>"),
    (
        "cache miss for cart cart_{} fetching from database",
        "cache miss for cart <*> fetching from database",
    ),
    (
        "slow query detected on cart_items took {}ms rows={} threshold=200ms",
        "slow query detected on cart_items took <*> <*> threshold=200ms",
    ),
    ("cache evicted {} entries", "cache evicted <*> entries"),
    (
        "failed to reserve inventory for cart cart_{} retry {} of 3",
        "failed to reserve inventory for cart <*> retry <*> of 3",
    ),
]
REFUSED_BODY = (
    "failed to connect to database: dial tcp 10.0.3.7:5432: connect: connection refused"
)


def op(svc, name, kind, attrs=None, children=(), weight=1.0, logs=(), error=None):
    return {
        "svc": svc,
        "name": name,
        "kind": kind,
        "attrs": attrs or {},
        "children": list(children),
        "weight": weight,
        "logs": list(logs),
        "error": error,
    }


def stacktrace(exc_type, frames):
    lines = ["Traceback (most recent call last):"]
    for f, n, fn in frames:
        lines.append(f'  File "{f}", line {n}, in {fn}')
    lines.append(f"{exc_type}: see exception.message")
    return "\n".join(lines)


class Generator:
    def __init__(self, seed, start_ns):
        self.rng = random.Random(seed)
        self.seed = seed
        self.start = start_ns
        self.logs = {c: [] for c in LOG_COLUMNS}
        self.spans = {c: [] for c in SPAN_COLUMNS}
        self.server_calls = (
            []
        )  # (svc, method, route, start, dur) for the http.server metrics
        self.edges = set()
        self.payment_error_logs = []
        self.exception_log = None
        self.cart_template_rows = [0] * len(CART_TEMPLATES)
        self.big_trace = None
        self.root_durations = {}
        self._make_pods()

    # ------------------------------------------------------------------ ids and resources

    def hex_id(self, bits):
        return f"{self.rng.getrandbits(bits):0{bits // 4}x}"

    def _make_pods(self):
        alphabet = "bcdfghjklmnpqrstvwxz2456789"
        self.pods = {}
        i = 0
        for svc in SERVICES:
            rs = "".join(self.rng.choice(alphabet) for _ in range(9))
            pods = []
            for n in range(POD_COUNTS[svc]):
                if svc == "postgres":
                    name = f"postgres-{n}"
                else:
                    name = f"{svc}-{rs}-" + "".join(
                        self.rng.choice(alphabet) for _ in range(5)
                    )
                uid = self.hex_id(128)
                uid = f"{uid[:8]}-{uid[8:12]}-{uid[12:16]}-{uid[16:20]}-{uid[20:]}"
                pods.append(
                    {
                        "name": name,
                        "svc": svc,
                        "node": NODES[i % 3],
                        "uid": uid,
                        "ns": NAMESPACES[svc],
                    }
                )
                i += 1
            self.pods[svc] = pods
        self.restarting = self.pods["cart"][0]
        self._res_cache = {}

    def version(self, svc, t):
        if svc == "checkout" and t >= self.start + DEPLOY_AT:
            return DEPLOY_VERSION
        return VERSIONS[svc]

    def resource(self, pod, t):
        v = self.version(pod["svc"], t)
        key = (pod["name"], v)
        if key not in self._res_cache:
            svc = pod["svc"]
            res = {
                "service.name": svc,
                "service.version": v,
                "deployment.environment.name": "production",
                "telemetry.sdk.language": LANG[svc],
                "host.name": pod["name"],
                "k8s.cluster.name": CLUSTER,
                "k8s.namespace.name": pod["ns"],
                "k8s.node.name": pod["node"],
                "k8s.pod.name": pod["name"],
                "k8s.pod.uid": pod["uid"],
                "k8s.container.name": svc,
            }
            res[
                "k8s.statefulset.name" if svc == "postgres" else "k8s.deployment.name"
            ] = svc
            self._res_cache[key] = res
        return self._res_cache[key]

    # ------------------------------------------------------------------ logs

    def log(self, t, svc, pod, severity, body, attrs=None, trace_id="", span_id=""):
        t = t - t % MS  # SDKs stamp logs in ms, so some rows share a timestamp
        L = self.logs
        L["Timestamp"].append(t)
        L["TraceId"].append(trace_id)
        L["SpanId"].append(span_id)
        L["TraceFlags"].append(1 if trace_id else 0)
        L["SeverityText"].append(severity)
        L["SeverityNumber"].append(SEVERITY[severity])
        L["ServiceName"].append(svc)
        L["Body"].append(body)
        L["ResourceSchemaUrl"].append("https://opentelemetry.io/schemas/1.26.0")
        L["ResourceAttributes"].append(self.resource(pod, t))
        L["ScopeSchemaUrl"].append("")
        L["ScopeName"].append(f"{svc}.logger")
        L["ScopeVersion"].append("")
        L["ScopeAttributes"].append({})
        L["LogAttributes"].append(attrs or {})
        L["EventName"].append("")
        if svc == "payment" and severity == "ERROR":
            self.payment_error_logs.append(t)

    def cart_log(self, t, pod, idx, args, severity="INFO", trace_id="", span_id=""):
        self.cart_template_rows[idx] += 1
        body = CART_TEMPLATES[idx][0].format(*args)
        self.log(t, "cart", pod, severity, body, trace_id=trace_id, span_id=span_id)

    # ------------------------------------------------------------------ spans

    def place(self, node, trace_id, parent_id, start, dur):
        rng = self.rng
        sid = self.hex_id(64)
        svc = node["svc"]
        pod = rng.choice(self.pods[svc])
        children = node["children"]
        if children:
            if node["kind"] == "Client" and len(children) == 1:
                gap = dur * rng.uniform(0.02, 0.06)
                slots = [(start + gap, dur - 2 * gap)]
            else:
                self_frac = rng.uniform(0.08, 0.25)
                weights = [c["weight"] * rng.uniform(0.7, 1.3) for c in children]
                total, t, slots = sum(weights), start + dur * self_frac / 2, []
                for w in weights:
                    d = dur * (1 - self_frac) * w / total
                    slots.append((t, d))
                    t += d
            for c, (s, d) in zip(children, slots):
                if node["kind"] == "Client" and c["kind"] == "Server":
                    self.edges.add((svc, c["svc"]))
                self.place(c, trace_id, sid, int(s), max(int(d), 1000))
        events = {"Timestamp": [], "Name": [], "Attributes": []}
        status, message = "Unset", ""
        if node["error"]:
            status, message = "Error", node["error"]["message"]
            if node["error"].get("exception"):
                events["Timestamp"].append(start + dur - dur // 10)
                events["Name"].append("exception")
                events["Attributes"].append(node["error"]["exception"])
        S = self.spans
        S["Timestamp"].append(start)
        S["TraceId"].append(trace_id)
        S["SpanId"].append(sid)
        S["ParentSpanId"].append(parent_id)
        S["TraceState"].append("")
        S["SpanName"].append(node["name"])
        S["SpanKind"].append(node["kind"])
        S["ServiceName"].append(svc)
        S["ResourceAttributes"].append(self.resource(pod, start))
        S["ScopeName"].append(f"{svc}.instrumentation")
        S["ScopeVersion"].append("1.0.0")
        S["SpanAttributes"].append(node["attrs"])
        S["Duration"].append(dur)
        S["StatusCode"].append(status)
        S["StatusMessage"].append(message)
        S["Events.Timestamp"].append(events["Timestamp"])
        S["Events.Name"].append(events["Name"])
        S["Events.Attributes"].append(events["Attributes"])
        for c in (
            "Links.TraceId",
            "Links.SpanId",
            "Links.TraceState",
            "Links.Attributes",
        ):
            S[c].append([])
        if node["kind"] == "Server" and "http.route" in node["attrs"]:
            a = node["attrs"]
            self.server_calls.append(
                (svc, a["http.request.method"], a["http.route"], start, dur)
            )
        for entry in node["logs"]:
            severity, body, attrs = entry[:3]
            at = entry[3] if len(entry) > 3 else None
            t = (
                start + dur
                if at == "end"
                else start + int(dur * rng.uniform(0.05, 0.95))
            )
            body = body.replace("{ms}", str(max(dur // MS, 1)))
            if svc == "cart":
                self.cart_template_rows[attrs.pop("_tpl")] += 1
            self.log(t, svc, pod, severity, body, attrs, trace_id, sid)
            if (
                attrs.get("exception.type")
                and self.exception_log is None
                and start >= self.start + SPIKE_AT
            ):
                self.exception_log = {
                    "trace_id": trace_id,
                    "span_id": sid,
                    "timestamp_ns": t - t % MS,
                }
        return sid

    # ------------------------------------------------------------------ trace shapes

    def http(
        self,
        caller,
        callee,
        method,
        route,
        server_children=(),
        server_logs=(),
        weight=1.0,
        error=None,
    ):
        attrs_c = {
            "http.request.method": method,
            "url.full": f"http://{callee}:8080{route}",
            "server.address": callee,
        }
        attrs_s = {
            "http.request.method": method,
            "http.route": route,
            "url.path": route,
            "server.address": callee,
        }
        code = "502" if error and callee != "payment" else ("500" if error else "200")
        attrs_c["http.response.status_code"] = attrs_s["http.response.status_code"] = (
            code
        )
        server = op(
            callee,
            f"{method} {route}",
            "Server",
            attrs_s,
            server_children,
            logs=server_logs,
            error=error,
        )
        return op(
            caller,
            f"{method} {route}",
            "Client",
            attrs_c,
            [server],
            weight=weight,
            error=error,
        )

    def db(self, caller, statement, logs=(), weight=0.5):
        verb, table = statement.split()[0], statement.split()[-1]
        attrs = {
            "db.system": "postgresql",
            "db.name": "shop",
            "db.statement": statement,
            "server.address": "postgres",
        }
        attrs["db.operation.name"] = verb
        server = op("postgres", f"{verb} {table}", "Server", dict(attrs))
        return op(
            caller,
            f"{verb} shop.{table}",
            "Client",
            attrs,
            [server],
            weight=weight,
            logs=logs,
        )

    def cart_tpl(self, idx, *args, severity="INFO"):
        return (severity, CART_TEMPLATES[idx][0].format(*args), {"_tpl": idx})

    def cart_db(self, statement):
        rng = self.rng
        logs = []
        if rng.random() < 0.3:
            logs.append(self.cart_tpl(3, rng.randint(1, 99999), severity="DEBUG"))
        if rng.random() < 0.01:
            logs.append(
                self.cart_tpl(
                    4, rng.randint(200, 900), rng.randint(1, 60), severity="WARN"
                )
            )
        return self.db("cart", statement, logs)

    def frontend_root(self, method, route, children, error=None):
        rng = self.rng
        session = f"sess_{rng.randint(1, 20000)}"
        status = "502" if error else "200"
        http_attrs = {
            "http.method": method,
            "http.route": route,
            "http.status_code": status,
        }
        logs = [
            (
                "DEBUG",
                f"incoming request {method} {route} session={session}",
                dict(http_attrs),
            ),
            ("INFO", f"session {session} resolved for user_{rng.randint(1, 5000)}", {}),
            (
                "ERROR" if error else "INFO",
                f"{method} {route} {status} {{ms}}ms",
                dict(http_attrs),
                "end",
            ),
        ]
        attrs = {"http.request.method": method, "http.route": route, "url.path": route}
        attrs["http.response.status_code"] = status
        return op(
            "frontend",
            f"{method} {route}",
            "Server",
            attrs,
            children,
            logs=logs,
            error=error,
        )

    def cart_server_logs(self, kind):
        rng = self.rng
        if kind == "load":
            return [self.cart_tpl(1, rng.randint(1, 5000), rng.randint(0, 12))]
        if rng.random() < 0.02:
            return [
                self.cart_tpl(
                    6, rng.randint(1, 99999), rng.randint(1, 3), severity="WARN"
                )
            ]
        return [
            self.cart_tpl(
                2, rng.randint(10000, 99999), rng.randint(1, 5), rng.randint(1, 99999)
            )
        ]

    def ad_call(self):
        rng = self.rng
        ad_logs = [
            ("DEBUG", f"ad request context=page{rng.randint(1, 40)}", {}),
            ("INFO", f"served {rng.randint(1, 5)} ads", {}),
        ]
        rank = op(
            "ad",
            "rank ads",
            "Internal",
            logs=[("DEBUG", f"ranked {rng.randint(20, 200)} candidates", {})],
        )
        return self.http("frontend", "ad", "GET", "/ads", [rank], ad_logs, weight=0.6)

    def cart_get(self, caller, weight=1.0):
        return self.http(
            caller,
            "cart",
            "GET",
            "/cart",
            [self.cart_db("SELECT * FROM cart_items")],
            self.cart_server_logs("load"),
            weight,
        )

    def charge(self, t, failed=None):
        rng = self.rng
        order = f"ord_{rng.randint(100000, 999999)}"
        spike = self.start + SPIKE_AT <= t < self.start + SPIKE_AT + SPIKE_LEN
        if failed is None:
            failed = rng.random() < (CHARGE_FAIL_SPIKE if spike else CHARGE_FAIL)
        error, pay_logs = None, [
            (
                "INFO",
                f"charging card for order {order} amount={rng.randint(5, 900)}.00",
                {},
            )
        ]
        if failed:
            exc_type = "GatewayTimeoutError" if spike else "CardDeclinedError"
            message = (
                "payment gateway timeout after 5000ms"
                if spike
                else "card declined by issuer"
            )
            exc = {
                "exception.type": exc_type,
                "exception.message": message,
                "exception.stacktrace": stacktrace(
                    exc_type,
                    [
                        ("/app/payment/server.py", 88, "charge"),
                        ("/app/payment/gateway.py", 141, "authorize"),
                        ("/app/payment/gateway.py", 203, "_post"),
                    ],
                ),
            }
            error = {"message": message, "exception": exc}
            pay_logs.append(
                ("ERROR", f"charge failed for order {order}: {message}", dict(exc))
            )
        else:
            pay_logs.append(("INFO", f"charge succeeded for order {order}", {}))
        fraud = op(
            "payment",
            "fraud check",
            "Internal",
            logs=[("DEBUG", f"fraud score {rng.randint(1, 99)}", {})],
        )
        return (
            self.http(
                "checkout",
                "payment",
                "POST",
                "/charge",
                [fraud],
                pay_logs,
                weight=3.0,
                error=error,
            ),
            failed,
        )

    def build_trace(self, t):
        rng = self.rng
        r = rng.random()
        if r < 0.25:
            render = op(
                "frontend",
                "render page",
                "Internal",
                logs=[("DEBUG", "rendered home page", {})],
            )
            return "GET /", self.frontend_root(
                "GET", "/", [render, self.ad_call(), self.cart_get("frontend")]
            )
        if r < 0.50:
            load = op("cart", "load cart", "Internal")
            call = self.http(
                "frontend",
                "cart",
                "GET",
                "/cart",
                [load, self.cart_db("SELECT * FROM cart_items")],
                self.cart_server_logs("load"),
            )
            return "GET /api/cart", self.frontend_root("GET", "/api/cart", [call])
        if r < 0.65:
            children = [
                self.cart_db("SELECT * FROM cart_items"),
                self.cart_db("INSERT INTO cart_items"),
            ]
            call = self.http(
                "frontend",
                "cart",
                "POST",
                "/cart/items",
                children,
                self.cart_server_logs("add"),
            )
            return "POST /api/cart", self.frontend_root("POST", "/api/cart", [call])
        if r < 0.85:
            return "GET /api/ads", self.frontend_root(
                "GET", "/api/ads", [self.ad_call()]
            )
        charge, failed = self.charge(t)
        order = f"ord_{rng.randint(100000, 999999)}"
        error = charge["error"]
        children = [
            op(
                "checkout",
                "validate order",
                "Internal",
                logs=[("DEBUG", f"validated order {order}", {})],
            ),
            self.cart_get("checkout"),
            charge,
        ]
        if not failed:
            children.append(
                self.db(
                    "checkout",
                    "INSERT INTO orders",
                    [("INFO", f"order {order} persisted", {})],
                )
            )
        co_logs = [
            ("INFO", f"checkout started for order {order}", {}),
            (
                "ERROR" if failed else "INFO",
                f"checkout {'failed' if failed else 'completed'} for order {order}",
                {},
            ),
        ]
        call = self.http(
            "frontend",
            "checkout",
            "POST",
            "/checkout",
            children,
            co_logs,
            weight=1.0,
            error=error,
        )
        return "POST /api/checkout", self.frontend_root(
            "POST", "/api/checkout", [call], error=error
        )

    def build_big_trace(self):
        """57 spans over frontend, checkout, cart, payment and postgres; two failed charge attempts."""
        children = [
            op("checkout", "compute tax", "Internal"),
            op("checkout", "apply discount", "Internal"),
            self.cart_get("checkout"),
        ]
        for i in range(10):
            reserve = op(
                "checkout",
                f"reserve item {i + 1}",
                "Internal",
                [],
                [self.db("checkout", "UPDATE inventory")],
            )
            children.append(reserve)
        for attempt in range(3):
            charge, _ = self.charge(0, failed=attempt < 2)
            children.append(charge)
        children.append(self.db("checkout", "INSERT INTO orders"))
        clear = self.http(
            "checkout",
            "cart",
            "DELETE",
            "/cart",
            [self.cart_db("DELETE FROM cart_items")],
        )
        children += [clear, op("checkout", "send confirmation", "Internal")]
        call = self.http(
            "frontend", "checkout", "POST", "/checkout", children, [], weight=1.0
        )
        session = op("frontend", "validate session", "Internal")
        receipt = op("frontend", "render receipt", "Internal")
        root = self.frontend_root("POST", "/api/checkout", [session, call, receipt])
        return root

    def gen_traces(self):
        rng = self.rng
        times = sorted(
            self.start + int(rng.uniform(0, DAY - 30 * NS)) for _ in range(N_TRACES - 1)
        )
        big_at = self.start + BIG_TRACE_AT
        for t in times:
            endpoint, root = self.build_trace(t)
            median = (
                CHECKOUT_MEDIAN_MS
                if endpoint == "POST /api/checkout"
                else ROOT_MEDIAN_MS
            )
            dur = int(rng.lognormvariate(math.log(median), SIGMA) * MS)
            self.root_durations.setdefault(endpoint, []).append(dur)
            self.place(root, self.hex_id(128), "", t, dur)
        n0 = len(self.spans["TraceId"])
        trace_id = self.hex_id(128)
        dur = 2400 * MS
        self.place(self.build_big_trace(), trace_id, "", big_at, dur)
        span_rows = range(n0, len(self.spans["TraceId"]))
        self.big_trace = {
            "trace_id": trace_id,
            "spans": len(span_rows),
            "services": sorted({self.spans["ServiceName"][i] for i in span_rows}),
            "error_spans": sum(
                self.spans["StatusCode"][i] == "Error" for i in span_rows
            ),
            "start": iso(big_at),
            "end": iso(
                max(
                    self.spans["Timestamp"][i] + self.spans["Duration"][i]
                    for i in span_rows
                )
            ),
        }

    # ------------------------------------------------------------------ background logs

    def gen_background(self, total):
        rng = self.rng
        start = self.start
        fixed = 0
        pay = self.pods["payment"]
        for m in range(DAY // MIN):
            t0 = start + m * MIN
            spike = SPIKE_AT <= m * MIN < SPIKE_AT + SPIKE_LEN
            for _ in range(SPIKE_FACTOR if spike else 1):
                batch = rng.randint(100000, 999999)
                exc = {
                    "exception.type": "UpstreamTimeoutError",
                    "exception.message": "ledger upstream timeout after 30s",
                    "exception.stacktrace": stacktrace(
                        "UpstreamTimeoutError",
                        [
                            ("/app/payment/ledger.py", 57, "reconcile"),
                            ("/app/payment/ledger.py", 112, "fetch"),
                        ],
                    ),
                }
                body = f"ledger reconciliation failed for batch {batch}: upstream timeout after 30s"
                self.log(
                    t0 + int(rng.uniform(0, MIN)),
                    "payment",
                    rng.choice(pay),
                    "ERROR",
                    body,
                    exc,
                )
                fixed += 1
            body = f"ledger sync completed batch={rng.randint(100000, 999999)} records={rng.randint(10, 500)}"
            self.log(
                t0 + int(rng.uniform(0, MIN)), "payment", rng.choice(pay), "INFO", body
            )
            fixed += 1
            for pod in self.pods["cart"]:
                self.cart_log(
                    t0 + int(rng.uniform(0, MIN)), pod, 5, (rng.randint(1, 4000),)
                )
                fixed += 1
            if m % 5 == 0:
                for pod in self.pods["postgres"]:
                    body = f"checkpoint complete: wrote {rng.randint(50, 5000)} buffers"
                    self.log(
                        t0 + int(rng.uniform(0, MIN)), "postgres", pod, "INFO", body
                    )
                    fixed += 1
                for pod in self.pods["ad"]:
                    body = f"refreshed ad inventory count={rng.randint(800, 1200)}"
                    self.log(t0 + int(rng.uniform(0, MIN)), "ad", pod, "INFO", body)
                    fixed += 1
        for pod in self.pods["cart"]:
            self.cart_log(
                start + rng.randint(0, 2 * NS), pod, 0, (rng.randint(1000, 30000),)
            )
            fixed += 1
        for k in range(1, DAY // RESTART_EVERY):
            t = start + k * RESTART_EVERY + rng.randint(1 * NS, 5 * NS)
            self.cart_log(t, self.restarting, 0, (rng.randint(1000, 30000),))
            fixed += 1
        refused_from = start + REFUSED_AT
        for i in range(REFUSED_ROWS):
            t = refused_from + i * (120 * NS // REFUSED_ROWS) + rng.randint(0, NS)
            self.log(
                t,
                "checkout",
                rng.choice(self.pods["checkout"]),
                "ERROR",
                REFUSED_BODY,
                {"db.system": "postgresql"},
            )
            fixed += 1
        self.refused = {"from": iso(refused_from), "to": iso(refused_from + 121 * NS)}
        services = ["frontend", "checkout", "payment", "ad"]
        for _ in range(total - fixed):
            svc = rng.choice(services)
            attrs = {
                "http.method": "GET",
                "http.route": "/healthz",
                "http.status_code": "200",
            }
            body = f"GET /healthz 200 {rng.randint(1, 3)}ms"
            t = start + int(rng.uniform(0, DAY))
            self.log(t, svc, rng.choice(self.pods[svc]), "DEBUG", body, attrs)

    # ------------------------------------------------------------------ metrics

    def gen_metrics(self):
        rng = self.rng
        start = self.start
        minutes = DAY // MIN
        gauge = {c: [] for c in GAUGE_COLUMNS}
        sums = {c: [] for c in SUM_COLUMNS}
        hist = {c: [] for c in HIST_COLUMNS}

        def point(table, res, svc, name, desc, unit, attrs, start_ns, t_ns, **values):
            table["ResourceAttributes"].append(res)
            table["ResourceSchemaUrl"].append("")
            table["ScopeName"].append("otel-demo")
            table["ScopeVersion"].append("1.0.0")
            table["ScopeAttributes"].append({})
            table["ScopeDroppedAttrCount"].append(0)
            table["ScopeSchemaUrl"].append("")
            table["ServiceName"].append(svc)
            table["MetricName"].append(name)
            table["MetricDescription"].append(desc)
            table["MetricUnit"].append(unit)
            table["Attributes"].append(attrs)
            table["StartTimeUnix"].append(to_dt(start_ns))
            table["TimeUnix"].append(to_dt(t_ns))
            table["Flags"].append(0)
            for c in (
                "Exemplars.FilteredAttributes",
                "Exemplars.TimeUnix",
                "Exemplars.Value",
            ):
                table[c].append([])
            table["Exemplars.SpanId"].append([])
            table["Exemplars.TraceId"].append([])
            for k, v in values.items():
                table[k].append(v)

        # gauges, one point a minute
        k8s_res = {}
        for pods in self.pods.values():
            for pod in pods:
                r = {
                    "k8s.cluster.name": CLUSTER,
                    "k8s.namespace.name": pod["ns"],
                    "k8s.node.name": pod["node"],
                }
                r.update({"k8s.pod.name": pod["name"], "k8s.pod.uid": pod["uid"]})
                k8s_res[pod["name"]] = r
        restart_times = [
            start + k * RESTART_EVERY for k in range(1, DAY // RESTART_EVERY)
        ]
        for pods in self.pods.values():
            for pod in pods:
                svc, name = pod["svc"], pod["name"]
                base_cpu = rng.uniform(0.1, 0.5)
                base_mem = rng.uniform(200, 800) * 2**20
                for m in range(minutes):
                    t = start + (m + 1) * MIN
                    if pod is self.restarting:
                        cpu = 0.95 + rng.uniform(-0.01, 0.01)
                        since = (t - start) % RESTART_EVERY
                        mem = base_mem * (0.5 + since / RESTART_EVERY)
                    else:
                        cpu = min(base_cpu * rng.uniform(0.8, 1.2), 0.85)
                        mem = base_mem * rng.uniform(0.95, 1.05)
                    res = self.resource(pod, t - 1)
                    point(
                        gauge,
                        res,
                        svc,
                        "process.runtime.cpu.utilization",
                        "Process CPU",
                        "1",
                        {},
                        start,
                        t,
                        Value=cpu,
                    )
                    point(
                        gauge,
                        res,
                        svc,
                        "process.runtime.memory.usage",
                        "Process memory",
                        "By",
                        {},
                        start,
                        t,
                        Value=mem,
                    )
                    kr = k8s_res[name]
                    point(
                        gauge,
                        kr,
                        "",
                        "k8s.pod.cpu.utilization",
                        "Pod CPU",
                        "1",
                        {},
                        start,
                        t,
                        Value=cpu,
                    )
                    point(
                        gauge,
                        kr,
                        "",
                        "k8s.pod.memory.usage",
                        "Pod memory",
                        "By",
                        {},
                        start,
                        t,
                        Value=mem * 1.1,
                    )
                    restarts = (
                        bisect.bisect_right(restart_times, t)
                        if pod is self.restarting
                        else 0
                    )
                    cr = dict(kr, **{"k8s.container.name": svc})
                    point(
                        gauge,
                        cr,
                        "",
                        "k8s.container.restarts",
                        "Container restarts",
                        "{restart}",
                        {},
                        start,
                        t,
                        Value=restarts,
                    )
        for node in NODES:
            res = {"k8s.cluster.name": CLUSTER, "k8s.node.name": node}
            base = rng.uniform(0.3, 0.6)
            for m in range(minutes):
                t = start + (m + 1) * MIN
                cpu = base * rng.uniform(0.9, 1.1)
                point(
                    gauge,
                    res,
                    "",
                    "k8s.node.cpu.utilization",
                    "Node CPU",
                    "1",
                    {},
                    start,
                    t,
                    Value=cpu,
                )
                mem = rng.uniform(6, 7) * 2**30
                point(
                    gauge,
                    res,
                    "",
                    "k8s.node.memory.usage",
                    "Node memory",
                    "By",
                    {},
                    start,
                    t,
                    Value=mem,
                )

        # http.server.* from the server spans, cumulative, one point a minute per series
        series = {}
        for svc, method, route, t, dur in self.server_calls:
            v = self.version(svc, t)
            series.setdefault((svc, v, method, route), []).append((t, dur))
        for (svc, v, method, route), calls in sorted(series.items()):
            calls.sort()
            res = {
                "service.name": svc,
                "service.version": v,
                "deployment.environment.name": "production",
            }
            res["k8s.namespace.name"] = NAMESPACES[svc]
            attrs = {"http.request.method": method, "http.route": route}
            born = start + DEPLOY_AT if v == DEPLOY_VERSION else start
            dies = (
                start + DEPLOY_AT
                if (svc == "checkout" and v != DEPLOY_VERSION)
                else start + DAY
            )
            reset = start + RESET_AT if svc == "frontend" else None
            i, count, req_count, req_start = 0, 0, 0, born
            buckets, total, lo, hi = [0] * (len(BOUNDS) + 1), 0.0, math.inf, 0.0
            t = born + MIN
            while t <= dies:
                if reset is not None and t - MIN == reset:
                    req_count, req_start = 0, reset
                while i < len(calls) and calls[i][0] < t:
                    secs = calls[i][1] / NS
                    buckets[bisect.bisect_left(BOUNDS, secs)] += 1
                    total += secs
                    lo, hi = min(lo, secs), max(hi, secs)
                    count += 1
                    req_count += 1
                    i += 1
                desc = "Number of HTTP server requests"
                point(
                    sums,
                    res,
                    svc,
                    "http.server.requests",
                    desc,
                    "{request}",
                    attrs,
                    req_start,
                    t,
                    Value=float(req_count),
                )
                sums["AggregationTemporality"].append(2)
                sums["IsMonotonic"].append(True)
                point(
                    hist,
                    res,
                    svc,
                    "http.server.request.duration",
                    "Duration of HTTP server requests",
                    "s",
                    attrs,
                    born,
                    t,
                    Count=count,
                    Sum=total,
                    BucketCounts=list(buckets),
                    ExplicitBounds=list(BOUNDS),
                    Min=lo if count else 0.0,
                    Max=hi,
                )
                hist["AggregationTemporality"].append(2)
                t += MIN
        return gauge, sums, hist

    # ------------------------------------------------------------------ facts

    def facts(self, rows, digests):
        start = self.start
        spike_from, spike_to = start + SPIKE_AT, start + SPIKE_AT + SPIKE_LEN
        per5 = {}
        for t in self.payment_error_logs:
            per5[(t - start) // (5 * MIN)] = per5.get((t - start) // (5 * MIN), 0) + 1
        spike_windows = sorted(
            w for w in per5 if spike_from <= start + w * 5 * MIN < spike_to
        )
        others = [n for w, n in per5.items() if w not in spike_windows]
        checkout = self.root_durations["POST /api/checkout"]
        rest = [
            d
            for k, v in self.root_durations.items()
            if k != "POST /api/checkout"
            for d in v
        ]
        return {
            "seed": self.seed,
            "start": iso(start),
            "end": iso(start + DAY),
            "trace_id": self.big_trace["trace_id"],
            "services": SERVICES,
            "rows": rows,
            "traces": N_TRACES,
            "logs_with_trace_id": sum(1 for x in self.logs["TraceId"] if x),
            "content_sha256": digests,
            "call_graph": sorted(list(e) for e in self.edges),
            "error_spike": {
                "service": "payment",
                "query": "ServiceName='payment' and SeverityText='ERROR'",
                "from": iso(spike_from),
                "to": iso(spike_to),
                "factor": SPIKE_FACTOR,
                "charge_error_ratio": [CHARGE_FAIL, CHARGE_FAIL_SPIKE],
                "error_logs_per_5m_spike": [per5[w] for w in spike_windows],
                "error_logs_per_5m_max_outside": max(others),
            },
            "slow_endpoint": {
                "service": "frontend",
                "span_name": "POST /api/checkout",
                "p95_ms": round(p95(checkout) / MS, 1),
                "others_p95_ms": round(p95(rest) / MS, 1),
            },
            "deploy": {
                "service": "checkout",
                "from_version": "1.4.0",
                "to_version": DEPLOY_VERSION,
                "at": iso(start + DEPLOY_AT),
            },
            "restarting_pod": {
                "pod": self.restarting["name"],
                "service": "cart",
                "namespace": self.restarting["ns"],
                "node": self.restarting["node"],
                "every_minutes": RESTART_EVERY // MIN,
                "restarts": DAY // RESTART_EVERY - 1,
                "cpu_utilization": 0.95,
            },
            "cart_patterns": {
                "service": "cart",
                "count": len(CART_TEMPLATES),
                "templates": [
                    {"template": t[1], "rows": n}
                    for t, n in zip(CART_TEMPLATES, self.cart_template_rows)
                ],
            },
            "big_trace": self.big_trace,
            "counter_reset": {
                "metric": "http.server.requests",
                "service": "frontend",
                "at": iso(start + RESET_AT),
            },
            "connection_refused": {
                "service": "checkout",
                "text": "connection refused",
                "rows": REFUSED_ROWS,
                **self.refused,
            },
            "exception_log": {
                "service": "payment",
                "trace_id": self.exception_log["trace_id"],
                "span_id": self.exception_log["span_id"],
                "timestamp": iso(self.exception_log["timestamp_ns"]),
            },
            "k8s": {
                "cluster": CLUSTER,
                "nodes": NODES,
                "namespaces": sorted(set(NAMESPACES.values())),
                "pods": [p["name"] for pods in self.pods.values() for p in pods],
            },
        }


LOG_COLUMNS = (
    """Timestamp TraceId SpanId TraceFlags SeverityText SeverityNumber ServiceName Body
ResourceSchemaUrl ResourceAttributes ScopeSchemaUrl ScopeName ScopeVersion ScopeAttributes
LogAttributes EventName""".split()
)
SPAN_COLUMNS = (
    """Timestamp TraceId SpanId ParentSpanId TraceState SpanName SpanKind ServiceName
ResourceAttributes ScopeName ScopeVersion SpanAttributes Duration StatusCode StatusMessage
Events.Timestamp Events.Name Events.Attributes Links.TraceId Links.SpanId Links.TraceState
Links.Attributes""".split()
)
METRIC_COMMON = (
    """ResourceAttributes ResourceSchemaUrl ScopeName ScopeVersion ScopeAttributes
ScopeDroppedAttrCount ScopeSchemaUrl ServiceName MetricName MetricDescription MetricUnit Attributes
StartTimeUnix TimeUnix Flags Exemplars.FilteredAttributes Exemplars.TimeUnix Exemplars.Value
Exemplars.SpanId Exemplars.TraceId""".split()
)
GAUGE_COLUMNS = METRIC_COMMON + ["Value"]
SUM_COLUMNS = METRIC_COMMON + ["Value", "AggregationTemporality", "IsMonotonic"]
HIST_COLUMNS = (
    METRIC_COMMON
    + "Count Sum BucketCounts ExplicitBounds Min Max AggregationTemporality".split()
)


def iso(ns):
    return (
        dt.datetime.fromtimestamp(ns // NS, dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        + f".{ns % NS:09d}Z"
    )


def to_dt(ns):
    return dt.datetime.fromtimestamp(ns // NS, dt.timezone.utc)


def p95(values):
    values = sorted(values)
    return values[math.ceil(0.95 * len(values)) - 1]


def digest(columns):
    h = hashlib.sha256()
    for name, values in columns.items():
        h.update(name.encode())
        for v in values:
            h.update(repr(v).encode())
    return h.hexdigest()


def parse_start(value):
    t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    ns = int(t.timestamp()) * NS
    if ns % (5 * MIN):
        raise SystemExit(
            "--start must be aligned to 5 minutes, so the planted windows align with 5m buckets"
        )
    return ns


def schema_statements(variant, database):
    for name in VARIANTS[variant]:
        sql = (
            (SCHEMA_DIR / f"{name}.sql")
            .read_text()
            .replace("${DATABASE}", f"`{database}`")
        )
        sql = "\n".join(
            line for line in sql.splitlines() if not line.lstrip().startswith("--")
        )
        for stmt in sql.split(";"):
            if stmt.strip():
                yield stmt.strip()


def load(client, variant, database, tables):
    client.command(f"CREATE DATABASE IF NOT EXISTS `{database}`")
    for t in ["otel_traces_trace_id_ts_mv", "otel_traces_trace_id_ts"] + TABLES:
        client.command(f"DROP TABLE IF EXISTS `{database}`.`{t}` SYNC")
    for stmt in schema_statements(variant, database):
        client.command(stmt)
    for table, columns in tables.items():
        names = list(columns)
        n = len(columns[names[0]]) if names else 0
        for lo in range(0, n, 100_000):
            data = [columns[c][lo : lo + 100_000] for c in names]
            client.insert(
                f"`{database}`.`{table}`",
                data,
                column_names=names,
                column_oriented=True,
            )
        print(f"  {database}.{table}: {n} rows", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--start",
        default="2026-01-01T00:00:00Z",
        help="UTC start of the 24h window, 5m aligned",
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=18123, help="ClickHouse HTTP port")
    p.add_argument("--user", default="default")
    p.add_argument("--password", default="")
    p.add_argument(
        "--database",
        default="otel",
        help="database for the compat variant; others get a suffix",
    )
    p.add_argument(
        "--variants", default="compat", help="comma list of compat, exporter, k8s"
    )
    p.add_argument("--facts", default=str(HERE / "facts.json"))
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="generate and write facts, touch no database",
    )
    args = p.parse_args()
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    for v in variants:
        if v not in VARIANTS:
            raise SystemExit(f"unknown variant {v}")

    g = Generator(args.seed, parse_start(args.start))
    g.gen_traces()
    traced = len(g.logs["Timestamp"])
    g.gen_background(round(traced * 3 / 7))  # 70% of the logs carry a TraceId
    gauge, sums, hist = g.gen_metrics()
    tables = {
        "otel_logs": g.logs,
        "otel_traces": g.spans,
        "otel_metrics_gauge": gauge,
        "otel_metrics_sum": sums,
        "otel_metrics_histogram": hist,
    }
    rows = {
        t: len(tables[t][next(iter(tables[t]))]) if t in tables else 0 for t in TABLES
    }
    facts = g.facts(rows, {t: digest(c) for t, c in tables.items()})
    Path(args.facts).write_text(json.dumps(facts, indent=2) + "\n")
    print(json.dumps(rows), file=sys.stderr)

    if not args.dry_run:
        import clickhouse_connect

        client = clickhouse_connect.get_client(
            host=args.host, port=args.port, username=args.user, password=args.password
        )
        for v in variants:
            database = args.database if v == "compat" else f"{args.database}_{v}"
            print(f"loading {v} into {database}", file=sys.stderr)
            load(client, v, database, tables)


if __name__ == "__main__":
    main()
