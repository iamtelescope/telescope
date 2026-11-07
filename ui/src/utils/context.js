// Surrounding context for a row: time window, quick filters and presets (adapted from HyperDX ContextFilterPills).
// No imports, so the backend tests can load this file in node.

export const CONTEXT_RANGES = [
    { label: '100ms', value: 100 },
    { label: '500ms', value: 500 },
    { label: '1s', value: 1000 },
    { label: '5s', value: 5000 },
    { label: '30s', value: 30000 },
    { label: '1m', value: 60000 },
    { label: '5m', value: 300000 },
    { label: '15m', value: 900000 },
]
export const DEFAULT_CONTEXT_RANGE = 5000
export const CONTEXT_LIMIT = 500

const MAX_VALUE_LENGTH = 200
const SERVICE_COLUMNS = ['ServiceName', 'service_name', 'service']
const TRACE_COLUMNS = ['TraceId', 'trace_id', 'traceId']
const RESOURCE_COLUMNS = ['ResourceAttributes', 'resource_attributes']
const PROMOTED_KEYS = ['service.name', 'k8s.namespace.name', 'k8s.pod.name', 'k8s.container.name', 'host.name']

export function contextWindow(row, range) {
    const t = row.time.unixtime
    return { from: t - range, to: t + range }
}

export function escapeValue(value) {
    return String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'")
}

function literal(value) {
    return typeof value === 'number' || typeof value === 'boolean' ? String(value) : `'${escapeValue(value)}'`
}

function usable(value) {
    if (typeof value === 'number' || typeof value === 'boolean') return true
    return typeof value === 'string' && value !== '' && value.length <= MAX_VALUE_LENGTH
}

function quoteKey(key) {
    return /^[A-Za-z_][A-Za-z0-9_]*$/.test(key) ? key : `'${escapeValue(key)}'`
}

function otelRoles(source) {
    return source.otel?.roles || source.data?.otel?.roles || {}
}

function firstColumn(source, row, candidates) {
    return candidates.find((c) => c && c in (source.columns || {}) && usable(row.data?.[c]))
}

function columnFilter(name, value) {
    return { id: `col:${name}`, label: name, value, expr: `${quoteKey(name)} = ${literal(value)}` }
}

function attrFilter(column, key, value) {
    return { id: `attr:${key}`, label: key, value, expr: `${column}.'${escapeValue(key)}' = ${literal(value)}` }
}

// Quick filters from the row's own values: suggest columns, OTel service/trace and promoted resource attributes.
export function extractQuickFilters(source, row) {
    const columns = source.columns || {}
    const data = row.data || {}
    const roles = otelRoles(source)
    const filters = []
    const seen = new Set()
    const add = (f) => {
        if (f && !seen.has(f.id)) {
            seen.add(f.id)
            filters.push(f)
        }
    }

    const service = firstColumn(source, row, [roles.service, ...SERVICE_COLUMNS])
    if (service) add({ ...columnFilter(service, data[service]), role: 'service' })
    const trace = firstColumn(source, row, [roles.trace_id, ...TRACE_COLUMNS])
    if (trace) add({ ...columnFilter(trace, data[trace]), role: 'trace' })

    const resource = [roles.resource_attrs, ...RESOURCE_COLUMNS].find(
        (c) => c && c in columns && data[c] && typeof data[c] === 'object',
    )
    if (resource) {
        for (const key of PROMOTED_KEYS) {
            if (usable(data[resource][key])) add(attrFilter(resource, key, data[resource][key]))
        }
    }

    for (const [name, meta] of Object.entries(columns)) {
        if (!meta.suggest || name === source.timeColumn || name === source.dateColumn) continue
        if (usable(data[name])) add(columnFilter(name, data[name]))
    }
    return filters
}

// Each preset is the chips it selects, offered only when the row has its identifying chip.
function presetIds(filters, source) {
    const ids = new Set(filters.map((f) => f.id))
    const pick = (key, list) => (ids.has(key) ? list.filter((id) => ids.has(id)) : [])
    const byRole = (role) => filters.filter((f) => f.role === role).map((f) => f.id)
    const service = byRole('service')
    const otelPod = ['attr:k8s.namespace.name', 'attr:k8s.pod.name']
    const k8sPod = ['col:context', 'col:namespace', 'col:pod']
    return {
        service: service.length ? service : pick('attr:service.name', ['attr:service.name']),
        pod: source.kind === 'kubernetes' ? pick('col:pod', k8sPod) : pick('attr:k8s.pod.name', otelPod),
        container:
            source.kind === 'kubernetes'
                ? pick('col:container', [...k8sPod, 'col:container'])
                : source.kind === 'docker'
                  ? pick('col:container_name', ['col:container_name'])
                  : pick('attr:k8s.container.name', [...otelPod, 'attr:k8s.container.name']),
        trace: byRole('trace'),
    }
}

const PRESET_LABELS = { service: 'Same service', pod: 'Same pod', container: 'Same container', trace: 'Same trace' }

export function availablePresets(filters, source) {
    const presets = [{ label: 'All', value: 'all' }]
    for (const [name, ids] of Object.entries(presetIds(filters, source))) {
        if (ids.length) presets.push({ label: PRESET_LABELS[name], value: name })
    }
    presets.push({ label: 'Custom', value: 'custom' })
    return presets
}

export function presetFilterIds(preset, filters, source) {
    return presetIds(filters, source)[preset] || []
}

export function buildContextQuery(selectedIds, filters, custom) {
    const clauses = filters.filter((f) => selectedIds.includes(f.id)).map((f) => f.expr)
    if (custom && custom.trim()) clauses.push(custom.trim())
    if (clauses.length < 2) return clauses[0] || ''
    return clauses.map((c) => `(${c})`).join(' and ')
}

// The row itself in a context result: same time and same values (data holds every source column).
export function isSameRow(a, b) {
    return (
        a.time.unixtime === b.time.unixtime &&
        a.time.microseconds === b.time.microseconds &&
        JSON.stringify(a.data) === JSON.stringify(b.data)
    )
}
