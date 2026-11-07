// Row panel enrichment for OTel sources, adapted from HyperDX DBRowOverviewPanel, ExceptionSubpanel,
// HttpMessageSections and infraCorrelations. No imports, so the backend tests can load this file in node.

export const DEFAULT_HIGHLIGHTED = [
    'service.version',
    'deployment.environment.name',
    'k8s.namespace.name',
    'k8s.pod.name',
    'host.name',
]

const TOP_LEVEL_ROLES = [
    ['service', 'Service'],
    ['span_name', 'Span'],
    ['span_kind', 'Kind'],
    ['severity_text', 'Severity'],
    ['status_code', 'Status'],
    ['status_message', 'Status message'],
    ['duration', 'Duration'],
    ['trace_id', 'Trace ID'],
    ['span_id', 'Span ID'],
    ['parent_span_id', 'Parent span ID'],
    ['scope', 'Scope'],
]

export function otelOf(source) {
    return source?.kind === 'clickhouse' ? source.data?.otel || null : null
}

// The Overview tab and the copy actions are for OTel logs and traces only.
export function isEnriched(source) {
    return ['logs', 'traces'].includes(otelOf(source)?.signal)
}

function role(source, name) {
    return otelOf(source)?.roles?.[name] || null
}

function isSet(value) {
    return value !== null && value !== undefined && value !== ''
}

function mapColumn(source, row, name) {
    const column = role(source, name)
    const value = column ? row?.data?.[column] : null
    return value && typeof value === 'object' && !Array.isArray(value) ? { column, values: value } : null
}

// The event attributes and resource attributes maps, null when the row lacks one.
export function attributeMaps(source, row) {
    return { attrs: mapColumn(source, row, 'attrs'), resource: mapColumn(source, row, 'resource_attrs') }
}

export function topLevel(source, row) {
    const result = []
    for (const [name, label] of TOP_LEVEL_ROLES) {
        const column = role(source, name)
        const value = column ? row?.data?.[column] : undefined
        if (isSet(value) && typeof value !== 'object') result.push({ role: name, label, column, value })
    }
    return result
}

export function durationNs(source, value) {
    const precision = otelOf(source)?.roles?.duration_precision ?? 9
    return Number(value) * 10 ** (9 - precision)
}

// Each highlighted key is a column name or an attribute key, looked up in event then resource attributes.
export function highlighted(source, row) {
    const keys = otelOf(source)?.highlighted || DEFAULT_HIGHLIGHTED
    const { attrs, resource } = attributeMaps(source, row)
    const result = []
    for (const key of keys) {
        const direct = row?.data?.[key]
        if (isSet(direct) && typeof direct !== 'object') {
            result.push({ key, value: direct, path: [key] })
            continue
        }
        const map = [attrs, resource].find((m) => m && isSet(m.values[key]))
        if (map) result.push({ key, value: map.values[key], path: [map.column, key] })
    }
    return result
}

// Zipped span events from the Nested `events` role, stored as `<name>.Timestamp/Name/Attributes` columns.
export function spanEvents(source, row) {
    const column = role(source, 'events')
    const data = row?.data || {}
    const names = column ? data[`${column}.Name`] : null
    if (!Array.isArray(names)) return []
    const times = data[`${column}.Timestamp`] || []
    const attrs = data[`${column}.Attributes`] || []
    return names.map((name, i) => ({ time: times[i] ?? null, name, attributes: attrs[i] || {} }))
}

function exceptionFrom(values, origin) {
    const e = {
        type: values['exception.type'] || '',
        message: values['exception.message'] || '',
        stacktrace: values['exception.stacktrace'] || '',
        origin,
    }
    return e.type || e.message || e.stacktrace ? e : null
}

// Exceptions from span events named "exception", else from the row's own exception.* attributes.
export function exceptions(source, row) {
    const fromEvents = spanEvents(source, row)
        .filter((e) => e.name === 'exception')
        .map((e) => exceptionFrom(e.attributes, 'event'))
        .filter(Boolean)
    if (fromEvents.length) return fromEvents
    const attrs = attributeMaps(source, row).attrs
    const e = attrs && exceptionFrom(attrs.values, 'attributes')
    return e ? [e] : []
}

const pick = (values, keys) => keys.map((k) => values[k]).find(isSet)

function headers(values, prefix) {
    return Object.keys(values)
        .filter((k) => k.startsWith(prefix))
        .sort()
        .map((k) => ({ name: k.slice(prefix.length), value: values[k] }))
}

