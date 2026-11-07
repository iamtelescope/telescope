import HTTP from '@/utils/http'

const http = new HTTP()

export const PATTERN_KINDS = ['clickhouse', 'docker', 'kubernetes']

export const fetchPatterns = (sourceSlug, params, signal) =>
    http.Post(`ui/v1/sources/${sourceSlug}/patterns`, params, signal)

export function buildRequest(store, column, sample) {
    const { group_by, ...params } = store.graphRequestParams
    return { ...params, column: column || '', sample }
}

// Columns a pattern can be mined from: everything but the time and date columns.
export function patternColumns(source) {
    return Object.keys(source.columns || {}).filter((name) => name !== source.timeColumn && name !== source.dateColumn)
}

// The current query AND the pattern's LIKE filter.
export function withPatternFilter(query, filter) {
    const current = (query || '').trim()
    return current ? `(${current}) and ${filter}` : filter
}

// Template split into literal text and <*> parameters, for highlighting.
export function templateParts(template) {
    return template.split(/(<\*>)/).filter((part) => part !== '')
}

export function formatShare(share) {
    const pct = share * 100
    if (pct > 0 && pct < 0.1) return '<0.1%'
    return `${pct.toFixed(pct < 10 ? 1 : 0)}%`
}
