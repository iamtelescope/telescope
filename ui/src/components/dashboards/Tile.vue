<template>
    <div
        class="flex flex-col h-full border rounded-lg border-neutral-300 dark:border-neutral-600 bg-white dark:bg-surface-900"
        data-testid="dashboard-tile"
    >
        <ProgressBar
            v-if="loading"
            class="bg-transparent rounded-t-lg rounded-b-none"
            mode="indeterminate"
            style="height: 2px"
        ></ProgressBar>
        <div v-else style="height: 2px; width: 100%"></div>
        <div
            class="tile-drag-handle flex items-center justify-between pl-2 pr-1 min-h-7"
            :class="{ 'cursor-move': editing }"
        >
            <div class="font-medium truncate" :title="tile.title">{{ tile.title }}</div>
            <Button icon="pi pi-ellipsis-v" text size="small" class="h-6 w-6 p-0" @click="toggleMenu" />
            <Menu ref="menu" :model="menuItems" :popup="true" />
        </div>
        <div class="flex-1 min-h-0 px-2 pb-2">
            <ChartView
                :chart="tile.chart"
                :data="data"
                :loading="loading"
                :error="error"
                :code="code"
                :validation="validation"
                :timeZone="timeZone"
                @rangeSelected="(r) => emit('rangeSelected', r)"
                @rowClick="onRowClick"
            />
        </div>
        <Dialog
            v-model:visible="fullscreen"
            modal
            :header="tile.title || 'Tile'"
            :style="{ width: '90vw' }"
            :breakpoints="{ '575px': '98vw' }"
        >
            <div class="h-[70vh]">
                <ChartView
                    v-if="fullscreen"
                    :chart="tile.chart"
                    :data="data"
                    :loading="loading"
                    :error="error"
                    :code="code"
                    :validation="validation"
                    :timeZone="timeZone"
                    @rangeSelected="onFullscreenRange"
                    @rowClick="onRowClick"
                />
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Menu, Dialog, ProgressBar } from 'primevue'

import ChartView from '@/components/dashboards/ChartView.vue'
import { useChartData } from '@/composables/dashboards/useDashboardService'
import { buildDrilldownRoute } from '@/utils/drilldown'

const props = defineProps(['tile', 'range', 'timeZone', 'editing', 'queue', 'refreshTick'])
const emit = defineEmits(['edit', 'duplicate', 'delete', 'rangeSelected'])

const router = useRouter()
const menu = ref()
const fullscreen = ref(false)
const { data, loading, error, code, validation, load, abort } = useChartData(props.queue)

const isText = computed(() => props.tile.chart.display === 'text')

const reload = () => {
    if (isText.value) return
    const c = props.tile.chart
    load(c.source, {
        from: props.range.from,
        to: props.range.to,
        query: c.query || '',
        dashboard_query: props.range.query || '',
        raw_query: c.raw_query || '',
        context_columns: c.context_columns || {},
        display: c.display,
        series: c.series,
        group_by: c.group_by || '',
        granularity: c.granularity || 'auto',
        limit: c.limit ?? 10,
    })
}

watch(() => [JSON.stringify(props.tile.chart), props.range.from, props.range.to, props.range.query], reload, {
    immediate: true,
})

watch(
    () => props.refreshTick,
    () => {
        if (!loading.value) reload()
    },
)

onBeforeUnmount(abort)

const openExplorer = (group) => {
    router.push(buildDrilldownRoute(props.tile.chart, props.range, group, props.timeZone))
}

const onRowClick = (group) => {
    if (props.tile.chart.group_by && !props.editing) openExplorer(group)
}

const onFullscreenRange = (range) => {
    fullscreen.value = false
    emit('rangeSelected', range)
}

const menuItems = computed(() => {
    const items = []
    if (props.editing) {
        items.push(
            { label: 'Edit', icon: 'pi pi-pencil', command: () => emit('edit') },
            { label: 'Duplicate', icon: 'pi pi-copy', command: () => emit('duplicate') },
            { label: 'Delete', icon: 'pi pi-trash', command: () => emit('delete') },
            { separator: true },
        )
    }
    if (!isText.value) {
        items.push({ label: 'Open in explorer', icon: 'pi pi-search', command: () => openExplorer() })
    }
    items.push({ label: 'Fullscreen', icon: 'pi pi-window-maximize', command: () => (fullscreen.value = true) })
    return items
})

const toggleMenu = (event) => {
    menu.value.toggle(event)
}
</script>
