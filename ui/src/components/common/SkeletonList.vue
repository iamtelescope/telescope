<template>
    <DataTable>
        <Column v-for="i in columns" :key="i">
            <template #header>
                <Skeleton width="6rem" height="1rem" />
            </template>
            <template #body>
                <Skeleton width="100%" height="0.875rem" />
            </template>
        </Column>
        <template #empty>
            <div v-for="i in rows" :key="i" class="flex">
                <div v-for="j in columns" :key="j" class="flex-1 p-3">
                    <Skeleton width="100%" height="0.875rem" />
                </div>
            </div>
        </template>
    </DataTable>
</template>

<script setup>
import { Skeleton } from 'primevue'
import { DataTable, Column } from 'primevue'

const props = defineProps({
    columns: {
        type: Number,
        default: 5,
    },
    rows: {
        type: Number,
        default: 10,
    },
})
</script>
