<template>
    <div class="flex flex-col h-full min-h-0">
        <div class="flex-1 min-h-0 overflow-auto">
            <div
                v-for="row in rows"
                :key="row.group"
                class="flex items-center gap-2 py-0.5 px-1 cursor-pointer rounded hover:bg-surface-100 dark:hover:bg-surface-800"
                @click="emit('rowClick', row.group)"
            >
                <div class="w-1/3 truncate text-sm" :title="row.group">{{ row.group }}</div>
                <div class="flex-1">
                    <div
                        class="h-4 rounded-sm"
                        :style="{ width: `${row.percent}%`, backgroundColor: getColor(row.group) }"
                    ></div>
                </div>
                <div class="w-24 text-right text-sm tabular-nums">{{ formatValue(row.value, numberFormat) }}</div>
            </div>
        </div>
        <TruncatedHint :truncated="data.truncated" :count="data.rows.length" />
    </div>
</template>

<script setup>
import { computed } from 'vue'

import TruncatedHint from '@/components/dashboards/charts/TruncatedHint.vue'
import { getColor } from '@/utils/colors.js'
import { formatValue } from '@/utils/dashboards.js'

const props = defineProps(['data', 'numberFormat'])
const emit = defineEmits(['rowClick'])

const rows = computed(() => {
    const items = props.data.rows.map((row) => ({ group: row.group, value: row.values[0] ?? 0 }))
    items.sort((a, b) => b.value - a.value)
    const max = Math.max(0, ...items.map((i) => i.value))
    return items.map((i) => ({ ...i, percent: max > 0 ? Math.max(0, (i.value / max) * 100) : 0 }))
})
</script>
