<template>
    <div class="flex flex-col h-full min-h-0 select-none" data-testid="heatmap-chart">
        <div ref="wrapper" class="relative flex-1 min-h-[8rem]">
            <canvas
                ref="canvas"
                class="absolute inset-0 cursor-crosshair"
                @mousedown="onDown"
                @mousemove="onMove"
                @mouseleave="hover = null"
                data-testid="heatmap-canvas"
            ></canvas>
            <div
                v-if="rect"
                class="absolute pointer-events-none border-2 border-orange-500 bg-orange-500/10 rounded-sm"
                :style="rect"
                data-testid="heatmap-selection"
            ></div>
            <div
                v-if="hover && !drag"
                class="absolute z-10 pointer-events-none rounded-md border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 px-2 py-1 text-xs shadow-md whitespace-nowrap"
                :style="{ left: `${hover.left}px`, top: `${hover.top}px` }"
                data-testid="heatmap-tooltip"
            >
                <div class="text-surface-500 dark:text-surface-400">{{ hover.time }}</div>
                <div>{{ hover.range }}</div>
                <div class="font-medium tabular-nums">{{ hover.count.toLocaleString() }} rows</div>
            </div>
        </div>
        <div class="flex items-center justify-end gap-1 pt-1 text-xs text-surface-500 dark:text-surface-400">
            <span>fewer</span>
            <span
                v-for="c in legend"
                :key="c"
                class="inline-block w-4 h-2.5 rounded-sm"
                :style="{ background: c }"
            ></span>
            <span>more rows (max {{ data.max.toLocaleString() }})</span>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useDark } from '@vueuse/core'
import { DateTime } from 'luxon'

import { formatNumber } from '@/components/dashboards/charts/format.js'
import { cellColor, legendColors, snapSelection, valueToPos } from '@/components/dashboards/charts/heatmap.js'

// `selection` is the outlier rectangle in data space; `selectable` makes a drag emit `select` instead of a time range.
const props = defineProps({
    data: Object,
    unit: { type: String, default: 'number' },
    timeZone: String,
    selection: Object,
    selectable: Boolean,
})
const emit = defineEmits(['select', 'rangeSelected'])

const PAD = { left: 64, right: 8, top: 6, bottom: 22 }
const isDark = useDark()
const wrapper = ref(null)
const canvas = ref(null)
const size = ref({ w: 0, h: 0 })
const hover = ref(null)
const drag = ref(null)
const legend = computed(() => legendColors(isDark.value))
let observer = null

const plot = computed(() => {
    const { w, h } = size.value
    const cols = props.data.timestamps.length
    const rows = props.data.y_edges.length - 1
    const pw = Math.max(1, w - PAD.left - PAD.right)
    const ph = Math.max(1, h - PAD.top - PAD.bottom)
    return { x: PAD.left, y: PAD.top, w: pw, h: ph, cols, rows, cw: pw / cols, ch: ph / rows }
})

const fmtValue = (v) => formatNumber(v, props.unit, { compact: true })
const fmtTime = (ms, withDate) =>
    DateTime.fromMillis(ms, { zone: props.timeZone || 'local' }).toFormat(withDate ? 'MM-dd HH:mm' : 'HH:mm')

const draw = () => {
    const el = canvas.value
    if (!el || !size.value.w) return
    const dpr = window.devicePixelRatio || 1
    el.width = size.value.w * dpr
    el.height = size.value.h * dpr
    el.style.width = `${size.value.w}px`
    el.style.height = `${size.value.h}px`
    const ctx = el.getContext('2d')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, size.value.w, size.value.h)
    const p = plot.value
    const dark = isDark.value
    const gap = p.cw > 4 ? 1 : 0
    for (const [t, b, n] of props.data.cells) {
        ctx.fillStyle = cellColor(n, props.data.max, dark)
        ctx.fillRect(p.x + t * p.cw, p.y + p.h - (b + 1) * p.ch, Math.max(1, p.cw - gap), Math.max(1, p.ch - gap))
    }
    ctx.fillStyle = dark ? '#a3a3a3' : '#6b7280'
    ctx.strokeStyle = dark ? '#404040' : '#e5e7eb'
    ctx.font = '11px sans-serif'
    ctx.beginPath()
    ctx.moveTo(p.x - 0.5, p.y)
    ctx.lineTo(p.x - 0.5, p.y + p.h + 0.5)
    ctx.lineTo(p.x + p.w, p.y + p.h + 0.5)
    ctx.stroke()
    // y labels on bucket edges, thinned to one per 18px.
    ctx.textAlign = 'right'
    ctx.textBaseline = 'middle'
    const edges = props.data.y_edges
    const every = Math.max(1, Math.ceil(18 / p.ch))
    for (let i = 0; i < edges.length; i += every) {
        ctx.fillText(fmtValue(edges[i]), p.x - 6, p.y + p.h - i * p.ch)
    }
    // x labels about every 110px, on bucket starts.
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    const ts = props.data.timestamps
    const withDate = ts.length && ts[ts.length - 1] - ts[0] > 86400000
    const step = Math.max(1, Math.ceil(110 / p.cw))
    for (let i = 0; i < ts.length; i += step) {
        ctx.fillText(fmtTime(ts[i], withDate), p.x + i * p.cw, p.y + p.h + 6)
    }
}

