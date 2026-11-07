// Helpers for the trace waterfall; the tree itself comes from the backend in display order.

// Service palette without red (errors) and green (logs), as in HyperDX's waterfall.
const SERVICE_COLORS = [
    '#3b82f6',
    '#8b5cf6',
    '#f59e0b',
    '#06b6d4',
    '#ec4899',
    '#6366f1',
    '#14b8a6',
    '#a16207',
    '#d946ef',
    '#64748b',
]
export const ERROR_COLOR = '#ef4444'

export const serviceColors = (services) =>
    Object.fromEntries(services.map((s, i) => [s, SERVICE_COLORS[i % SERVICE_COLORS.length]]))

export function formatDuration(ns) {
    const abs = Math.abs(ns)
    if (abs >= 1e9) return `${+(ns / 1e9).toFixed(abs >= 1e11 ? 0 : 2)}s`
    if (abs >= 1e6) return `${+(ns / 1e6).toFixed(abs >= 1e8 ? 0 : 2)}ms`
    if (abs >= 1e3) return `${+(ns / 1e3).toFixed(2)}µs`
    return `${ns}ns`
}

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
