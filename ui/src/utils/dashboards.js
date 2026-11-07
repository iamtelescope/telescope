import { Parameter, parse as parseFlyql } from 'flyql'

import { localTimeZone } from '@/utils/datetimeranges'

export const TIMESERIES_DISPLAYS = ['line', 'stacked_area', 'stacked_bar']

export const DISPLAYS = [
    { value: 'line', label: 'Line' },
    { value: 'stacked_area', label: 'Area' },
    { value: 'stacked_bar', label: 'Bars' },
    { value: 'number', label: 'Number' },
    { value: 'table', label: 'Table' },
    { value: 'bar', label: 'Top N' },
    { value: 'pie', label: 'Pie' },
    { value: 'search', label: 'Logs' },
    { value: 'patterns', label: 'Patterns' },
    { value: 'text', label: 'Text' },
]
// Tiles that list log rows or event patterns instead of aggregating series.
export const LOG_TILE_DISPLAYS = ['search', 'patterns']
export const isLogTile = (display) => LOG_TILE_DISPLAYS.includes(display)
export const SEARCH_TILE_MAX_LIMIT = 500

// Query aggregations; tile series may also be a 'formula' over them.
export const AGGS = ['count', 'sum', 'avg', 'min', 'max', 'quantile', 'uniq', 'last_value', 'any']
export const MAX_GROUP_BY = 3
// Displays that show one series; extra series must be hidden formula operands.
export const SINGLE_SERIES_DISPLAYS = ['number', 'bar', 'pie']
export const COLOR_RULE_OPS = [
    { value: 'gt', label: '>' },
    { value: 'gte', label: '≥' },
    { value: 'lt', label: '<' },
    { value: 'lte', label: '≤' },
    { value: 'eq', label: '=' },
]
export const QUANTILE_LEVELS = [0.5, 0.75, 0.9, 0.95, 0.99]
export const GRANULARITIES = ['auto', '15s', '30s', '1m', '5m', '10m', '15m', '30m', '1h', '2h', '6h', '12h', '1d']
export const REFRESH_OPTIONS = ['off', '30s', '1m', '5m']
export const REFRESH_MS = { '30s': 30000, '1m': 60000, '5m': 300000 }
export const NUMBER_UNITS = [
    'number',
    'bytes',
    'bytes_si',
    'duration_ns',
    'duration_us',
    'duration_ms',
    'duration_s',
    'percent',
]
export const MAX_SERIES = 5

export const isTimeseries = (display) => TIMESERIES_DISPLAYS.includes(display)
export const maxLimit = (display) => (isTimeseries(display) ? 50 : 100)

// The series a single-value display shows: the first one not hidden.
export const visibleIndex = (series) =>
    Math.max(
        0,
        (series || []).findIndex((s) => !s.hidden),
    )

// The color of the first matching rule, or null.
export const ruleColor = (rules, value) => {
    if (value === null || value === undefined) return null
    const test = { gt: (a, b) => a > b, gte: (a, b) => a >= b, lt: (a, b) => a < b, lte: (a, b) => a <= b }
    const rule = (rules || []).find((r) => (test[r.op] ? test[r.op](value, r.value) : value === r.value))
    return rule ? rule.color : null
}

// Spec section 5 numeric type check, after unwrapping Nullable and LowCardinality.
export const isNumericType = (type) => {
    let t = String(type || '')
    let prev = null
    while (prev !== t) {
        prev = t
        t = t.replace(/^\s*(Nullable|LowCardinality)\((.*)\)\s*$/i, '$2')
    }
    return (
        /^(U?Int\d+|Float\d+|Decimal.*)$/.test(t) ||
        /^(tinyint|smallint|int|bigint|largeint|float|double|decimal.*)$/i.test(t)
    )
}

export const countOnlyKind = (kind) => kind === 'docker' || kind === 'kubernetes'

