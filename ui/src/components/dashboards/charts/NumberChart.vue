<template>
    <div class="number-tile flex flex-col items-center justify-center h-full min-w-0 gap-1 px-2">
        <div
            class="number-value max-w-full truncate font-semibold tabular-nums leading-none text-surface-900 dark:text-surface-0"
            :title="exactNumber(data.value)"
        >
            {{ text }}
        </div>
        <div class="max-w-full truncate text-sm text-surface-500 dark:text-surface-400" :title="label">{{ label }}</div>
    </div>
</template>

<script setup>
import { computed } from 'vue'

import { valueLabel, seriesUnit, formatNumber, exactNumber } from '@/components/dashboards/charts/format.js'

const props = defineProps(['data', 'chart'])

const series = computed(() => props.chart.series?.[0])
const label = computed(() => valueLabel(series.value))
const text = computed(() =>
    formatNumber(props.data.value, seriesUnit(series.value, props.chart.number_format), { compact: true }),
)
</script>

<style scoped>
.number-tile {
    container-type: size;
}
.number-value {
    font-size: clamp(1.5rem, min(14cqw, 40cqh), 3.5rem);
}
</style>
