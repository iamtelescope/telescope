<template>
    <div class="flex flex-col h-full min-h-0" data-testid="raw-sql-table">
        <DataTable
            :value="rows"
            size="small"
            scrollable
            scrollHeight="flex"
            removableSort
            stripedRows
            class="raw-sql-table flex-1 min-h-0 text-sm"
        >
            <Column
                v-for="(col, idx) in data.columns"
                :key="idx"
                :field="`c${idx}`"
                :sortField="integer(col) ? (row) => sortKey(row[`c${idx}`]) : `c${idx}`"
                :header="col.name"
                sortable
                :headerClass="numeric(col) ? 'text-right' : ''"
                :bodyClass="numeric(col) ? 'text-right tabular-nums whitespace-nowrap' : 'whitespace-nowrap'"
                :pt="numeric(col) ? { columnHeaderContent: { class: 'justify-end' } } : undefined"
            >
                <template #body="{ data: row }">
                    <span v-if="row[`c${idx}`] === null" class="italic text-surface-400">NULL</span>
                    <span v-else>{{ show(row[`c${idx}`]) }}</span>
                </template>
            </Column>
        </DataTable>
        <div v-if="data.truncated" class="text-xs text-surface-500 dark:text-surface-400 pt-1">
            truncated: showing the first {{ data.rows.length }} rows
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { DataTable, Column } from 'primevue'

const props = defineProps(['data'])

const NUMERIC_RE = /^(Nullable\()?(U?Int\d+|Float\d+|Decimal)/
const numeric = (col) => NUMERIC_RE.test(col.type)
const integer = (col) => /^(Nullable\()?U?Int\d+/.test(col.type)
// Integers beyond 2^53 arrive as strings to keep their digits; BigInt keeps their order.
const sortKey = (v) => (typeof v === 'string' ? BigInt(v) : v)
const show = (v) => (typeof v === 'object' ? JSON.stringify(v) : String(v))
const rows = computed(() => props.data.rows.map((row) => Object.fromEntries(row.map((v, idx) => [`c${idx}`, v]))))
</script>

<style scoped>
.raw-sql-table :deep(.p-datatable-thead > tr > th) {
    font-weight: 500;
    white-space: nowrap;
}
</style>
