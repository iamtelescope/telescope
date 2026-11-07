<template>
    <div ref="wrapper" class="h-64" data-testid="alert-preview-chart">
        <YagrChart v-if="settings" :settings="settings" :theme="theme" height="100%" />
    </div>
    <div class="flex flex-wrap gap-4 mt-2 text-xs text-surface-500">
        <span
            ><span
                class="inline-block w-4 border-t-2 border-dashed align-middle mr-1"
                :style="{ borderColor: THRESHOLD }"
            />threshold</span
        >
        <span
            ><span class="inline-block w-3 h-3 align-middle mr-1 rounded-sm" :style="{ background: FIRING }" />{{
                bandLabel || 'would fire'
            }}</span
        >
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDark } from '@vueuse/core'

import YagrChart from '@/components/common/YagrChart.vue'
import { ACCENT, categoricalColor } from '@/components/dashboards/charts/palette.js'
import { formatNumber, groupLabel } from '@/components/dashboards/charts/format.js'
import { getChartSettings } from '@/utils/chartSettings.js'
import { localTimeZone } from '@/utils/datetimeranges'
import { isRange } from '@/features/alerts/useAlerts.js'

// Threshold shading adapted from HyperDX components/AlertPreviewChart.tsx (MIT).
const props = defineProps(['data', 'alert', 'bandLabel'])

const THRESHOLD = 'rgba(234, 88, 12, 0.9)'
const FIRING = 'rgba(239, 68, 68, 0.18)'
const isDark = useDark()
const theme = computed(() => (isDark.value ? 'dark' : 'light'))
const wrapper = ref(null)
const mounted = ref(false)
onMounted(() => (mounted.value = true))

const thresholdLines = computed(() => {
    const a = props.alert
    if (a.threshold === null || a.threshold === undefined) return []
    if (isRange(a.threshold_type) && a.threshold_max !== null && a.threshold_max !== undefined) {
        return [
            { value: [a.threshold, a.threshold_max], color: 'rgba(234, 88, 12, 0.12)' },
            { value: a.threshold, color: THRESHOLD, width: 2 },
            { value: a.threshold_max, color: THRESHOLD, width: 2 },
        ]
    }
    return [{ value: a.threshold, color: THRESHOLD, width: 2 }]
})

const firingBands = computed(() => {
    const { windows, step_ms: step, series } = props.data
    return windows
        .map((t, i) => (series.some((s) => s.would_fire[i]) ? { value: [t, t + step], color: FIRING } : null))
        .filter(Boolean)
})

const settings = computed(() => {
    if (!mounted.value) return null
    const series = props.data.series.map((s, idx) => ({
        name: s.group ? groupLabel(s.group) : 'value',
        id: `${idx}`,
        data: s.values,
        color: props.data.series.length === 1 ? ACCENT[theme.value] : categoricalColor(idx, theme.value),
    }))
    const result = getChartSettings({
        type: 'line',
        timestamps: props.data.windows,
        series,
        timeZone: localTimeZone,
        theme: theme.value,
        width: wrapper.value.getBoundingClientRect().width,
        nameLabel: 'Group',
        valueLabel: 'Value',
        escape: true,
        stacking: false,
        formatValue: (v) => formatNumber(v, 'number', { compact: true }),
        legend: series.length > 1,
        lineWidth: 2,
        plotLines: firingBands.value,
        padding: [14, 22, 0, 4],
    })
    result.axes.y = { ...(result.axes.y || {}), plotLines: thresholdLines.value }
    // Keep the threshold in view even when every value is far below it.
    const values = props.data.series.flatMap((s) => s.values).filter((v) => v !== null)
    const marks = thresholdLines.value.flatMap((l) => (Array.isArray(l.value) ? l.value : [l.value]))
    const max = Math.max(...values, ...marks)
    const min = Math.min(0, ...values, ...marks)
    result.scales.y = { ...result.scales.y, min, max: max > min ? max * 1.1 : min + 1 }
    return result
})
</script>
