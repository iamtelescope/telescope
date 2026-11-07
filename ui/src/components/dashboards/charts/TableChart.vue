<template>
    <div class="flex flex-col h-full min-h-0">
        <DataTable
            :value="rows"
            size="small"
            scrollable
            scrollHeight="flex"
            removableSort
            stripedRows
            class="chart-table flex-1 min-h-0 text-sm"
            :rowHover="true"
            :rowClass="() => (clickable ? 'cursor-pointer' : '')"
            @row-click="(e) => emit('rowClick', e.data.group)"
        >
            <Column v-if="groupColumn" field="group" :header="groupColumn.name" sortable>
                <template #body="{ data: row }">
                    <span
                        :class="{ 'italic text-surface-500 dark:text-surface-400': isEmptyGroup(row.group) }"
                        :title="groupLabel(row.group)"
                    >
                        {{ groupLabel(row.group) }}
                    </span>
                </template>
            </Column>
            <Column
                v-for="col in valueColumns"
                :key="col.field"
                :field="col.field"
                :header="col.name"
                sortable
                headerClass="text-right"
                bodyClass="text-right tabular-nums whitespace-nowrap"
                :pt="{ columnHeaderContent: { class: 'justify-end' } }"
            >
                <template #body="{ data: row }">
                    <span :title="exactNumber(row[col.field])">{{ col.format(row[col.field]) }}</span>
                </template>
            </Column>
        </DataTable>
        <TruncatedHint :truncated="data.truncated" :count="data.rows.length" />
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { DataTable, Column } from 'primevue'

import TruncatedHint from '@/components/dashboards/charts/TruncatedHint.vue'
import {
    seriesLabel,
    seriesUnit,
    groupLabel,
    formatNumber,
    exactNumber,
} from '@/components/dashboards/charts/format.js'

const props = defineProps(['data', 'chart'])
const emit = defineEmits(['rowClick'])

const clickable = computed(() => !!props.chart.group_by)
const isEmptyGroup = (group) => group === '__none__' || group === ''

const groupColumn = computed(() => props.data.columns.find((c) => c.kind === 'group'))
const valueColumns = computed(() => {
    const defs = props.chart.series || []
    const format = props.chart.number_format
    return props.data.columns
        .filter((c) => c.kind === 'value')
        .map((c, idx) => {
            const unit = seriesUnit(defs[idx], format)
            return {
                name: defs[idx] ? seriesLabel(defs[idx]) : c.name,
                field: `v${idx}`,
                format: (v) => formatNumber(v, unit, { decimals: unit === 'number' ? format?.decimals : undefined }),
            }
        })
})
const rows = computed(() =>
    props.data.rows.map((row) => {
        const item = { group: row.group }
        row.values.forEach((v, idx) => (item[`v${idx}`] = v))
        return item
    }),
)
</script>

<style scoped>
.chart-table :deep(.p-datatable-thead > tr > th) {
    font-weight: 500;
    white-space: nowrap;
}
</style>
