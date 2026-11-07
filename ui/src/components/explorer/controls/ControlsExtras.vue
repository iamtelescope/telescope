<template>
    <!-- The tooltip sits on a wrapper: a disabled button gets no pointer events. -->
    <span
        class="mr-2 inline-block"
        v-tooltip.bottom="store.text ? 'Alerts cannot use the text search; put it in the query instead' : null"
    >
        <Button
            icon="pi pi-bell"
            label="Create alert"
            text
            size="small"
            data-testid="create-alert-btn"
            :disabled="!!store.text"
            @click="create"
        />
    </span>
</template>

<script setup>
// Extra explorer toolbar actions: "Create alert" opens the alert editor on the current search.
import { useRouter } from 'vue-router'
import { Button } from 'primevue'

import { useSourceControlsStore } from '@/stores/sourceControls'

const props = defineProps(['source'])
const router = useRouter()
const store = useSourceControlsStore()

const create = () => {
    const query = { source: props.source.slug }
    if (store.query) query.query = store.query
    if (store.rawQuery) query.raw_query = store.rawQuery
    if (store.graphGroupBy) query.group_by = store.graphGroupBy
    if (Object.keys(store.contextColumns || {}).length) query.context_columns = JSON.stringify(store.contextColumns)
    router.push({ name: 'alertNew', query })
}
</script>
