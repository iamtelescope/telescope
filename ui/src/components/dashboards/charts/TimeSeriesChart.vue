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
import { seriesLabel, seriesUnit, groupLabel, formatNumber } from '@/components/dashboards/charts/format.js'
import {
    ACCENT,
    categoricalColor,
    isSeverityGrouping,
    severityColor,
    severityRank,
} from '@/components/dashboards/charts/palette.js'
import { getChartSettings } from '@/utils/chartSettings.js'

const props = defineProps(['data', 'chart', 'timeZone'])
const emit = defineEmits(['rangeSelected'])

const types = { line: 'line', stacked_area: 'area', stacked_bar: 'column' }
const isDark = useDark()
const wrapper = ref(null)
const mounted = ref(false)
const theme = computed(() => (isDark.value ? 'dark' : 'light'))

const groupsCount = computed(() => new Set(props.data.series.map((s) => s.group)).size)

// The bucket that contains "now" is still filling up; it is dropped so the chart does not end in a fake cliff.
const pointsCount = computed(() => {
    const ts = props.data.timestamps
    const inProgress = ts.length > 1 && ts[ts.length - 1] + (props.data.step_ms || 0) > Date.now()
    return inProgress ? ts.length - 1 : ts.length
})

const unit = computed(() => {
    const units = new Set((props.chart.series || []).map((s) => seriesUnit(s, props.chart.number_format)))
    return units.size === 1 ? [...units][0] : 'number'
})

const lines = computed(() => {
    const defs = props.chart.series || []
    const groups = props.data.series.map((s) => s.group)
    const severity = defs.length === 1 && isSeverityGrouping(props.chart.group_by, groups)
    const items = props.data.series.map((s) => {
        const label = seriesLabel(defs[s.series_index])
        let name = label
        if (s.group !== null && s.group !== undefined) {
            name = defs.length > 1 ? `${label} · ${groupLabel(s.group)}` : groupLabel(s.group)
        }
        return { ...s, name }
    })
    if (severity) items.sort((a, b) => severityRank(a.group) - severityRank(b.group))
    return items.map((s, idx) => {
        let color = severity ? severityColor(s.group, theme.value) : null
        if (!color) color = items.length === 1 ? ACCENT[theme.value] : categoricalColor(idx, theme.value)
        return { ...s, color }
    })
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
        formatValue: (v) => formatNumber(v, unit.value, { compact: true }),
        legend: series.length > 1,
        lineWidth: props.chart.display === 'line' ? 2 : 1,
        fitColumns: true,
        onSelect: (range) => emit('rangeSelected', range),
    })
})

onMounted(() => {
    mounted.value = true
})
</script>
