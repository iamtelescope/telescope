// Display names of connection and source kinds.
export const KIND_LABELS = {
    clickhouse: 'ClickHouse',
    starrocks: 'StarRocks',
    docker: 'Docker',
    kubernetes: 'Kubernetes',
}

export const kindLabel = (kind) => KIND_LABELS[kind] || kind
