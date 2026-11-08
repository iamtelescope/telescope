<template>
    <div class="number-tile relative flex flex-col items-center justify-center h-full min-w-0 gap-1 px-2">
        <svg
            v-if="sparkline"
            class="absolute inset-x-0 bottom-0 w-full h-2/5 pointer-events-none"
            viewBox="0 0 100 40"
            preserveAspectRatio="none"
            data-testid="number-sparkline"
        >
            <path :d="sparkline.area" :fill="accent" fill-opacity="0.1" />
            <path
                :d="sparkline.line"
                :stroke="accent"
                stroke-opacity="0.45"
                stroke-width="1.5"
                fill="none"
                vector-effect="non-scaling-stroke"
            />
        </svg>
        <div
            class="number-value relative max-w-full truncate font-semibold tabular-nums leading-none"
            :class="{ 'text-surface-900 dark:text-surface-0': !ruleColorValue }"
            :style="ruleColorValue ? { color: ruleColorValue } : null"
            :title="exactNumber(data.value)"
            data-testid="number-value"
        >
            {{ text }}
        </div>
        <div class="relative max-w-full truncate text-sm text-surface-500 dark:text-surface-400" :title="label">
            {{ label }}
        </div>
        <div
            v-if="delta"
            class="relative text-xs tabular-nums text-surface-600 dark:text-surface-300"
            :title="`Previous period: ${exactNumber(data.previous_value)}`"
            data-testid="number-delta"
        >
            <i :class="delta.up ? 'pi pi-arrow-up' : 'pi pi-arrow-down'" style="font-size: 0.65rem"></i>
            {{ delta.text }} vs previous
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDark } from '@vueuse/core'

import { seriesLabel, seriesUnit, formatTileValue, exactNumber } from '@/components/dashboards/charts/format.js'
import { ACCENT } from '@/components/dashboards/charts/palette.js'
import { ruleColor, visibleIndex } from '@/utils/dashboards.js'

const props = defineProps(['data', 'chart'])

const isDark = useDark()
const series = computed(() => props.chart.series?.[visibleIndex(props.chart.series)])
// The series itself, e.g. "count" or "p95 Duration": rows may be spans, so no "rows" noun.
const label = computed(() => seriesLabel(series.value))
const text = computed(() =>
    formatTileValue(props.data.value, seriesUnit(series.value, props.chart.number_format), props.chart.number_format, {
        compact: true,
    }),
)
const ruleColorValue = computed(() => ruleColor(props.chart.color_rules, props.data.value))
const accent = computed(() => ruleColorValue.value || series.value?.color || ACCENT[isDark.value ? 'dark' : 'light'])

const delta = computed(() => {
    const { value, previous_value: previous } = props.data
    if (previous === undefined || previous === null || value === null || value === undefined) return null
    if (previous === 0) return value === 0 ? { up: true, text: '0%' } : null
    const change = ((value - previous) / Math.abs(previous)) * 100
    return { up: change >= 0, text: `${change >= 0 ? '+' : ''}${change.toFixed(Math.abs(change) < 10 ? 1 : 0)}%` }
})

// The series as an SVG path in a 100x40 box; null buckets count as gaps.
const sparkline = computed(() => {
    const values = props.data.sparkline?.values || []
    const points = values.map((v, i) => [i, v]).filter(([, v]) => v !== null && v !== undefined)
    if (points.length < 2) return null
    const max = Math.max(...points.map(([, v]) => v))
    const min = Math.min(0, ...points.map(([, v]) => v))
    const span = max - min || 1
    const x = (i) => (i / (values.length - 1)) * 100
    const y = (v) => 40 - ((v - min) / span) * 36
    const line = points.map(([i, v], k) => `${k ? 'L' : 'M'}${x(i).toFixed(2)},${y(v).toFixed(2)}`).join(' ')
    const first = x(points[0][0]).toFixed(2)
    const last = x(points[points.length - 1][0]).toFixed(2)
    return { line, area: `${line} L${last},40 L${first},40 Z` }
})
</script>

<style scoped>
.number-tile {
    container-type: size;
}
.number-value {
    font-size: clamp(1.5rem, min(14cqw, 40cqh), 3.5rem);
}
</style>
