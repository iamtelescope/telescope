<template>
    <div class="flex flex-col px-4 pt-4 min-h-screen" data-testid="dashboard">
        <ConfirmDialog />
        <DataView :loadings="[loading && !dashboard]" :errors="[error]">
            <template v-if="dashboard && draft">
                <div class="flex flex-wrap items-start justify-between gap-2 mb-2">
                    <div class="flex flex-col min-w-0">
                        <div class="text-2xl font-medium flex items-center">
                            <LayoutDashboard class="mr-2 w-6 h-6" />
                            <span class="truncate">{{ dashboard.name }}</span>
                            <Tag v-if="dashboard.shared" value="shared" severity="secondary" class="ml-2" />
                        </div>
                        <div v-if="dashboard.description" class="text-surface-500">{{ dashboard.description }}</div>
                    </div>
                    <div class="flex flex-wrap items-center gap-1">
                        <DatetimePicker
                            :from="range.from"
                            :to="range.to"
                            :timeZone="timeZone"
                            @rangeSelect="onRangeSelect"
                        />
                        <Select
                            v-model="draft.refresh"
                            :options="REFRESH_OPTIONS"
                            size="small"
                            v-tooltip.bottom="'Auto refresh'"
                        >
                            <template #value="{ value }"
                                ><i class="pi pi-sync mr-1 text-xs"></i>{{ value === 'off' ? 'Off' : value }}</template
                            >
                        </Select>
                        <Button icon="pi pi-refresh" text size="small" v-tooltip.bottom="'Refresh now'" @click="tick" />
                        <template v-if="dashboard.canEdit()">
                            <template v-if="editing">
                                <Button
                                    label="Add tile"
                                    icon="pi pi-plus"
                                    size="small"
                                    text
                                    @click="openEditor(null)"
                                />
                                <Button label="Cancel" severity="secondary" outlined size="small" @click="cancelEdit" />
                                <Button label="Save" icon="pi pi-check" size="small" :loading="saving" @click="save" />
                            </template>
                            <Button
                                v-else
                                label="Edit"
                                icon="pi pi-pencil"
                                size="small"
                                outlined
                                @click="editing = true"
                            />
                        </template>
                        <Button
                            icon="pi pi-ellipsis-v"
                            text
                            size="small"
                            @click="(e) => menu.toggle(e)"
                            data-testid="dashboard-menu-btn"
                        />
                        <Menu ref="menu" :model="menuItems" :popup="true" />
                    </div>
                </div>
                <div class="mb-2">
                    <InputText
                        v-model="filterInput"
                        size="small"
                        fluid
                        placeholder="Dashboard filter (FlyQL), applied to every tile. Press Enter to apply"
                        @keydown.enter="applyFilter"
                        data-testid="dashboard-filter"
                    />
                </div>
                <div
                    v-if="!draft.tiles.length"
                    class="flex flex-col items-center justify-center py-16 text-gray-500 dark:text-gray-400"
                >
                    <LayoutDashboard class="w-12 h-12 mb-4 opacity-40" />
                    <p class="text-lg font-medium mb-2">This dashboard has no tiles</p>
                    <Button
                        v-if="dashboard.canEdit()"
                        label="Add tile"
                        icon="pi pi-plus"
                        size="small"
                        @click="startAdd"
                    />
                </div>
                <GridLayout
                    v-else
                    v-model:layout="layout"
                    :col-num="24"
                    :row-height="32"
                    :margin="[8, 8]"
                    :is-draggable="editing"
                    :is-resizable="editing"
                    :vertical-compact="true"
                    @layout-updated="syncLayout"
                    class="-mx-2"
                >
                    <GridItem
                        v-for="item in layout"
                        :key="item.i"
                        :x="item.x"
                        :y="item.y"
                        :w="item.w"
                        :h="item.h"
                        :i="item.i"
                        :min-h="1"
                        :max-h="48"
                        drag-allow-from=".tile-drag-handle"
                    >
                        <Tile
                            :tile="tileById[item.i]"
                            :range="range"
                            :timeZone="timeZone"
                            :editing="editing"
                            :queue="queue"
                            :refreshTick="refreshTick"
                            @edit="openEditor(tileById[item.i])"
                            @duplicate="duplicateTile(tileById[item.i])"
                            @delete="deleteTile(tileById[item.i])"
                            @rangeSelected="onRangeSelect"
                        />
                    </GridItem>
                </GridLayout>
            </template>
        </DataView>
        <TileEditor
            v-model:visible="editorVisible"
            :tile="editorTile"
            :sources="sources || []"
            :range="range"
            :timeZone="timeZone"
            @apply="onEditorApply"
        />
    </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, ConfirmDialog, InputText, Menu, Select, Tag, useConfirm, useToast } from 'primevue'
