export const escapeFlyqlValue = (value) => String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'")

// `group` is one value, or one value per column of a several-column group by.
export function buildDrilldownQuery(tileQuery, dashboardQuery, groupBy, group) {
    const parts = [tileQuery, dashboardQuery].filter((q) => q && q.trim())
    const columns = Array.isArray(group) ? (groupBy || '').split(',').map((c) => c.trim()) : [groupBy]
    const values = Array.isArray(group) ? group : [group]
    const groups = groupBy
        ? columns
              .map((c, i) => [c, values[i]])
              .filter(([c, v]) => c && v !== undefined && v !== null && v !== '__none__')
        : []
    if (!groups.length && parts.length < 2) return parts[0] || ''
    const conditions = parts.map((q) => `(${q})`)
    for (const [column, value] of groups) conditions.push(`${column} = '${escapeFlyqlValue(value)}'`)
    return conditions.join(' and ')
}

// Explorer route for a tile; `group` is the clicked table or bar row, if any.
export function buildDrilldownRoute(chart, range, group, timeZone) {
    const query = {
        from: range.from,
        to: range.to,
        timeZone,
        graph_group_by: (chart.group_by || '').split(',')[0].trim(),
    }
    const q = buildDrilldownQuery(chart.query, range.query, chart.group_by, group)
    if (q) query.query = q
    if (chart.raw_query) query.raw_query = chart.raw_query
    for (const [key, value] of Object.entries(chart.context_columns || {})) {
        query[`ctx_${key}`] = value
    }
    return { name: 'explore', params: { sourceSlug: chart.source }, query }
}