export function parseJson(value) {
    if (typeof value !== 'string' || !/^\s*[[{]/.test(value)) return null
    try {
        return JSON.parse(value)
    } catch {
        return null
    }
}

// HTTP request and response from semconv attributes (old and new names), null when the row is not HTTP.
export function httpMessage(source, row) {
    const attrs = attributeMaps(source, row).attrs
    if (!attrs) return null
    const v = attrs.values
    const message = {
        method: pick(v, ['http.request.method', 'http.method']),
        url: pick(v, ['url.full', 'http.url', 'url.path', 'http.target']),
        route: pick(v, ['http.route']),
        status: pick(v, ['http.response.status_code', 'http.status_code']),
        server: pick(v, ['server.address', 'net.host.name', 'http.host']),
        client: pick(v, ['client.address', 'net.peer.ip', 'http.client_ip']),
        userAgent: pick(v, ['user_agent.original', 'http.user_agent']),
        protocol: pick(v, ['network.protocol.version', 'http.flavor']),
        requestHeaders: headers(v, 'http.request.header.'),
        responseHeaders: headers(v, 'http.response.header.'),
        requestBody: pick(v, ['http.request.body']),
        responseBody: pick(v, ['http.response.body']),
    }
    return message.method || message.status || message.route || message.url ? message : null
}

// A JSON body as flattened {path, value} rows, null when the body is not JSON.
export function parsedBody(source, row) {
    const column = role(source, 'body')
    const parsed = parseJson(column ? row?.data?.[column] : null)
    if (parsed === null || typeof parsed !== 'object') return null
    const rows = []
    const walk = (value, path) => {
        if (value && typeof value === 'object' && Object.keys(value).length) {
            for (const [k, v] of Object.entries(value)) walk(v, [...path, k])
        } else {
            rows.push({ path, value: value && typeof value === 'object' ? JSON.stringify(value) : value })
        }
    }
    walk(parsed, [column])
    return rows
}

function escapeValue(value) {
    return String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'")
}

// The explorer query for "Copy link": the row's trace and span ids within a second of its time.
export function rowLinkQuery(source, row) {
    const clauses = ['trace_id', 'span_id']
        .map((name) => role(source, name))
        .filter((column) => column && isSet(row?.data?.[column]))
        .map((column) => `${column} = '${escapeValue(row.data[column])}'`)
    const t = row.time.unixtime
    return { from: t - 1000, to: t + 1000, query: clauses.join(' and ') }
}

// Infrastructure correlation groups: a resource attribute on the row and gauge metrics filtered by it.
export const INFRA_GROUPS = [
    {
        title: 'Pod',
        attribute: 'k8s.pod.name',
        charts: [
            { key: 'cpu', title: 'CPU usage', metric: 'k8s.pod.cpu.utilization', unit: 'percent', scale: 100 },
            { key: 'memory', title: 'Memory used', metric: 'k8s.pod.memory.usage', unit: 'bytes' },
            { key: 'restarts', title: 'Container restarts', metric: 'k8s.container.restarts', agg: 'max' },
        ],
    },
    {
        title: 'Node',
        attribute: 'k8s.node.name',
        charts: [
            { key: 'cpu', title: 'CPU usage', metric: 'k8s.node.cpu.utilization', unit: 'percent', scale: 100 },
            { key: 'memory', title: 'Memory used', metric: 'k8s.node.memory.usage', unit: 'bytes' },
        ],
    },
]

export const INFRA_RANGES = [
    { label: '30m', value: 15 * 60000 },
    { label: '1h', value: 30 * 60000 },
    { label: '1d', value: 12 * 3600000 },
]
export const DEFAULT_INFRA_RANGE = 30 * 60000

export function infraGroups(source, row) {
    const resource = attributeMaps(source, row).resource
    if (!resource) return []
    return INFRA_GROUPS.filter((g) => isSet(resource.values[g.attribute])).map((g) => ({
        ...g,
        value: String(resource.values[g.attribute]),
    }))
}

export function infraAvailable(source, row) {
    return isEnriched(source) && infraGroups(source, row).length > 0
}

export function infraWindow(row, half, now) {
    const t = row.time.unixtime
    return { from: t - half, to: Math.min(t + half, now) }
}

// A chartData request on the metrics source (its table is the gauge table) for one infra chart.
export function infraChartRequest(metricsSource, group, chart, window) {
    const roles = otelOf(metricsSource)?.roles || {}
    const resource = roles.resource_attrs || 'ResourceAttributes'
    const where = `${roles.metric_name || 'MetricName'} = '${escapeValue(chart.metric)}'`
    const value = { agg: chart.agg || 'avg', column: roles.value || 'Value', alias: 'value', where }
    const series = chart.scale
        ? [
              { ...value, hidden: true },
              { agg: 'formula', formula: `value * ${chart.scale}`, alias: chart.title },
          ]
        : [{ ...value, alias: chart.title }]
    return {
        from: window.from,
        to: window.to,
        query: `${resource}.'${escapeValue(group.attribute)}' = '${escapeValue(group.value)}'`,
        raw_query: '',
        context_columns: {},
        display: 'line',
        series,
        group_by: '',
        granularity: 'auto',
    }
}

// The shown (last) series' value in the bucket holding time t, null when that bucket is empty.
export function valueAt(data, t) {
    const ts = data?.timestamps || []
    let i = -1
    for (let k = 0; k < ts.length && ts[k] <= t; k++) i = k
    const series = data?.series?.[data.series.length - 1]
    return i >= 0 ? (series?.values[i] ?? null) : null
}

// A FlyQL field for a path, quoting segments with dots, as the FLATTENED tab does.
export function queryField(path) {
    return path.map((s) => (s.includes('.') ? `"${s.replace(/"/g, '\\"')}"` : s)).join('.')
}