import { GridLayout, GridItem } from 'grid-layout-plus'
import { LayoutDashboard } from 'lucide-vue-next'

import DataView from '@/components/common/DataView.vue'
import DatetimePicker from '@/components/explorer/controls/DatetimePicker.vue'
import Tile from '@/components/dashboards/Tile.vue'
import TileEditor from '@/components/dashboards/TileEditor.vue'
import { useGetDashboard, useSaveDashboard } from '@/composables/dashboards/useDashboardService'
import { useGetSources } from '@/composables/sources/useSourceService'
import { Dashboard } from '@/sdk/models/dashboard'
import { DashboardService } from '@/sdk/services/dashboard'
import { createRequestQueue } from '@/utils/requestQueue'
import { REFRESH_MS, REFRESH_OPTIONS, bottomY, defaultTileSize, newTileId } from '@/utils/dashboards'
import { exportDashboard } from '@/utils/dashboardFile'
import { fieldErrorsText } from '@/utils/utils'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const srv = new DashboardService()

const slug = route.params.dashboardSlug
const { dashboard, loading, error, load } = useGetDashboard(slug)
const { sources } = useGetSources()
const { update, create, remove } = useSaveDashboard()

const queue = createRequestQueue(4)
const draft = ref(null)
const layout = ref([])
const editing = ref(route.query.edit === '1')
const saving = ref(false)
const refreshTick = ref(0)
const filterInput = ref('')
const menu = ref()
const editorVisible = ref(false)
const editorTile = ref(null)

const toMillisOrString = (value) => (/^\d+$/.test(String(value)) ? parseInt(value) : value)

// URL query params override the saved range, filter and time zone until Save.
const range = computed(() => ({
    from: toMillisOrString(route.query.from ?? draft.value?.time.from),
    to: toMillisOrString(route.query.to ?? draft.value?.time.to),
    query: route.query.query ?? draft.value?.query ?? '',
}))
const timeZone = computed(() => route.query.time_zone ?? draft.value?.time.time_zone ?? 'UTC')
const tileById = computed(() => Object.fromEntries((draft.value?.tiles || []).map((t) => [t.id, t])))

const rebuildLayout = () => {
    layout.value = draft.value.tiles.map((t) => ({ i: t.id, x: t.x, y: t.y, w: t.w, h: t.h }))
}

const syncLayout = () => {
    for (const item of layout.value) {
        const tile = tileById.value[item.i]
        if (tile) Object.assign(tile, { x: item.x, y: item.y, w: item.w, h: item.h })
    }
}

const resetDraft = () => {
    draft.value = JSON.parse(JSON.stringify(dashboard.value.data))
    rebuildLayout()
}

watch(dashboard, (value) => {
    if (!value) return
    if (!value.canEdit()) editing.value = false
    if (!editing.value || !draft.value) resetDraft()
})

watch(
    () => range.value.query,
    (value) => (filterInput.value = value),
    { immediate: true },
)

const setQuery = (params) => {
    router.replace({ query: { ...route.query, ...params } })
}

const onRangeSelect = (params) => {
    const query = { from: params.from, to: params.to }
    if (params.timeZone) query.time_zone = params.timeZone
    setQuery(query)
}

const applyFilter = () => setQuery({ query: filterInput.value })

const tick = () => {
    refreshTick.value++
}

let timer = null
watch(
    () => draft.value?.refresh,
    (value) => {
        clearInterval(timer)
        timer = null
        if (REFRESH_MS[value]) {
            timer = setInterval(() => {
                if (!document.hidden) tick()
            }, REFRESH_MS[value])
        }
    },
)
onBeforeUnmount(() => clearInterval(timer))

const cancelEdit = () => {
    editing.value = false
    resetDraft()
}

