import HTTP from '@/utils/http'
import { isNumericType } from '@/utils/dashboards.js'
import { isMapType } from '@/components/explorer/facets/facets.js'

const http = new HTTP()

export const fetchHeatmap = (sourceSlug, params, signal) =>
    http.Post(`ui/v1/sources/${sourceSlug}/heatmap`, params, signal)

export const fetchDeltas = (sourceSlug, params, signal) =>
    http.Post(`ui/v1/sources/${sourceSlug}/deltas`, params, signal)

// Deltas need a ClickHouse source with a numeric column to draw on the y axis.
export function numericColumns(source) {
    return Object.entries(source?.columns || {})
        .filter(([name, col]) => name !== source.timeColumn && isNumericType(col.type))
        .map(([name]) => name)
}

export const deltasAvailable = (source) => source?.kind === 'clickhouse' && numericColumns(source).length > 0

// The OTel duration column, else a duration-like one, else the first numeric column.
export function defaultColumn(source) {
    const columns = numericColumns(source)
    const duration = source?.otelRole?.('duration')
    if (columns.includes(duration)) return duration
    return columns.find((c) => /duration|latency|elapsed/i.test(c)) || columns[0] || null
}

export function buildRequest(store, column) {
    const { group_by, ...params } = store.graphRequestParams
    return { ...params, column }
}

// Column and map key of a flattened property, or null when it cannot be filtered (array elements).
export function propertyPath(source, key) {
    if (key.includes('[')) return null
    const columns = source?.columns || {}
    if (columns[key] && !isMapType(columns[key].type)) return { column: key, key: null }
    const column = Object.keys(columns)
        .filter((c) => isMapType(columns[c].type) && key.startsWith(`${c}.`))
        .sort((a, b) => b.length - a.length)[0]
    return column ? { column, key: key.slice(column.length + 1) } : null
}

export function formatPercent(value) {
    if (value > 0 && value < 0.1) return '<0.1%'
    return `${value.toFixed(value < 10 ? 1 : 0)}%`
}
