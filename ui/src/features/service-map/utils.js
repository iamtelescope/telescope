// Colour scales, node sizes and formatting adapted from HyperDX components/ServiceMap/utils.ts;
// the layered layout replaces HyperDX's dagre.

export const METRICS = [
    { value: 'errorRate', label: 'Error rate' },
    { value: 'latency', label: 'Latency' },
    { value: 'throughput', label: 'Throughput' },
]
const HUE = { errorRate: 0, latency: 35, throughput: 210 }
const NEUTRAL = 'hsl(220 8% 82%)'

// Error rate (0..1) thresholds; "high" is the red bucket.
export const ERROR_ELEVATED = 0.01
export const ERROR_HIGH = 0.05

export const errorLevel = (rate) =>
    rate >= ERROR_HIGH ? 'high' : rate >= ERROR_ELEVATED ? 'elevated' : rate > 0 ? 'low' : 'none'
const ERROR_INTENSITY = { low: 0.35, elevated: 0.7, high: 1 }

const lerp = (from, to, t) => from + (to - from) * t
const ramp = (hue, t) => {
    t = Math.max(0, Math.min(1, t))
    const s = Math.round(lerp(35, 72, t))
    const l = Math.round(lerp(90, 42, t))
    return { fill: `hsl(${hue} ${s}% ${l}%)`, border: `hsl(${hue} ${s}% ${Math.max(l - 24, 18)}%)` }
}

export const metricValue = (node, metric) => {
    if (metric === 'errorRate') return node.error_rate
    if (metric === 'latency') return node.p95 || 0
    return node.requests + (node.outgoing || 0)
}

export function nodeColors(node, metric, max) {
    // A caller-only service has no server spans: nothing measured, so outline only.
    if (!node.requests) return { fill: 'transparent', border: 'var(--p-surface-400)', dashed: true }
    if (metric === 'errorRate') {
        const level = errorLevel(node.error_rate)
        return level === 'none'
            ? { fill: NEUTRAL, border: 'hsl(220 8% 58%)' }
            : ramp(HUE.errorRate, ERROR_INTENSITY[level])
    }
    return ramp(HUE[metric], max > 0 ? metricValue(node, metric) / max : 0)
}

export const legendGradient = (metric) =>
    metric === 'errorRate'
        ? `linear-gradient(to right, ${NEUTRAL} 0 25%, ${ramp(0, 0.35).fill} 25% 50%, ${ramp(0, 0.7).fill} 50% 75%, ${ramp(0, 1).fill} 75% 100%)`
        : `linear-gradient(to right, ${ramp(HUE[metric], 0).fill}, ${ramp(HUE[metric], 1).fill})`

export function nodeSize(throughput, max) {
    if (max <= 0 || throughput <= 0) return 32
    return Math.round(32 + Math.sqrt(Math.min(throughput, max) / max) * 28)
}

// Columns by longest path from the callers; a cycle stops growing after one pass per node.
export function layout(services, edges, dx = 220, dy = 110) {
    const rank = Object.fromEntries(services.map((s) => [s, 0]))
    for (let i = 0; i < services.length; i++) {
        let changed = false
        for (const e of edges) {
            if (rank[e.server] < rank[e.client] + 1) {
                rank[e.server] = rank[e.client] + 1
                changed = true
            }
        }
        if (!changed) break
    }
    const columns = {}
    for (const s of services) (columns[rank[s]] ||= []).push(s)
    const tallest = Math.max(0, ...Object.values(columns).map((c) => c.length))
    // Each column sorted by the mean row of its callers, to cut edge crossings.
    const row = {}
    const ranks = Object.keys(columns)
        .map(Number)
        .sort((a, b) => a - b)
    for (const r of ranks) {
        const callers = (s) => edges.filter((e) => e.server === s && e.client in row).map((e) => row[e.client])
        const key = (s) => (callers(s).length ? callers(s).reduce((a, b) => a + b) / callers(s).length : 0)
        columns[r].sort((a, b) => key(a) - key(b))
        columns[r].forEach((s, i) => (row[s] = i + (tallest - columns[r].length) / 2))
    }
    const positions = {}
    for (const s of services) positions[s] = { x: rank[s] * dx, y: row[s] * dy }
    return positions
}

export function formatRate(perSecond) {
    if (!Number.isFinite(perSecond) || perSecond <= 0) return '0 req/s'
    if (perSecond >= 1000) return `${(perSecond / 1000).toFixed(1)}k req/s`
    if (perSecond >= 1) return `${perSecond.toFixed(1)} req/s`
    return `${perSecond.toFixed(2)} req/s`
}

export const formatPercent = (rate) => `${(rate * 100).toFixed(rate && rate < 0.001 ? 2 : 1)}%`

export function formatMs(ms) {
    if (ms === null || ms === undefined) return '–'
    if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`
    return `${ms.toFixed(ms < 10 ? 2 : 0)} ms`
}

export const escapeFlyql = (value) => String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'")