const askReload = () => {
    confirm.require({
        header: 'Dashboard was changed elsewhere',
        message: 'Reload it? Your unsaved changes will be lost.',
        icon: 'pi pi-exclamation-triangle',
        rejectProps: { label: 'Keep editing', severity: 'secondary', outlined: true },
        acceptProps: { label: 'Reload' },
        accept: async () => {
            editing.value = false
            await load()
        },
    })
}

const body = (data, shared) => ({
    name: dashboard.value.name,
    description: dashboard.value.description,
    shared: shared ?? dashboard.value.shared,
    data: data,
    version: dashboard.value.version,
})

const handleUpdateResponse = (response) => {
    if (response.result) {
        dashboard.value = new Dashboard(response.data)
        response.sendToastMessages(toast)
        return true
    }
    if (response.validation?.fields?.version) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: response.validation.fields.version.join(', '),
            life: 6000,
        })
        askReload()
    } else if (response.validation && !response.validation.result) {
        const fields = fieldErrorsText(response.validation.fields)
        const text = [...(response.validation.non_field || []), fields].filter(Boolean).join('; ')
        toast.add({ severity: 'error', summary: 'Invalid dashboard', detail: text, life: 10000 })
    }
    response.sendToastErrors(toast)
    return false
}

const save = async () => {
    syncLayout()
    const data = JSON.parse(JSON.stringify(draft.value))
    data.time = { from: range.value.from, to: range.value.to, time_zone: timeZone.value }
    data.query = range.value.query
    saving.value = true
    const response = await update(slug, body(data))
    saving.value = false
    if (handleUpdateResponse(response)) {
        editing.value = false
        resetDraft()
        router.replace({ query: {} })
    }
}

// Sends the stored data, so unsaved edits stay in the draft.
const toggleShared = async () => {
    handleUpdateResponse(await update(slug, body(dashboard.value.data, !dashboard.value.shared)))
}

const duplicateDashboard = async () => {
    const response = await srv.getDashboard(slug)
    if (!response.result) return response.sendToastErrors(toast)
    const created = await create({
        name: `Copy of ${response.data.name}`,
        description: response.data.description,
        shared: false,
        data: response.data.data,
    })
    created.sendToast(toast)
    if (created.result) router.push({ name: 'dashboard', params: { dashboardSlug: created.data.slug } })
}

const deleteDashboard = () => {
    confirm.require({
        header: 'Delete dashboard',
        message: `Delete "${dashboard.value.name}"? This cannot be undone.`,
        icon: 'pi pi-exclamation-triangle',
        rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true },
        acceptProps: { label: 'Delete', severity: 'danger' },
        accept: async () => {
            const response = await remove(slug)
            response.sendToastErrors(toast)
            if (response.result) router.push({ name: 'dashboards' }).then(() => response.sendToastMessages(toast))
        },
    })
}

const menuItems = computed(() => {
    const d = dashboard.value
    if (!d) return []
    const items = [
        { label: 'Export JSON', icon: 'pi pi-download', command: () => exportDashboard(d) },
        { label: 'Duplicate', icon: 'pi pi-copy', command: duplicateDashboard },
    ]
    if (d.canEdit()) {
        items.push({
            label: d.shared ? 'Make private' : 'Share with everyone',
            icon: d.shared ? 'pi pi-lock' : 'pi pi-users',
            command: toggleShared,
        })
    }
    if (d.canDelete()) items.push({ label: 'Delete', icon: 'pi pi-trash', command: deleteDashboard })
    return items
})

const startAdd = () => {
    editing.value = true
    openEditor(null)
}

const openEditor = (tile) => {
    editorTile.value = tile
    editorVisible.value = true
}

const addTile = (title, chart) => {
    syncLayout()
    const size = defaultTileSize(chart.display)
    draft.value.tiles.push({
        id: newTileId(draft.value.tiles),
        x: 0,
        y: bottomY(draft.value.tiles),
        ...size,
        title,
        chart,
    })
    rebuildLayout()
}

const onEditorApply = ({ title, chart }) => {
    const existing = editorTile.value && tileById.value[editorTile.value.id]
    if (existing) {
        existing.title = title
        existing.chart = chart
    } else {
        addTile(title, chart)
    }
}

const duplicateTile = (tile) => {
    addTile(tile.title, JSON.parse(JSON.stringify(tile.chart)))
}

const deleteTile = (tile) => {
    syncLayout()
    draft.value.tiles = draft.value.tiles.filter((t) => t.id !== tile.id)
    rebuildLayout()
}
</script>