export const emptyDashboardData = () => ({
    time: { from: 'now-1h', to: 'now', time_zone: localTimeZone },
    query: '',
    refresh: 'off',
    version: DASHBOARD_DATA_VERSION,
    variables: [],
    sections: [],
    tiles: [],
})

export const newTileId = (tiles) => {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    const used = new Set((tiles || []).map((t) => t.id))
    let id
    do {
        id = Array.from({ length: 6 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
    } while (used.has(id))
    return id
}

export const defaultTileSize = (display) => {
    if (isLogTile(display)) return { w: 24, h: 10 }
    return display === 'number' || display === 'text' ? { w: 6, h: 4 } : { w: 12, h: 8 }
}

export const GRID_COLUMNS = 24

export const bottomY = (tiles) => Math.max(0, ...(tiles || []).map((t) => t.y + t.h))

// Bottom of the grid, right after the last row's tiles when it fits; vertical compaction then lifts it up.
export const newTilePosition = (tiles, w) => {
    if (!tiles?.length) return { x: 0, y: 0 }
    const lastY = Math.max(...tiles.map((t) => t.y))
    const x = Math.max(...tiles.filter((t) => t.y === lastY).map((t) => t.x + t.w))
    return { x: x + w <= GRID_COLUMNS ? x : 0, y: bottomY(tiles) }
}

export const formatValue = (value, format) => {
    if (value === null || value === undefined) return '–'
    const unit = format?.unit || 'number'
    const decimals = format?.decimals ?? (unit === 'number' ? undefined : 2)
    const num = (v) =>
        v.toLocaleString(
            undefined,
            decimals === undefined ? {} : { minimumFractionDigits: decimals, maximumFractionDigits: decimals },
        )
    const scaled = (v, base, units) => {
        let i = 0
        while (Math.abs(v) >= base && i < units.length - 1) {
            v /= base
            i++
        }
        return `${num(v)} ${units[i]}`
    }
    if (unit === 'bytes') return scaled(value, 1024, ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'])
    if (unit === 'percent') return `${num(value)}%`
    if (unit === 'duration_ms') {
        const abs = Math.abs(value)
        if (abs < 1000) return `${num(value)} ms`
        if (abs < 60000) return `${num(value / 1000)} s`
        if (abs < 3600000) return `${num(value / 60000)} min`
        return `${num(value / 3600000)} h`
    }
    return num(value)
}

export const DASHBOARD_DATA_VERSION = 3
export const VARIABLE_TYPES = [
    { value: 'values', label: 'Column values' },
    { value: 'static', label: 'Static list' },
    { value: 'text', label: 'Text' },
]
export const VARIABLE_NAME_RE = /^[A-Za-z_][A-Za-z0-9_]{0,63}$/
export const VARIABLE_URL_PREFIX = 'var-'

// v1 dashboards had no variables, v2 no sections; the server upgrades them the same way.
export const upgradeDashboardData = (data) => {
    if (!data) return data
    if ((data.version ?? 1) === 1) data = { ...data, version: 2, variables: data.variables || [] }
    if (data.version === 2) data = { ...data, version: DASHBOARD_DATA_VERSION, sections: data.sections || [] }
    return data
}

const asList = (value) => (Array.isArray(value) ? value : value === undefined || value === null ? [] : [value])

export const isEmptyValue = (value) => asList(value).filter((v) => v !== '').length === 0

// Current value of each variable: the URL `var-<name>` wins over the saved default.
export const variableValues = (variables, routeQuery) => {
    const values = {}
    for (const v of variables || []) {
        const key = VARIABLE_URL_PREFIX + v.name
        const raw = key in (routeQuery || {}) ? asList(routeQuery[key]) : asList(v.default)
        const list = raw.filter((x) => x !== '' && x !== null)
        values[v.name] = v.multi ? list : (list[0] ?? '')
    }
    return values
}

export const variableRouteQuery = (variable, value) => {
    const list = asList(value).filter((x) => x !== '')
    return { [VARIABLE_URL_PREFIX + variable.name]: list.length ? (variable.multi ? list : list[0]) : '' }
}

// chartData `params`: a required variable left empty is omitted, so the server reports it.
export const variableParams = (variables, values) => {
    const params = {}
    for (const v of variables || []) {
        const value = values[v.name]
        if (isEmptyValue(value)) {
            if (!v.required) params[v.name] = v.multi ? [] : ''
        } else {
            params[v.name] = value
        }
    }
    return params
}

export const missingRequired = (variables, values) =>
    (variables || []).filter((v) => v.required && isEmptyValue(values[v.name])).map((v) => v.name)

const flyqlLiteral = (value) => {
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    return `'${String(value).replace(/'/g, "\\'")}'`
}

const paramValues = (param, params) => {
    if (param.positional || !(param.name in params)) return null
    return asList(params[param.name]).filter((v) => v !== null && v !== '')
}

// The JS parser's IN-list ranges exclude a string's quotes; widen them back.
const quotedRange = (text, range) => {
    const quote = text[range.start - 1]
    const quoted = (quote === "'" || quote === '"') && text[range.end] === quote
    return quoted ? [range.start - 1, range.end + 1] : [range.start, range.end]
}

// Mirrors backend bind_query; returns null when a value is missing, so callers keep the raw query.
const bindExpression = (text, expr, params) => {
    const start = expr.key.range.start
    const edits = []
    if (expr.value instanceof Parameter) {
        const values = paramValues(expr.value, params)
        if (values === null) throw new Error('unbound')
        if (!values.length) return undefined
        const literals = values.map(flyqlLiteral)
        if (literals.length === 1) {
            edits.push([expr.valueRange.start, expr.valueRange.end, literals[0]])
        } else if (expr.operator === '=' || expr.operator === '!=') {
            const op = expr.operator === '=' ? 'in' : 'not in'
            edits.push([expr.operatorRange.start, expr.valueRange.end, `${op} [${literals.join(', ')}]`])
        } else {
            throw new Error('multi')
        }
    } else if (expr.values && expr.values.some((v) => v instanceof Parameter)) {
        const items = []
        expr.values.forEach((value, i) => {
            if (value instanceof Parameter) {
                const values = paramValues(value, params)
                if (values === null) throw new Error('unbound')
                items.push(...values.map(flyqlLiteral))
            } else {
                items.push(text.slice(...quotedRange(text, expr.valueRanges[i])))
            }
        })
        if (!items.length) return undefined
        const first = quotedRange(text, expr.valueRanges[0])
        const last = quotedRange(text, expr.valueRanges[expr.valueRanges.length - 1])
        edits.push([first[0], last[1], items.join(', ')])
    }
    let result = text.slice(start, expr.range.end)
    for (const [s, e, replacement] of edits.sort((a, b) => b[0] - a[0])) {
        result = result.slice(0, s - start) + replacement + result.slice(e - start)
    }
    return result
}

const bindNode = (text, node, params) => {
    let body
    if (node.expression) {
        body = bindExpression(text, node.expression, params)
    } else {
        const parts = [node.left, node.right]
            .filter(Boolean)
            .map((child) => bindNode(text, child, params))
            .filter((part) => part !== undefined)
        if (!parts.length) return undefined
        body = parts.length === 1 ? parts[0] : `(${parts[0]} ${node.boolOperator} ${parts[1]})`
    }
    if (body === undefined) return undefined
    return node.negated ? `not ${body}` : body
}

// FlyQL text with `$name` values substituted, for the explorer drill-down.
export const bindFlyql = (query, params) => {
    if (!query || !query.includes('$')) return query
    try {
        const root = parseFlyql(query).root
        return bindNode(query, root, params || {}) ?? ''
    } catch {
        return query
    }
}

// Tile chart and range with variables substituted, for the explorer, which has no variables.
export const boundForExplorer = (chart, range) => ({
    chart: { ...chart, query: bindFlyql(chart.query || '', range.params) },
    range: { ...range, query: bindFlyql(range.query || '', range.params) },
})
