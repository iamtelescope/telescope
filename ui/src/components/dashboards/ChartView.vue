<template>
    <TextTile v-if="chart.display === 'text'" :text="chart.text" />
    <div v-else-if="code === 'no_access'" class="flex items-center justify-center h-full text-sm text-surface-500">
        You don't have access to source {{ chart.source }}
    </div>
    <div v-else-if="code === 'query_failed'" class="h-full overflow-auto">
        <Error :error="error" />
    </div>
    <div v-else-if="validation && !validation.result" class="h-full overflow-auto">
        <ValidationError :validation="validation" message="Invalid tile settings" />
    </div>
    <div v-else-if="error" class="h-full overflow-auto">
        <Error :error="error" />
    </div>
    <div v-else-if="!data || data.kind !== expectedKind" class="flex items-center justify-center h-full">
        <Skeleton v-if="loading" width="100%" height="100%" />
    </div>
    <div v-else-if="isEmpty" class="flex items-center justify-center h-full text-sm text-surface-500">No data</div>
    <TimeSeriesChart
        v-else-if="data.kind === 'timeseries'"
        :data="data"
        :display="chart.display"
        :timeZone="timeZone"
        :groupBy="chart.group_by"
        @rangeSelected="(range) => emit('rangeSelected', range)"
    />
    <NumberChart v-else-if="data.kind === 'number'" :data="data" :numberFormat="chart.number_format" />
    <BarChart
        v-else-if="data.kind === 'table' && chart.display === 'bar'"
        :data="data"
        :numberFormat="chart.number_format"
        @rowClick="(group) => emit('rowClick', group)"
    />
    <TableChart
        v-else-if="data.kind === 'table'"
        :data="data"
        :numberFormat="chart.number_format"
        @rowClick="(group) => emit('rowClick', group)"
    />
</template>

<script setup>
import { computed } from 'vue'
import { Skeleton } from 'primevue'

import Error from '@/components/common/Error.vue'
import ValidationError from '@/components/common/ValidationError.vue'
import TimeSeriesChart from '@/components/dashboards/charts/TimeSeriesChart.vue'
import NumberChart from '@/components/dashboards/charts/NumberChart.vue'
import TableChart from '@/components/dashboards/charts/TableChart.vue'
import BarChart from '@/components/dashboards/charts/BarChart.vue'
import TextTile from '@/components/dashboards/charts/TextTile.vue'
import { isTimeseries } from '@/utils/dashboards.js'

const props = defineProps(['chart', 'data', 'loading', 'error', 'code', 'validation', 'timeZone'])
const emit = defineEmits(['rangeSelected', 'rowClick'])

const expectedKind = computed(() => {
    if (isTimeseries(props.chart.display)) return 'timeseries'
    return props.chart.display === 'number' ? 'number' : 'table'
})

const isEmpty = computed(() => {
    if (props.data.kind === 'timeseries') return !props.data.series.length
    if (props.data.kind === 'table') return !props.data.rows.length
    return false
})
</script>
