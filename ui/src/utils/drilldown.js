export const escapeFlyqlValue = (value) => String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'")

export function buildDrilldownQuery(tileQuery, dashboardQuery, groupBy, group) {
    const parts = [tileQuery, dashboardQuery].filter((q) => q && q.trim())
    const hasGroup = groupBy && group !== undefined && group !== null && group !== '__none__'
    if (!hasGroup && parts.length < 2) return parts[0] || ''
    const conditions = parts.map((q) => `(${q})`)
    if (hasGroup) conditions.push(`${groupBy} = '${escapeFlyqlValue(group)}'`)
    return conditions.join(' and ')
}

// Explorer route for a tile; `group` is the clicked table or bar row, if any.
export function buildDrilldownRoute(chart, range, group) {
    const query = {
        from: range.from,
        to: range.to,
        graph_group_by: chart.group_by || '',
    }
    const q = buildDrilldownQuery(chart.query, range.query, chart.group_by, group)
    if (q) query.query = q
    if (chart.raw_query) query.raw_query = chart.raw_query
    for (const [key, value] of Object.entries(chart.context_columns || {})) {
        query[`ctx_${key}`] = value
    }
    return { name: 'explore', params: { sourceSlug: chart.source }, query }
}
