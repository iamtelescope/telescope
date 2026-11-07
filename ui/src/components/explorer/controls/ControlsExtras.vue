<template>
    <Button
        icon="pi pi-bell"
        class="mr-2"
        label="Create alert"
        text
        size="small"
        data-testid="create-alert-btn"
        @click="create"
    />
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
    router.push({ name: 'alertNew', query })
}
</script>
