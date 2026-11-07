<template></template>

<script setup>
// Extra Tile.vue menu entries come from the exposed items array (PrimeVue MenuItem shape).
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps(['tile', 'range', 'timeZone'])
const route = useRoute()
const router = useRouter()

const items = computed(() => {
    const dashboard = route.params.dashboardSlug
    if (!dashboard || !props.tile?.chart || props.tile.chart.display === 'text') return []
    return [
        {
            label: 'Create alert',
            icon: 'pi pi-bell',
            command: () =>
                router.push({
                    name: 'alertNew',
                    query: { dashboard, tile: props.tile.id, title: props.tile.title || undefined },
                }),
        },
    ]
})
defineExpose({ items })
</script>
