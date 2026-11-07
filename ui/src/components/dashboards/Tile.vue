<template>
    <div
        class="dash-tile group flex flex-col h-full rounded-lg border bg-white dark:bg-surface-900"
        :class="editing ? 'dash-tile--editing' : 'border-surface-200 dark:border-surface-700'"
        data-testid="dashboard-tile"
    >
        <div
            class="tile-drag-handle flex items-center gap-1 h-9 shrink-0 pl-3 pr-1"
            :class="{ 'cursor-move': editing }"
        >
            <GripVertical v-if="editing" class="w-3.5 h-3.5 -ml-1.5 shrink-0 text-surface-400" />
            <div
                ref="titleEl"
                class="min-w-0 truncate text-base font-semibold text-surface-800 dark:text-surface-100"
                :class="{ 'italic font-normal text-surface-400 dark:text-surface-500': !tile.title }"
                v-tooltip.top="titleTruncated ? tile.title : null"
                @mouseenter="checkTruncated"
            >
                {{ tile.title || 'Untitled' }}
            </div>
            <i
                v-if="tile.description"
                class="pi pi-info-circle shrink-0 ml-1 text-surface-400"
                style="font-size: 0.8rem"
                v-tooltip.top="tile.description"
                :aria-label="tile.description"
                data-testid="tile-description"
            ></i>
            <i
                v-if="loading || logLoading"
                class="pi pi-spin pi-spinner shrink-0 ml-1 text-surface-400"
                style="font-size: 0.75rem"
                v-tooltip.top="'Loading'"
                data-testid="tile-loading"
            ></i>
            <div class="flex-1"></div>
            <div
                v-if="!kiosk"
                class="tile-actions flex items-center shrink-0 transition-opacity"
                :class="{ 'tile-actions--open': menuOpen }"
            >
                <Button
                    v-if="!isText"
                    icon="pi pi-compass"
                    text
                    rounded
                    severity="secondary"
                    size="small"
                    class="tile-action"
                    aria-label="Open in explorer"
                    v-tooltip.top="'Open in explorer'"
                    @click="openExplorer()"
                />
                <Button
                    v-if="canEdit"
                    icon="pi pi-pencil"
                    text
                    rounded
                    severity="secondary"
                    size="small"
                    class="tile-action"
                    aria-label="Edit tile"
                    v-tooltip.top="'Edit'"
                    @click="emit('edit')"
                />
                <template v-if="editing">
                    <Button
                        icon="pi pi-copy"
                        text
                        rounded
                        severity="secondary"
                        size="small"
                        class="tile-action"
                        aria-label="Duplicate tile"
                        v-tooltip.top="'Duplicate'"
                        @click="emit('duplicate')"
                    />
                    <Button
                        icon="pi pi-trash"
                        text
                        rounded
                        severity="secondary"
                        size="small"
                        class="tile-action tile-action--danger"
                        aria-label="Delete tile"
                        v-tooltip.top="'Delete'"
                        @click="emit('delete')"
                    />
                </template>
                <Button
                    icon="pi pi-ellipsis-v"
                    text
                    rounded
                    severity="secondary"
                    size="small"
                    class="tile-action"
                    aria-label="More actions"
                    aria-haspopup="true"
                    @click="toggleMenu"
                />
            </div>
            <Menu ref="menu" :model="menuItems" :popup="true" @show="menuOpen = true" @hide="menuOpen = false" />
            <TileMenuExtras ref="menuExtras" :tile="tile" :range="range" :timeZone="timeZone" />
        </div>
        <div class="flex-1 min-h-0 px-3 pb-2">
            <LogTileView
                v-if="isLog"
                :chart="tile.chart"
                :range="range"
                :timeZone="timeZone"
                :queue="queue"
                :refreshTick="refreshTick"
                :attribution="attribution()"
                @loading="(v) => (logLoading = v)"
            />
            <ChartView
                v-else
                :chart="tile.chart"
                :data="data"
                :loading="loading"
                :error="error"
                :code="code"
                :validation="validation"
                :timeZone="timeZone"
                :explore="true"
                @rangeSelected="onChartRange"
                @rowClick="onRowClick"
            />
        </div>
        <Dialog
            v-model:visible="fullscreen"
            modal
            :header="tile.title || 'Untitled'"
            :style="{ width: '90vw' }"
            :breakpoints="{ '575px': '98vw' }"
        >
            <div class="h-[70vh]">
                <LogTileView
                    v-if="fullscreen && isLog"
                    :chart="tile.chart"
                    :range="range"
                    :timeZone="timeZone"
                    :attribution="attribution()"
                />
                <ChartView
                    v-else-if="fullscreen"
                    :chart="tile.chart"
                    :data="data"
                    :loading="loading"
                    :error="error"
                    :code="code"
                    :validation="validation"
                    :timeZone="timeZone"
                    :explore="true"
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
import { Button, Menu, Dialog } from 'primevue'
import { GripVertical } from 'lucide-vue-next'

import ChartView from '@/components/dashboards/ChartView.vue'
import LogTileView from '@/components/dashboards/charts/LogTileView.vue'
import { logTileExplorerRoute } from '@/components/dashboards/charts/logTiles'
import TileMenuExtras from '@/components/dashboards/TileMenuExtras.vue'
import { useChartData } from '@/composables/dashboards/useDashboardService'
import { registerTileRequest } from '@/composables/useMarkers.js'
import { buildDrilldownRoute } from '@/utils/drilldown'
import { boundForExplorer, isLogTile } from '@/utils/dashboards'