// Cell under a point, clamped to the plot.
const cellAt = (x, y) => {
    const p = plot.value
    const t = Math.min(p.cols - 1, Math.max(0, Math.floor((x - p.x) / p.cw)))
    const b = Math.min(p.rows - 1, Math.max(0, Math.floor((p.y + p.h - y) / p.ch)))
    return { t, b }
}

const inPlot = (x, y) => {
    const p = plot.value
    return x >= p.x && x <= p.x + p.w && y >= p.y && y <= p.y + p.h
}

const point = (e) => {
    const box = canvas.value.getBoundingClientRect()
    return { x: e.clientX - box.left, y: e.clientY - box.top }
}

const onMove = (e) => {
    const { x, y } = point(e)
    if (!inPlot(x, y)) {
        hover.value = null
        return
    }
    const { t, b } = cellAt(x, y)
    const cell = props.data.cells.find((c) => c[0] === t && c[1] === b)
    const edges = props.data.y_edges
    const ts = props.data.timestamps[t]
    hover.value = {
        left: Math.min(x + 12, size.value.w - 170),
        top: Math.max(0, y - 60),
        time: `${fmtTime(ts, true)} – ${fmtTime(ts + props.data.step_ms, false)}`,
        range: `${b === 0 ? '≤ ' : `${fmtValue(edges[b])} – `}${fmtValue(edges[b + 1])}`,
        count: cell ? cell[2] : 0,
    }
}

const onDown = (e) => {
    const start = point(e)
    if (!inPlot(start.x, start.y)) return
    drag.value = { x0: start.x, y0: start.y, x1: start.x, y1: start.y }
    const move = (ev) => {
        const { x, y } = point(ev)
        drag.value = { ...drag.value, x1: x, y1: y }
    }
    const up = () => {
        window.removeEventListener('mousemove', move)
        window.removeEventListener('mouseup', up)
        const d = drag.value
        drag.value = null
        if (Math.abs(d.x1 - d.x0) < 3 && Math.abs(d.y1 - d.y0) < 3) return
        const a = cellAt(Math.min(d.x0, d.x1), Math.max(d.y0, d.y1))
        const z = cellAt(Math.max(d.x0, d.x1), Math.min(d.y0, d.y1))
        const sel = snapSelection(props.data, a.t, z.t, a.b, z.b)
        if (props.selectable) emit('select', sel)
        else emit('rangeSelected', { from: sel.t_min, to: sel.t_max + 1 })
    }
    window.addEventListener('mousemove', move)
    window.addEventListener('mouseup', up)
}

// The drag rectangle while dragging, otherwise the persisted selection.
const rect = computed(() => {
    const p = plot.value
    if (drag.value) {
        const d = drag.value
        return {
            left: `${Math.min(d.x0, d.x1)}px`,
            top: `${Math.min(d.y0, d.y1)}px`,
            width: `${Math.abs(d.x1 - d.x0)}px`,
            height: `${Math.abs(d.y1 - d.y0)}px`,
        }
    }
    const s = props.selection
    if (!s || !size.value.w) return null
    const ts = props.data.timestamps
    const span = ts.length * props.data.step_ms
    const xOf = (ms) => p.x + Math.min(1, Math.max(0, (ms - ts[0]) / span)) * p.w
    const yOf = (v) => p.y + p.h - valueToPos(v, props.data.y_edges) * p.ch
    const left = xOf(s.t_min)
    const top = yOf(s.y_max)
    return {
        left: `${left}px`,
        top: `${top}px`,
        width: `${Math.max(2, xOf(s.t_max + 1) - left)}px`,
        height: `${Math.max(2, yOf(s.y_min) - top)}px`,
    }
})

const measure = () => {
    if (!wrapper.value) return
    size.value = { w: wrapper.value.clientWidth, h: wrapper.value.clientHeight }
}

onMounted(() => {
    observer = new ResizeObserver(measure)
    observer.observe(wrapper.value)
    measure()
})
onBeforeUnmount(() => observer && observer.disconnect())
watch([size, () => props.data, isDark, () => props.unit], draw, { flush: 'post' })
</script>
