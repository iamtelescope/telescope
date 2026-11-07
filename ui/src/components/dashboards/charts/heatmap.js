// Geometry and colors of the heatmap tile; layout ideas from HyperDX components/DBHeatmapChart (MIT).

// One blue ramp, light to dark; dark mode runs it from the surface up to the light end.
const RAMP = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
const DARK_RAMP = ['#0d366b', '#184f95', '#256abf', '#3987e5', '#6da7ec', '#9ec5f4', '#cde2fb']

// Counts map to the ramp on a log scale, so a few hot cells do not wash out the rest.
export const cellColor = (count, max, dark) => {
    const ramp = dark ? DARK_RAMP : RAMP
    if (!count || !max) return null
    const t = max > 1 ? Math.log1p(count) / Math.log1p(max) : 1
    return ramp[Math.min(ramp.length - 1, Math.floor(t * ramp.length))]
}

export const legendColors = (dark) => (dark ? DARK_RAMP : RAMP)

// Continuous bucket position (0 = bottom of bucket 0) of a value, and back.
export const valueToPos = (value, edges) => {
    if (value <= edges[0]) return 0
    const last = edges.length - 1
    if (value >= edges[last]) return last
    let i = 0
    while (edges[i + 1] < value) i++
    return i + Math.log(value / edges[i]) / Math.log(edges[i + 1] / edges[i])
}

// The selection snapped outward to whole cells: inclusive ms times, and 0 for the open bottom bucket.
export const snapSelection = (data, i0, i1, b0, b1) => {
    const ts = data.timestamps
    const edges = data.y_edges
    return {
        t_min: ts[i0],
        t_max: ts[i1] + data.step_ms - 1,
        y_min: b0 === 0 ? 0 : edges[b0],
        y_max: edges[b1 + 1],
    }
}

// Cells inside a snapped selection, for the "N rows selected" hint.
export const countInSelection = (data, sel) => {
    if (!sel) return 0
    let total = 0
    for (const [t, b, n] of data.cells) {
        const ts = data.timestamps[t]
        const lo = b === 0 ? 0 : data.y_edges[b]
        if (ts >= sel.t_min && ts <= sel.t_max && lo >= sel.y_min && data.y_edges[b + 1] <= sel.y_max) total += n
    }
    return total
}

const PRECISION_UNITS = { 0: 'duration_s', 3: 'duration_ms', 6: 'duration_us', 9: 'duration_ns' }

// The number unit of an OTel traces source's duration column, or null for other columns.
export const durationUnit = (source, column) => {
    const role = source?.otelRole?.('duration')
    if (!role || role !== column) return null
    return PRECISION_UNITS[source.otelRole('duration_precision') ?? 9] || null
}
