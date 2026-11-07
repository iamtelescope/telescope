<template>
    <TextTile v-if="chart.display === 'text'" :text="chart.text" />
    <div
        v-else-if="code === 'no_access'"
        class="flex flex-col items-center justify-center gap-1.5 h-full p-2 text-center text-sm text-surface-500 dark:text-surface-400"
    >
        <i class="pi pi-lock text-xl"></i>
        <span>You don't have access to source {{ chart.source }}</span>
    </div>
    <div v-else-if="validation && !validation.result && code !== 'query_failed'" class="h-full overflow-auto">
        <ValidationError :validation="validation" message="Invalid tile settings" />
    </div>
    <div
        v-else-if="code === 'query_failed' || error"
        class="flex flex-col items-center justify-center gap-1.5 h-full p-2 text-center text-sm text-surface-500 dark:text-surface-400"
    >
        <i class="pi pi-exclamation-triangle text-xl text-red-500 dark:text-red-400"></i>
        <span class="font-medium text-surface-700 dark:text-surface-200">Query failed</span>
        <pre
            class="max-w-full max-h-[50%] overflow-auto whitespace-pre-wrap break-words text-left text-xs font-mono px-2"
            >{{ error }}</pre
        >
    </div>
    <div v-else-if="!data || data.kind !== expectedKind" class="h-full">
        <div v-if="loading" class="flex h-full gap-2 p-1" :class="skeletonLayout" data-testid="chart-skeleton">
            <template v-if="expectedKind === 'timeseries'">
                <Skeleton v-for="(h, idx) in skeletonBars" :key="idx" class="flex-1" :height="`${h}%`" />
            </template>
            <template v-else-if="expectedKind === 'number'">
                <Skeleton width="40%" height="2.5rem" />
                <Skeleton width="25%" height="0.875rem" />
            </template>
            <template v-else>
                <Skeleton v-for="idx in 5" :key="idx" height="1.25rem" :width="`${100 - idx * 12}%`" />
            </template>
        </div>
    </div>
    <div
        v-else-if="isEmpty"
        class="flex flex-col items-center justify-center gap-1.5 h-full p-2 text-center text-sm text-surface-500 dark:text-surface-400"
    >
        <i class="pi pi-chart-bar text-xl"></i>
        <span>No data in this time range</span>
    </div>
    <TimeSeriesChart
        v-else-if="data.kind === 'timeseries'"
        :data="data"
        :chart="chart"
        :timeZone="timeZone"
        @rangeSelected="(range) => emit('rangeSelected', range)"
    />
    <NumberChart v-else-if="data.kind === 'number'" :data="data" :chart="chart" />
    <PieChart
        v-else-if="data.kind === 'table' && chart.display === 'pie'"
        :data="data"
        :chart="chart"
        @rowClick="(group) => emit('rowClick', group)"
    />
    <BarChart
        v-else-if="data.kind === 'table' && chart.display === 'bar'"
        :data="data"
        :chart="chart"
        @rowClick="(group) => emit('rowClick', group)"
    />
    <TableChart
        v-else-if="data.kind === 'table'"
        :data="data"
        :chart="chart"
        @rowClick="(group) => emit('rowClick', group)"
    />
</template>

<script setup>
import { computed } from 'vue'
import { Skeleton } from 'primevue'

import ValidationError from '@/components/common/ValidationError.vue'
import TimeSeriesChart from '@/components/dashboards/charts/TimeSeriesChart.vue'
import NumberChart from '@/components/dashboards/charts/NumberChart.vue'
import TableChart from '@/components/dashboards/charts/TableChart.vue'
import BarChart from '@/components/dashboards/charts/BarChart.vue'
import PieChart from '@/components/dashboards/charts/PieChart.vue'
import TextTile from '@/components/dashboards/charts/TextTile.vue'
import { isTimeseries } from '@/utils/dashboards.js'

const props = defineProps(['chart', 'data', 'loading', 'error', 'code', 'validation', 'timeZone'])
const emit = defineEmits(['rangeSelected', 'rowClick'])

const skeletonBars = [35, 55, 45, 70, 50, 65, 40, 60, 75, 55, 45, 60]

const expectedKind = computed(() => {
    if (isTimeseries(props.chart.display)) return 'timeseries'
    return props.chart.display === 'number' ? 'number' : 'table'
})

const skeletonLayout = computed(() => {
    if (expectedKind.value === 'timeseries') return 'flex-row items-end'
    if (expectedKind.value === 'number') return 'flex-col items-center justify-center'
    return 'flex-col'
})

// A time series whose buckets are all zero or null has nothing to draw either.
const isEmpty = computed(() => {
    const d = props.data
    if (d.kind === 'timeseries') return !d.series.some((s) => s.values.some((v) => v !== null && v !== 0))
    if (d.kind === 'table') return !d.rows.length
    return d.value === null || d.value === undefined
})
</script>
