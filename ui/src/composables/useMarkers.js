import { ref } from 'vue'

// Vertical chart markers for a context getter ({ source } or { chart }, plus from/to in ms); none yet.
export function useMarkers(context) {
    return ref([])
}

// Marker { time (ms), color? } to a Yagr x-axis plot line.
export const markerPlotLines = (markers) =>
    markers.map((m) => ({ value: m.time, color: m.color || 'rgba(239, 68, 68, 0.8)', width: 1 }))
