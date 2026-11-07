// Data and drill-down for the search (log rows) and patterns dashboard tiles (P5.2).
import HTTP from '@/utils/http'
import { Source } from '@/sdk/models/source'
import { SourceService } from '@/sdk/services/source'
import { buildDrilldownRoute } from '@/utils/drilldown'
import { boundForExplorer } from '@/utils/dashboards'
import { withPatternFilter } from '@/components/explorer/patterns/patterns'

const http = new HTTP()
const sourceSrv = new SourceService()
// Source slug -> promise of its Source model (or null), shared by every log tile on the page.
const sources = new Map()

export const PATTERN_SAMPLES = [1000, 10000, 50000, 100000]

export const fetchLogTile = (chart, body, signal, attribution) => {
    const qs = attribution ? `?${new URLSearchParams(attribution)}` : ''
    return http.Post(`ui/v1/sources/${chart.source}/${chart.display}Tile${qs}`, body, signal)
}

export const loadSource = (slug) => {
    if (!sources.has(slug)) {
        const promise = sourceSrv.getSource(slug).then((r) => (r.result ? new Source(r.data) : null))
        sources.set(slug, promise)
        promise.then((s) => s || sources.delete(slug))
    }
    return sources.get(slug)
}

// The request for a tile at the dashboard range; `before` asks for the page after a cursor.
export function logTileBody(chart, range, before) {
    const body = {
        from: range.from,
        to: range.to,
        query: chart.query || '',
        dashboard_query: range.query || '',
        raw_query: chart.raw_query || '',
        context_columns: chart.context_columns || {},
        params: range.params || {},
    }
    if (chart.display === 'search') {
        Object.assign(body, { columns: chart.columns || '', limit: chart.limit ?? 50 })
        if (before) body.before = before
    } else {
        Object.assign(body, { column: chart.column || '', sample: chart.sample ?? 10000 })
    }
    return body
}

// Explorer route for the tile: its columns or patterns mode, plus an optional pattern filter.
export function logTileExplorerRoute(chart, range, timeZone, patternFilter) {
    const bound = boundForExplorer(chart, range)
    const route = buildDrilldownRoute(bound.chart, bound.range, undefined, timeZone)
    delete route.query.graph_group_by
    if (chart.display === 'search' && chart.columns) route.query.columns = chart.columns
    if (patternFilter) route.query.query = withPatternFilter(route.query.query, patternFilter)
    else if (chart.display === 'patterns') route.query.mode = 'patterns'
    return route
}
