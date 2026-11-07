<template>
    <div class="flex flex-col h-full min-h-0">
        <div class="flex-1 min-h-0 overflow-auto flex flex-col">
            <div
                v-for="row in rows"
                :key="row.group"
                class="bar-row flex items-center gap-3 px-1 rounded"
                :class="{ 'cursor-pointer hover:bg-surface-100 dark:hover:bg-surface-800': clickable }"
                :title="`${groupLabel(row.group)}: ${exactNumber(row.value)}`"
                @click="emit('rowClick', row.group)"
            >
                <div
                    class="w-[30%] max-w-56 shrink-0 truncate text-sm"
                    :class="
                        isEmptyGroup(row.group)
                            ? 'italic text-surface-500 dark:text-surface-400'
                            : 'text-surface-700 dark:text-surface-200'
                    "
                >
                    {{ groupLabel(row.group) }}
                </div>
                <div class="bar-track flex-1 min-w-0 h-full flex items-center">
                    <div
                        class="bar-fill rounded-r bg-[#2a78d6] dark:bg-[#3987e5]"
                        :style="{ width: `${row.percent}%` }"
                    ></div>
                </div>
                <div class="w-20 shrink-0 text-right text-sm tabular-nums text-surface-700 dark:text-surface-200">
                    {{ format(row.value) }}
                </div>
            </div>
        </div>
        <TruncatedHint :truncated="data.truncated" :count="data.rows.length" />
    </div>
</template>

<script setup>
import { computed } from 'vue'

import TruncatedHint from '@/components/dashboards/charts/TruncatedHint.vue'
import { seriesUnit, groupLabel, formatNumber, exactNumber } from '@/components/dashboards/charts/format.js'

const props = defineProps(['data', 'chart'])
const emit = defineEmits(['rowClick'])

const clickable = computed(() => !!props.chart.group_by)
const isEmptyGroup = (group) => group === '__none__' || group === ''
const unit = computed(() => seriesUnit(props.chart.series?.[0], props.chart.number_format))
const format = (v) => formatNumber(v, unit.value, { compact: true })

const rows = computed(() => {
    const items = props.data.rows.map((row) => ({ group: row.group, value: row.values[0] ?? 0 }))
    items.sort((a, b) => b.value - a.value)
    const max = Math.max(0, ...items.map((i) => i.value))
    // A minimum width keeps tiny non-zero values visible.
    return items.map((i) => ({ ...i, percent: max > 0 && i.value > 0 ? Math.max(0.5, (i.value / max) * 100) : 0 }))
})
</script>

<style scoped>
/* Rows share the tile height, between a readable minimum and a calm maximum, then scroll. */
.bar-row {
    flex: 1 1 0;
    min-height: 1.5rem;
    max-height: 2.75rem;
}
.bar-fill {
    height: clamp(0.5rem, 60%, 1.5rem);
}
</style>
