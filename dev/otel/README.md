# OTel test-data kit

Deterministic OpenTelemetry logs, traces and metrics for tests and demos: 24 hours, six services
(`frontend`, `checkout`, `payment`, `cart`, `ad`, `postgres`), written to ClickHouse in the tables the
OpenTelemetry ClickHouse exporter uses. The same `--seed` and `--start` always produce the same rows and the same
`facts.json`.

## Regenerate

```bash
# from the repo root, with the backend venv (needs clickhouse-connect)
python dev/otel/generate.py                                   # compat schema into database `otel`
python dev/otel/generate.py --variants compat,exporter,k8s    # also `otel_exporter` and `otel_k8s`
python dev/otel/generate.py --dry-run --facts /tmp/facts.json # generate and write facts only, no ClickHouse
```

Options: `--seed` (default 42), `--start` (UTC, 5-minute aligned, default `2026-01-01T00:00:00Z`), `--host`
(127.0.0.1), `--port` (HTTP, 18123), `--user`, `--password`, `--database` (otel), `--facts` (this directory's
`facts.json`). Each run drops and recreates the `otel_*` tables of the databases it loads, so a rerun is
idempotent. It never touches other tables. A run takes about 10 s to generate and 5 s per variant to load.

`facts.json` is committed for the defaults. With another `--seed` or `--start`, pass `--facts` somewhere else, or
expect a diff. To see the data under "last 24 hours" in the UI, pass a recent start, e.g.
`--start "$(date -u -v-24H +%Y-%m-%dT%H:00:00Z)"`.

## Schema variants (`schema/`)

| Variant | Files | Database | What differs |
|---|---|---|---|
| `compat` | `compat_logs.sql`, `compat_traces.sql`, `compat_metrics.sql` | `otel` | HyperDX's compat seed DDL without `__hdx_*` columns or TTL; metric times are `DateTime` |
| `exporter` | `exporter_*.sql` | `otel_exporter` | The exporter's own defaults: `TimestampTime` and a `ServiceName`-first key on logs, `Nested` `Events`/`Links`/`Exemplars`, `DateTime64(9)` metric times, `otel_traces_trace_id_ts` + MV |
| `k8s` | `k8s_logs.sql` + compat traces/metrics | `otel_k8s` | Logs with HyperDX's materialized `__hdx_materialized_k8s.*` columns |

`${DATABASE}` in the files is replaced by the target database. `Nested` columns are flattened to `Events.Timestamp`
etc. under the default `flatten_nested = 1`, as with the real exporter. The exporter DDL was written to match the
collector's default templates; it is not a copy of them. All variants hold the same rows.
The exponential histogram and summary tables are created empty.

## Data

- About 40k traces and 300k spans (`Server`, `Client`, `Internal`; `StatusCode` `Unset`/`Error`), `Duration` in ns.
  Call graph: frontend→cart, frontend→ad, frontend→checkout, checkout→cart, checkout→payment, checkout→postgres,
  cart→postgres. Postgres emits `Server` spans so the DB edges show up in a client→server join.
- About 385k logs, 70% carrying the `TraceId`/`SpanId` of a real span. Log timestamps are whole milliseconds, so some rows share
  a timestamp. Frontend request logs carry `LogAttributes` `http.method`, `http.route`, `http.status_code`.
- Every row has `ResourceAttributes` with `service.name`, `service.version`, `k8s.cluster.name`, `k8s.namespace.name`,
  `k8s.node.name`, `k8s.pod.name`, `k8s.pod.uid`, `k8s.container.name`, `host.name`. 3 nodes, 4 namespaces, 20 pods.
- Metrics, one point a minute: `http.server.request.duration` histogram and `http.server.requests` sum (both
  cumulative, per service, method and route, derived from the server spans); `process.runtime.cpu.utilization`,
  `process.runtime.memory.usage` per pod; `k8s.pod.cpu.utilization`, `k8s.pod.memory.usage`, `k8s.container.restarts`
  per pod; `k8s.node.cpu.utilization`, `k8s.node.memory.usage` per node.

## Planted facts (`facts.json`)

| Key | Fact |
|---|---|
| `error_spike` | `payment` errors ×20 for 10 minutes from start+12h: ERROR logs go from 1 to 20 a minute and the charge failure ratio from 2% to 40%. `ServiceName='payment' and SeverityText='ERROR'` is above 50 per 5m only in those two windows |
| `slow_endpoint` | frontend `POST /api/checkout` p95 ≈ 1.8 s; every other frontend endpoint p95 ≈ 120 ms |
| `deploy` | `checkout` `service.version` 1.4.0 → 1.5.0 at start+16h, with a new metric series from then |
| `restarting_pod` | one `cart` pod at CPU 0.95 restarts every 30 minutes (47 times); its `k8s.container.restarts` steps by 1 each time and it logs `cart service started` on each start |
| `cart_patterns` | every `cart` body comes from 7 templates, which Drain3 with default settings mines as exactly 7 clusters (row counts per template listed) |
| `trace_id`, `big_trace` | one trace of 57 spans over 5 services with 4 errored spans (two failed charge attempts) |
| `counter_reset` | `http.server.requests` for `frontend` restarts from 0 at start+6h (new `StartTimeUnix`) |
| `connection_refused` | exactly 25 `checkout` ERROR logs containing `connection refused`, within 2 minutes from start+20h |
| `exception_log` | a payment ERROR log with `exception.type`, `exception.message`, `exception.stacktrace`; its span has an `exception` event |
| `rows`, `content_sha256` | per-table row counts and a digest of the generated rows, for checking that a rerun is identical |

## Tests

`backend/tests/integration/conftest.py` provides `ch_client`, `otel_facts` and `otel_db`. Tests marked
`@pytest.mark.clickhouse` are skipped unless `TELESCOPE_TEST_CH_HOST` and `TELESCOPE_TEST_CH_PORT` (HTTP) are set.
`otel_db` (database from `TELESCOPE_TEST_OTEL_DB`, default `otel`) fails if the row counts differ from `facts.json`.

```bash
cd backend && TELESCOPE_TEST_CH_HOST=127.0.0.1 TELESCOPE_TEST_CH_PORT=18123 pytest -m clickhouse tests/integration
```
