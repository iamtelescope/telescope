<template>
    <div ref="wrapper" class="flex flex-col h-full min-h-0">
        <div class="relative flex-1 min-h-0">
            <YagrChart v-if="settings" :settings="settings" :theme="theme" height="100%" @ready="onReady" />
            <span
                v-for="flag in flags"
                :key="`${flag.kind}-${flag.time}-${flag.label}`"
                class="chart-marker"
                :style="{ left: `${flag.left}px`, top: `${flag.top}px`, background: flag.color || ALERT_COLOR }"
                v-tooltip.top="flag.label"
                :aria-label="flag.label"
                :data-kind="flag.kind"
                :data-time="flag.time"
                data-testid="chart-marker"
            ></span>
        </div>
        <TruncatedHint :truncated="data.truncated" :count="groupsCount" />
    </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useDark } from '@vueuse/core'

import YagrChart from '@/components/common/YagrChart.vue'
import TruncatedHint from '@/components/dashboards/charts/TruncatedHint.vue'
import { seriesLabel, seriesUnit, groupLabel, formatTileValue } from '@/components/dashboards/charts/format.js'
import {
    ACCENT,
    categoricalColor,
    isSeverityGrouping,
    severityColor,
    severityRank,
} from '@/components/dashboards/charts/palette.js'
import { getChartSettings } from '@/utils/chartSettings.js'
import { useMarkers, markerPlotLines } from '@/composables/useMarkers.js'

const props = defineProps(['data', 'chart', 'timeZone'])
const emit = defineEmits(['rangeSelected'])

// Every dashboard time series shares one uPlot cursor sync group, so the crosshair follows across tiles.
const SYNC_KEY = 'telescope-dashboard'
const ALERT_COLOR = 'rgb(239, 68, 68)'

const types = { line: 'line', stacked_area: 'area', stacked_bar: 'column' }
const isDark = useDark()
const wrapper = ref(null)
const flags = ref([])
const mounted = ref(false)
const theme = computed(() => (isDark.value ? 'dark' : 'light'))
const markers = useMarkers(() => ({
    chart: props.chart,
    from: props.data.timestamps[0],
    to: props.data.timestamps[props.data.timestamps.length - 1],
}))

const groupsCount = computed(() => new Set(props.data.series.map((s) => s.group)).size)

// The bucket that contains "now" is still filling up; it is dropped so the chart does not end in a fake cliff.
const pointsCount = computed(() => {
    const ts = props.data.timestamps
    const inProgress = ts.length > 1 && ts[ts.length - 1] + (props.data.step_ms || 0) > Date.now()
    return inProgress ? ts.length - 1 : ts.length
})

const shownDefs = computed(() => (props.chart.series || []).filter((s) => !s.hidden))

const unit = computed(() => {
    const units = new Set(shownDefs.value.map((s) => seriesUnit(s, props.chart.number_format)))
    return units.size === 1 ? [...units][0] : 'number'
})

// Hidden series are formula operands; previous-period series reuse their current series' color.
const lines = computed(() => {
    const defs = props.chart.series || []
    const shown = props.data.series.filter((s) => !defs[s.series_index]?.hidden)
    const current = shown.filter((s) => !s.previous)
    const groups = current.map((s) => s.group)
    const severity = shownDefs.value.length === 1 && isSeverityGrouping(props.chart.group_by, groups)
    const named = (s) => {
        const label = seriesLabel(defs[s.series_index])
        let name = label
        if (s.group !== null && s.group !== undefined) {
            name = shownDefs.value.length > 1 ? `${label} · ${groupLabel(s.group)}` : groupLabel(s.group)
        }
        return { ...s, name: s.previous ? `${name} (previous)` : name }
    }
    const items = current.map(named)
    if (severity) items.sort((a, b) => severityRank(a.group) - severityRank(b.group))
    const colors = {}
    const result = items.map((s, idx) => {
        let color = defs[s.series_index]?.color || (severity ? severityColor(s.group, theme.value) : null)
        if (!color) color = items.length === 1 ? ACCENT[theme.value] : categoricalColor(idx, theme.value)
        colors[`${s.group}|${s.series_index}`] = color
        return { ...s, color }
    })
    const previous = shown
        .filter((s) => s.previous)
        .map((s) => ({ ...named(s), color: colors[`${s.group}|${s.series_index}`] || ACCENT[theme.value] }))
    return result.concat(previous)
})

