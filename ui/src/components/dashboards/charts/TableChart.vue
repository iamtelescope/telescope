<template>
    <div class="flex flex-col h-full min-h-0">
        <DataTable
            :value="rows"
            size="small"
            scrollable
            scrollHeight="flex"
            removableSort
            class="flex-1 min-h-0"
            :rowHover="true"
            @row-click="(e) => emit('rowClick', e.data.group)"
        >
            <Column v-if="groupColumn" field="group" :header="groupColumn.name" sortable class="cursor-pointer" />
            <Column
                v-for="col in valueColumns"
                :key="col.field"
                :field="col.field"
                :header="col.name"
                sortable
                class="cursor-pointer text-right"
            >
                <template #body="slotProps">{{ formatValue(slotProps.data[col.field], numberFormat) }}</template>
            </Column>
        </DataTable>
        <TruncatedHint :truncated="data.truncated" :count="data.rows.length" />
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { DataTable, Column } from 'primevue'

import TruncatedHint from '@/components/dashboards/charts/TruncatedHint.vue'
import { formatValue } from '@/utils/dashboards.js'

const props = defineProps(['data', 'numberFormat'])
const emit = defineEmits(['rowClick'])

const groupColumn = computed(() => props.data.columns.find((c) => c.kind === 'group'))
const valueColumns = computed(() =>
    props.data.columns.filter((c) => c.kind === 'value').map((c, idx) => ({ name: c.name, field: `v${idx}` })),
)
const rows = computed(() =>
    props.data.rows.map((row) => {
        const item = { group: row.group }
        row.values.forEach((v, idx) => (item[`v${idx}`] = v))
        return item
    }),
)
</script>
