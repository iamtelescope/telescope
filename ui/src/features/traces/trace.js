// Helpers for the trace waterfall; the tree itself comes from the backend in display order.
import { entityColors } from '@/components/dashboards/charts/palette.js'
import { formatNumber } from '@/components/dashboards/charts/format.js'
import { currentTheme } from '@/utils/colors.js'

export const ERROR_COLOR = '#ef4444'

// The dashboards' per-name colors, so a service looks the same in a trace and on a tile.
export const serviceColors = (services) => Object.fromEntries(entityColors(services, currentTheme()))

// Durations read as on dashboards and the service map: "733 ms", "1.39 s", "12.5 µs".
export const formatDuration = (ns) => formatNumber(ns, 'duration_ns')

// Spans not hidden by a collapsed ancestor; `collapsed` is a Set of span indexes.
export function visibleSpans(spans, collapsed) {
    const out = []
    let hideBelow = null
    for (const span of spans) {
        if (hideBelow !== null && span.depth > hideBelow) continue
        hideBelow = collapsed.has(span.index) ? span.depth : null
        out.push(span)
    }
    return out
}

export const collapsibleIndexes = (spans) => spans.filter((s) => s.children > 0).map((s) => s.index)

// Evenly spaced axis ticks over [from, to] ns.
export function ticks(from, to, count = 5) {
    return Array.from({ length: count + 1 }, (_, i) => from + ((to - from) * i) / count)
}

// Offset of a nanosecond timestamp string from the trace start.
export const offsetNs = (tsNs, startNs) => Number(BigInt(tsNs) - BigInt(startNs))

export const isException = (event) => event.name === 'exception'

export const traceRoute = (slug, traceId, aroundMs, spanId) => ({
    name: 'trace',
    params: { sourceSlug: slug, traceId },
    query: { around: aroundMs ?? undefined, span: spanId || undefined },
})
