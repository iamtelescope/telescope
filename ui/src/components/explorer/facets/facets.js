import HTTP from '@/utils/http'
import { getPinnedFacets, setPinnedFacets } from '@/features/prefs/service'

const http = new HTTP()

export const VISIBLE_VALUES = 5
export const FETCH_LIMIT = 10

export const fetchFacets = (sourceSlug, params, signal) =>
    http.Post(`ui/v1/sources/${sourceSlug}/facets`, params, signal)

const baseType = (type) =>
    (type || '')
        .toLowerCase()
        .replace(/^nullable\((.*)\)$/, '$1')
        .replace(/^lowcardinality\((.*)\)$/, '$1')
        .replace(/^nullable\((.*)\)$/, '$1')

export const isMapType = (type) => baseType(type).startsWith('map(')
const isNumberType = (type) =>
    /^(u?int\d*|float\d*|decimal.*|double|bigint|smallint|tinyint|largeint)/.test(baseType(type))
const isBoolType = (type) => ['bool', 'boolean'].includes(baseType(type))

// Default facets: low-cardinality looking columns (LowCardinality, Enum, Bool, small ints) and Map keys.
export function defaultFacetColumns(source) {
    const result = []
    for (const [name, column] of Object.entries(source.columns || {})) {
        if (name === source.timeColumn || name === source.dateColumn) continue
        const type = (column.type || '').toLowerCase()
        const base = baseType(type)
        if (
            name === source.severityColumn ||
            type.includes('lowcardinality(') ||
            base.startsWith('enum') ||
            isBoolType(type) ||
            /^u?int(8|16)$/.test(base) ||
            isMapType(type)
        ) {
            result.push(name)
        }
    }
    return result
}

// A map key with dots becomes a double-quoted FlyQL segment, like the row drawer does.
export function facetPath(column, key) {
    if (key === undefined || key === null) return column
    const segment = key.includes('.') ? `"${key.replace(/"/g, '\\"')}"` : key
    return `${column}.${segment}`
}

export function typedValue(source, column, key, value) {
    if (value === null) return null
    const type = key === undefined || key === null ? source.columns[column]?.type : ''
    if (isNumberType(type) && value !== '' && !isNaN(Number(value))) return Number(value)
    if (isBoolType(type) && (value === 'true' || value === 'false')) return value === 'true'
    return value
}

export function formatValue(value) {
    if (value === null) return '(null)'
    if (value === '') return '(empty)'
    return String(value)
}

const storageKey = (user, source) => `telescope.facets.pinned.${user || 'anonymous'}.${source.slug}`

function loadLocalPinned(user, source) {
    try {
        const value = JSON.parse(localStorage.getItem(storageKey(user, source)) || '[]')
        return Array.isArray(value) ? value : []
    } catch {
        return []
    }
}

function dropLocalPinned(user, source) {
    try {
        localStorage.removeItem(storageKey(user, source))
    } catch {
        // Storage can be unavailable (private mode).
    }
}

// Pins are stored server-side; pins this browser kept in localStorage are uploaded once, then dropped.
export async function loadPinned(user, source) {
    const response = await getPinnedFacets(source.slug)
    const local = loadLocalPinned(user, source)
    if (!response.result) return local
    let facets = response.data.facets
    if (facets === null && local.length && (await setPinnedFacets(source.slug, local)).result) facets = local
    if (facets !== null) dropLocalPinned(user, source)
    return facets || local
}

export const savePinned = (source, pinned) => setPinnedFacets(source.slug, pinned)

export function loadCollapsed() {
    try {
        return localStorage.getItem('telescope.facets.collapsed') === '1'
    } catch {
        return false
    }
}

export function saveCollapsed(value) {
    try {
        localStorage.setItem('telescope.facets.collapsed', value ? '1' : '0')
    } catch {
        // Storage can be unavailable (private mode); the panel state then lasts for the page only.
    }
}

// Facet ids: `col` for a column (or a Map column's keys) and `col.key` for a Map key's values.
// A dotted column name (e.g. Nested `Links.TraceId`) is a column, not a Map key.
export function splitFacetId(id, columns = {}) {
    if (id in columns) return { column: id, key: null }
    const dot = id.indexOf('.')
    return dot < 0 ? { column: id, key: null } : { column: id.slice(0, dot), key: id.slice(dot + 1) }
}

export function buildRequest(store, columns, mapKeys) {
    const { group_by, ...params } = store.graphRequestParams
    return { ...params, columns, map_keys: mapKeys, limit: FETCH_LIMIT }
}
