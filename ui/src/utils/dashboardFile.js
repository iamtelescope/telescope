export function exportDashboard(dashboard) {
    const file = {
        telescope_dashboard: 1,
        name: dashboard.name,
        description: dashboard.description,
        data: dashboard.data,
    }
    const blob = new Blob([JSON.stringify(file, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${dashboard.slug}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
}

// Returns an error text when the parsed file is not a telescope dashboard export.
export function checkDashboardFile(file) {
    if (!file || typeof file !== 'object' || Array.isArray(file)) return 'file is not a JSON object'
    if (file.telescope_dashboard !== 1) return 'telescope_dashboard must be 1'
    if (typeof file.name !== 'string' || !file.name) return 'name must be a non-empty string'
    if (file.description !== undefined && typeof file.description !== 'string') return 'description must be a string'
    const data = file.data
    if (!data || typeof data !== 'object' || !Array.isArray(data.tiles)) return 'data.tiles must be a list'
    for (const tile of data.tiles) {
        if (!tile || typeof tile !== 'object' || !tile.chart || typeof tile.chart !== 'object')
            return 'every tile must have a chart object'
    }
    return null
}

export function fileSourceSlugs(file) {
    const slugs = new Set()
    for (const tile of file.data.tiles) {
        if (tile.chart.display !== 'text' && tile.chart.source) slugs.add(tile.chart.source)
    }
    return [...slugs]
}

export function remapSources(data, mapping) {
    const result = JSON.parse(JSON.stringify(data))
    for (const tile of result.tiles) {
        if (mapping[tile.chart.source]) tile.chart.source = mapping[tile.chart.source]
    }
    return result
}