const settings = computed(() => {
    if (!mounted.value) return null
    const n = pointsCount.value
    // Yagr lists and stacks series in reverse, so reversing keeps the legend in rank or severity order.
    const series = lines.value.map((s, idx) => ({
        name: s.name,
        id: `${idx}`,
        data: s.values.slice(0, n),
        stack: 'tile',
        color: s.color,
        // The previous period is an unstacked dashed line over the current one.
        ...(s.previous ? { type: 'line', stackGroup: 1, width: 1.5, dash: [6, 4] } : {}),
    }))
    series.reverse()
    const base = getChartSettings({
        type: types[props.chart.display],
        timestamps: props.data.timestamps.slice(0, n),
        series: series,
        timeZone: props.timeZone,
        theme: theme.value,
        width: wrapper.value.getBoundingClientRect().width,
        nameLabel: props.chart.group_by || 'Series',
        valueLabel: 'Value',
        escape: true,
        formatValue: (v) => formatTileValue(v, unit.value, props.chart.number_format, { compact: true }),
        legend: series.length > 1,
        lineWidth: props.chart.display === 'line' ? 2 : 1,
        fitColumns: true,
        plotLines: markerPlotLines(markers.value),
        // Room on the right for the last x tick label, which sits on the plot edge.
        padding: [14, 22, 0, 4],
        onSelect: (range) => emit('rangeSelected', range),
    })
    return {
        ...base,
        cursor: { ...base.cursor, sync: SYNC_KEY },
        // A synced tile moves its crosshair but keeps its tooltip hidden.
        tooltip: { ...base.tooltip, show: (y) => !!y.plugins.tooltip?.state.pinned || y.root.matches(':hover') },
        editUplotOptions: (opts) => {
            opts = base.editUplotOptions(opts)
            opts.cursor.sync = { key: SYNC_KEY, setSeries: false, scales: ['x', null] }
            opts.hooks = { ...opts.hooks, draw: [...(opts.hooks?.draw || []), placeFlags] }
            return opts
        },
    }
})

// Marker flags sit on top of the plot area, over their plot lines, so they can be hovered.
// uPlot sets the plot area offsets before drawing, even before its root is in the page.
const placeFlags = (u) => {
    const left = parseFloat(u.over.style.left) || 0
    const top = parseFloat(u.over.style.top) || 0
    const { min, max } = u.scales.x
    flags.value = markers.value
        .filter((m) => m.time >= min && m.time <= max)
        .map((m) => ({ ...m, left: left + u.valToPos(m.time, 'x'), top }))
}

// A pinned tooltip (click on the chart) offers the explorer at the hovered bucket.
let unpinOutside = null
const onReady = (yagr) => {
    // Yagr leaves the uPlot sync group at init; joining it syncs the crosshair.
    yagr.subscribe()
    document.removeEventListener('mousedown', unpinOutside)
    const tooltip = yagr.plugins.tooltip
    if (!tooltip) return
    const close = () => {
        tooltip.pin(false)
        tooltip.hide()
    }
    // The tooltip re-renders right after it pins, so the button is added on render too.
    const addButton = (elem, x) => {
        if (x === null || x === undefined || elem.querySelector('.tile-tooltip-explore')) return
        const button = document.createElement('button')
        button.type = 'button'
        button.className = 'tile-tooltip-explore'
        button.dataset.testid = 'tooltip-explore'
        button.textContent = 'Open in explorer at this bucket'
        button.addEventListener('click', () => {
            close()
            emit('rangeSelected', { from: x, to: x + (props.data.step_ms || 0), explore: true })
        })
        elem.appendChild(button)
    }
    tooltip.on('render', (elem, { state, data }) => state.pinned && addButton(elem, data?.x))
    tooltip.on('pin', (elem) => {
        addButton(elem, yagr.uplot.data[0][yagr.uplot.cursor.idx])
        document.removeEventListener('mousedown', unpinOutside)
        unpinOutside = (e) => {
            if (!elem.contains(e.target) && !yagr.root.contains(e.target)) close()
        }
        document.addEventListener('mousedown', unpinOutside)
    })
    tooltip.on('unpin', (elem) => {
        elem.querySelector('.tile-tooltip-explore')?.remove()
        document.removeEventListener('mousedown', unpinOutside)
    })
}
onBeforeUnmount(() => document.removeEventListener('mousedown', unpinOutside))

onMounted(() => {
    mounted.value = true
})
</script>

<style scoped>
.chart-marker {
    position: absolute;
    width: 9px;
    height: 9px;
    margin-left: -4.5px;
    margin-top: -2px;
    transform: rotate(45deg);
    border-radius: 1px;
    cursor: default;
    z-index: 1;
}
</style>

<style>
.tile-tooltip-explore {
    display: block;
    width: 100%;
    margin-top: 0.5rem;
    padding: 0.25rem 0.5rem;
    border-radius: 0.375rem;
    font-size: 0.8rem;
    font-weight: 500;
    color: #fff;
    background: var(--p-primary-600);
    cursor: pointer;
}
.tile-tooltip-explore:hover {
    background: var(--p-primary-700);
}
</style>