const props = defineProps([
    'tile',
    'range',
    'timeZone',
    'editing',
    'canEdit',
    'queue',
    'refreshTick',
    'kiosk',
    'sections',
])
const emit = defineEmits(['edit', 'duplicate', 'delete', 'move', 'rangeSelected'])

const router = useRouter()
const menu = ref()
const menuExtras = ref()
const menuOpen = ref(false)
const titleEl = ref()
const titleTruncated = ref(false)
const fullscreen = ref(false)
const attribution = () => ({
    dashboard: router.currentRoute.value.params.dashboardSlug || '',
    tile: props.tile.id,
})
const { data, loading, error, code, validation, load, abort } = useChartData(props.queue, attribution)

const isText = computed(() => props.tile.chart.display === 'text')
// Log rows and patterns tiles load themselves, with paging.
const isLog = computed(() => isLogTile(props.tile.chart.display))
const logLoading = ref(false)

const checkTruncated = () => {
    titleTruncated.value = titleEl.value.scrollWidth > titleEl.value.clientWidth
}

const requestBody = () => {
    const c = props.tile.chart
    return {
        source: c.source,
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
        params: props.range.params || {},
        ...(c.compare ? { compare: true } : {}),
        ...(c.sparkline ? { sparkline: true } : {}),
    }
}

const reload = () => {
    if (isText.value || isLog.value) return
    const { source, ...body } = requestBody()
    load(source, body)
}

watch(
    () => props.tile.chart,
    (chart) => registerTileRequest(chart, requestBody),
    { immediate: true },
)

watch(
    () => [
        JSON.stringify(props.tile.chart),
        props.range.from,
        props.range.to,
        props.range.query,
        JSON.stringify(props.range.params),
    ],
    reload,
    { immediate: true },
)

watch(
    () => props.refreshTick,
    () => {
        if (!loading.value) reload()
    },
)

onBeforeUnmount(abort)

const openExplorer = (group) => {
    if (isLog.value) return router.push(logTileExplorerRoute(props.tile.chart, props.range, props.timeZone))
    const { chart, range } = boundForExplorer(props.tile.chart, props.range)
    router.push(buildDrilldownRoute(chart, range, group, props.timeZone))
}

const onRowClick = (group) => {
    if (props.tile.chart.group_by && !props.editing) openExplorer(group)
}

// A pinned tooltip asks for the explorer at its bucket; a drag zooms the dashboard.
const onChartRange = (range) => {
    if (!range.explore) return emit('rangeSelected', range)
    const { chart, range: bound } = boundForExplorer(props.tile.chart, { ...props.range, ...range })
    router.push(buildDrilldownRoute(chart, bound, undefined, props.timeZone))
}

const onFullscreenRange = (range) => {
    fullscreen.value = false
    onChartRange(range)
}

const menuItems = computed(() => {
    const items = []
    if (!isText.value) {
        items.push({ label: 'Open in explorer', icon: 'pi pi-compass', command: () => openExplorer() })
    }
    items.push({ label: 'Fullscreen', icon: 'pi pi-window-maximize', command: () => (fullscreen.value = true) })
    if (props.canEdit) {
        items.push({ separator: true }, { label: 'Edit', icon: 'pi pi-pencil', command: () => emit('edit') })
    }
    if (props.editing) {
        items.push(
            { label: 'Duplicate', icon: 'pi pi-copy', command: () => emit('duplicate') },
            { label: 'Delete', icon: 'pi pi-trash', command: () => emit('delete') },
        )
        const targets = [{ id: '', title: 'No section' }, ...(props.sections || [])].filter(
            (s) => s.id !== (props.tile.section || ''),
        )
        if (props.sections?.length) {
            items.push({
                label: 'Move to section',
                icon: 'pi pi-arrow-right-arrow-left',
                items: targets.map((s) => ({
                    label: s.title || 'Untitled section',
                    command: () => emit('move', s.id),
                })),
            })
        }
    }
    const extras = menuExtras.value?.items || []
    if (extras.length) items.push({ separator: true }, ...extras)
    return items
})

const toggleMenu = (event) => {
    menu.value.toggle(event)
}
</script>

<style scoped>
.dash-tile {
    box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.04);
    transition:
        border-color 0.15s,
        box-shadow 0.15s;
}
.dash-tile:hover {
    box-shadow: 0 2px 6px 0 rgb(0 0 0 / 0.07);
}
.dash-tile--editing {
    border-style: dashed;
    border-color: var(--p-surface-400);
}
.dash-tile--editing:hover {
    border-color: var(--p-primary-color);
}
.dark .dash-tile {
    box-shadow: none;
}
.dark .dash-tile--editing {
    border-color: var(--p-surface-600);
}
.dark .dash-tile--editing:hover {
    border-color: var(--p-primary-color);
}
.tile-actions {
    opacity: 0;
}
.dash-tile:hover .tile-actions,
.dash-tile:focus-within .tile-actions,
.tile-actions--open {
    opacity: 1;
}
@media (hover: none) {
    .tile-actions {
        opacity: 1;
    }
}
.tile-action {
    width: 1.75rem;
    height: 1.75rem;
    padding: 0;
}
.tile-action :deep(.p-button-icon) {
    font-size: 0.95rem;
}
.tile-action--danger:hover {
    color: var(--p-red-500);
}
</style>
