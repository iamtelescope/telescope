import { ref, toRaw, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

import { AlertService } from '@/features/alerts/service.js'
import HTTP from '@/utils/http'

const srv = new AlertService()
const http = new HTTP()
// A tile's chart object -> its tile id, registered by TileMenuExtras so a chart can find its tile alerts.
const tileOfChart = new WeakMap()
export const registerTileChart = (chart, tileId) => chart && tileOfChart.set(toRaw(chart), tileId)
// A tile's chart object -> a getter of its chartData body, registered by Tile.vue for release markers.
const requestOfChart = new WeakMap()
export const registerTileRequest = (chart, getter) => chart && requestOfChart.set(toRaw(chart), getter)

export const RELEASE_COLOR = 'rgba(99, 102, 241, 0.9)'

const alertMarkers = async (p, signal) => {
    const response = await srv.markers(p, signal)
    if (!response.result) return []
    return response.data.map((m) => ({
        time: m.time,
        kind: 'alert',
        label: m.group_key ? `${m.name} (${m.group_key})` : m.name,
    }))
}

const releaseMarkers = async (body, signal) => {
    const response = await http.Post(`ui/v1/otel/${body.source}/releases`, body, signal)
    if (!response.result) return []
    return response.data.map((r) => ({
        time: r.time,
        kind: 'release',
        color: RELEASE_COLOR,
        label: `Release ${r.service} ${r.version}`,
    }))
}

// Vertical chart markers for a context getter ({ source } or { chart }, plus from/to in ms):
// alert firings, and service.version releases for a dashboard tile.
export function useMarkers(context) {
    const markers = ref([])
    const route = useRoute()
    let abort = null
    const params = () => {
        const c = context() || {}
        if (!c.from || !c.to) return null
        if (c.source?.slug) return { alerts: { source: c.source.slug, from: c.from, to: c.to } }
        const tile = c.chart && tileOfChart.get(toRaw(c.chart))
        const request = c.chart && requestOfChart.get(toRaw(c.chart))
        const dashboard = route?.params?.dashboardSlug
        const result = {}
        if (tile && dashboard) result.alerts = { dashboard, tile, from: c.from, to: c.to }
        if (request) result.releases = { ...request(), from: c.from, to: c.to }
        return result.alerts || result.releases ? result : null
    }
    watch(
        () => JSON.stringify(params()),
        async () => {
            abort?.abort()
            const p = params()
            if (!p) return (markers.value = [])
            abort = new AbortController()
            const signal = abort.signal
            const [alerts, releases] = await Promise.all([
                p.alerts ? alertMarkers(p.alerts, signal) : [],
                p.releases ? releaseMarkers(p.releases, signal) : [],
            ])
            if (signal.aborted) return
            markers.value = [...alerts, ...releases]
        },
        { immediate: true },
    )
    onBeforeUnmount(() => abort?.abort())
    return markers
}

// Marker { time (ms), color?, kind? } to a Yagr x-axis plot line; releases are dashed.
export const markerPlotLines = (markers) =>
    markers.map((m) => ({
        value: m.time,
        color: m.color || 'rgba(239, 68, 68, 0.8)',
        width: 1,
        ...(m.kind === 'release' ? { dash: [4, 3] } : {}),
    }))
