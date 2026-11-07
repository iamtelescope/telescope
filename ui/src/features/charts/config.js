import { AGGS } from '@/utils/dashboards.js'

// The chart explorer keeps its whole tile ({title, description, chart}) in one JSON `config` URL param, like HyperDX.
export const parseConfig = (text) => {
    try {
        const value = JSON.parse(text || '')
        if (!value || typeof value !== 'object' || !value.chart || typeof value.chart !== 'object') return null
        return { title: String(value.title || ''), description: String(value.description || ''), chart: value.chart }
    } catch {
        return null
    }
}

export const serializeConfig = ({ title, description, chart }) =>
    JSON.stringify({ title: title || '', ...(description ? { description } : {}), chart })

// Search alerts watch one plain series; metric and formula series have no alert equivalent.
export const alertSeries = (chart) =>
    chart?.display === 'text' ? null : (chart?.series || []).find((s) => !s.hidden && AGGS.includes(s.agg))

// Query params AlertEditor prefills a new search alert from; the series filter joins the chart query.
export const alertQuery = ({ title, chart }) => {
    const s = alertSeries(chart)
    const filters = [chart.query, s.where].filter(Boolean)
    const query = { source: chart.source, agg: s.agg }
    if (title) query.title = title
    if (filters.length) query.query = filters.length > 1 ? filters.map((f) => `(${f})`).join(' and ') : filters[0]
    if (chart.raw_query) query.raw_query = chart.raw_query
    if (Object.keys(chart.context_columns || {}).length) query.context_columns = JSON.stringify(chart.context_columns)
    if (chart.group_by) query.group_by = chart.group_by
    if (s.column) query.column = s.column
    if (s.agg === 'quantile') query.level = String(s.level ?? 0.95)
    return query
}
