<template>
    <div ref="wrapper" class="flex flex-col h-full min-h-0">
        <div class="flex-1 min-h-0">
            <YagrChart v-if="settings" :settings="settings" :theme="theme" height="100%" />
        </div>
        <TruncatedHint :truncated="data.truncated" :count="groupsCount" />
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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

const types = { line: 'line', stacked_area: 'area', stacked_bar: 'column' }
const isDark = useDark()
const wrapper = ref(null)
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
    return getChartSettings({
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
})

onMounted(() => {
    mounted.value = true
})
</script>
