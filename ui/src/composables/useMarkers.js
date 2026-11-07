import { ref, toRaw, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

import { AlertService } from '@/features/alerts/service.js'

const srv = new AlertService()
// A tile's chart object -> its tile id, registered by TileMenuExtras so a chart can find its tile alerts.
const tileOfChart = new WeakMap()
export const registerTileChart = (chart, tileId) => chart && tileOfChart.set(toRaw(chart), tileId)

// Vertical chart markers for a context getter ({ source } or { chart }, plus from/to in ms): alert firings.
export function useMarkers(context) {
    const markers = ref([])
    const route = useRoute()
    let abort = null
    const params = () => {
        const c = context() || {}
        if (!c.from || !c.to) return null
        if (c.source?.slug) return { source: c.source.slug, from: c.from, to: c.to }
        const tile = c.chart && tileOfChart.get(toRaw(c.chart))
        const dashboard = route?.params?.dashboardSlug
        if (tile && dashboard) return { dashboard, tile, from: c.from, to: c.to }
        return null
    }
    watch(
        () => JSON.stringify(params()),
        async () => {
            abort?.abort()
            const p = params()
            if (!p) return (markers.value = [])
            abort = new AbortController()
            const signal = abort.signal
            const response = await srv.markers(p, signal)
            if (signal.aborted) return
            markers.value = response.result
                ? response.data.map((m) => ({
                      time: m.time,
                      label: m.group_key ? `${m.name} (${m.group_key})` : m.name,
                  }))
                : []
        },
        { immediate: true },
    )
    onBeforeUnmount(() => abort?.abort())
    return markers
}

// Marker { time (ms), color? } to a Yagr x-axis plot line.
export const markerPlotLines = (markers) =>
    markers.map((m) => ({ value: m.time, color: m.color || 'rgba(239, 68, 68, 0.8)', width: 1 }))
