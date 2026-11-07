-- otel_logs with materialized k8s.* columns as HyperDX creates them, adapted from HyperDX
-- docker/otel-collector/schema/seed/00002_otel_logs_compat.sql without session/env columns or TTL.
CREATE TABLE IF NOT EXISTS ${DATABASE}.otel_logs
(
  `Timestamp` DateTime64(9) CODEC(Delta, ZSTD(3)),
  `TraceId` String CODEC(ZSTD(3)),
  `SpanId` String CODEC(ZSTD(3)),
  `TraceFlags` UInt8,
  `SeverityText` LowCardinality(String) CODEC(ZSTD(3)),
  `SeverityNumber` UInt8,
  `ServiceName` LowCardinality(String) CODEC(ZSTD(3)),
  `Body` String CODEC(ZSTD(3)),
  `ResourceSchemaUrl` LowCardinality(String) CODEC(ZSTD(3)),
  `ResourceAttributes` Map(LowCardinality(String), String) CODEC(ZSTD(3)),
  `ScopeSchemaUrl` LowCardinality(String) CODEC(ZSTD(3)),
  `ScopeName` String CODEC(ZSTD(3)),
  `ScopeVersion` LowCardinality(String) CODEC(ZSTD(3)),
  `ScopeAttributes` Map(LowCardinality(String), String) CODEC(ZSTD(3)),
  `LogAttributes` Map(LowCardinality(String), String) CODEC(ZSTD(3)),
  `EventName` String CODEC(ZSTD(3)),
  `__hdx_materialized_k8s.cluster.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.cluster.name'] CODEC(ZSTD(3)),
  `__hdx_materialized_k8s.container.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.container.name'] CODEC(ZSTD(3)),
  `__hdx_materialized_k8s.deployment.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.deployment.name'] CODEC(ZSTD(3)),
  `__hdx_materialized_k8s.namespace.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.namespace.name'] CODEC(ZSTD(3)),
  `__hdx_materialized_k8s.node.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.node.name'] CODEC(ZSTD(3)),
  `__hdx_materialized_k8s.pod.name` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.pod.name'] CODEC(ZSTD(3)),
  `__hdx_materialized_k8s.pod.uid` LowCardinality(String) MATERIALIZED ResourceAttributes['k8s.pod.uid'] CODEC(ZSTD(3)),
  INDEX idx_trace_id TraceId TYPE bloom_filter(0.001) GRANULARITY 1,
  INDEX idx_res_attr_key mapKeys(ResourceAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
  INDEX idx_res_attr_value mapValues(ResourceAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
  INDEX idx_scope_attr_key mapKeys(ScopeAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
  INDEX idx_scope_attr_value mapValues(ScopeAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
  INDEX idx_log_attr_key mapKeys(LogAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
  INDEX idx_log_attr_value mapValues(LogAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
  INDEX idx_lower_body lower(Body) TYPE tokenbf_v1(32768, 3, 0) GRANULARITY 8
)
ENGINE = MergeTree
PARTITION BY toDate(Timestamp)
ORDER BY (toStartOfFiveMinutes(Timestamp), ServiceName, Timestamp)
SETTINGS index_granularity = 8192;
