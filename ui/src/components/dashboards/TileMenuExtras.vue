<template>
    <router-link
        v-if="alerts.length"
        :to="{ name: 'alertDetail', params: { alertId: alerts[0].id } }"
        class="flex items-center shrink-0 gap-0.5 px-1 text-xs"
        :class="firing ? 'text-red-600 dark:text-red-400' : 'text-surface-500 dark:text-surface-400'"
        v-tooltip.top="alerts.map((a) => `${a.name}: ${STATE_LABEL[a.state]}`).join('\n')"
        :data-testid="`tile-alert-badge-${tile.id}`"
    >
        <i class="pi pi-bell" style="font-size: 0.8rem" /><span v-if="alerts.length > 1">{{ alerts.length }}</span>
    </router-link>
</template>

<script>
// Dashboard slug -> { at, promise } of its tile alerts, shared by all tiles of the dashboard.
const cache = new Map()
</script>

<script setup>
// Extra Tile.vue menu entries come from the exposed items array (PrimeVue MenuItem shape).
// The template is the tile's alert badge; the tile's chart is registered for alert markers.
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { registerTileChart } from '@/composables/useMarkers.js'
import { AlertService } from '@/features/alerts/service.js'
import { STATE_LABEL } from '@/features/alerts/useAlerts.js'

const props = defineProps(['tile', 'range', 'timeZone'])
const route = useRoute()
const router = useRouter()
const srv = new AlertService()

watch(
    () => [props.tile?.chart, props.tile?.id],
    () => registerTileChart(props.tile?.chart, props.tile?.id),
    { immediate: true },
)

const dashboardAlerts = ref([])
watch(
    () => route.params.dashboardSlug,
    async (slug) => {
        dashboardAlerts.value = []
        if (!slug) return
        let entry = cache.get(slug)
        if (!entry || Date.now() - entry.at > 30_000) {
            entry = { at: Date.now(), promise: srv.list({ dashboard: slug }) }
            cache.set(slug, entry)
        }
        const response = await entry.promise
        if (route.params.dashboardSlug === slug) dashboardAlerts.value = response.result ? response.data : []
    },
    { immediate: true },
)
const alerts = computed(() => dashboardAlerts.value.filter((a) => a.tile_id === props.tile?.id))
const firing = computed(() => alerts.value.some((a) => a.state === 'ALERT'))

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
