<template>
    <div
        class="dash-page flex flex-col px-4 pt-3 pb-6 min-h-screen bg-surface-100 dark:bg-surface-950"
        :class="{ 'dash-page--kiosk': kiosk }"
        data-testid="dashboard"
    >
        <ConfirmDialog />
        <DataView :loadings="[loading && !dashboard]" :errors="[error]">
            <template v-if="dashboard && draft">
                <div
                    v-if="kiosk"
                    class="flex items-center gap-3 -mx-4 px-4 pb-3 mb-1 border-b border-surface-200 dark:border-surface-800"
                    data-testid="kiosk-header"
                >
                    <LayoutDashboard class="w-5 h-5 shrink-0 text-surface-500 dark:text-surface-400" />
                    <h1 class="m-0 text-2xl font-semibold truncate text-surface-900 dark:text-surface-0">
                        {{ dashboard.name }}
                    </h1>
                    <span class="text-surface-500 dark:text-surface-400 truncate" data-testid="kiosk-range">
                        {{ rangeLabel }}
                    </span>
                    <div class="flex-1"></div>
                    <span
                        class="flex items-center gap-1.5 shrink-0 text-sm text-surface-500 dark:text-surface-400"
                        data-testid="kiosk-live-status"
                    >
                        <span class="dash-live-dot" :class="{ 'dash-live-dot--busy': refreshing }"></span>
                        Live · every {{ refreshValue }} · Read-only
                    </span>
                    <Button
                        icon="pi pi-window-minimize"
                        text
                        rounded
                        severity="secondary"
                        aria-label="Exit kiosk mode"
                        v-tooltip.bottom="'Exit kiosk mode (Esc)'"
                        data-testid="kiosk-exit"
                        @click="exitKiosk"
                    />
                </div>
                <div
                    v-else
                    class="dash-toolbar sticky top-0 z-10 -mx-4 px-4 pt-1 pb-3 bg-surface-100 dark:bg-surface-950"
                >
                    <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
                        <div class="flex flex-col min-w-0 flex-1 basis-64">
                            <div class="flex items-center gap-2 min-w-0">
                                <LayoutDashboard class="w-5 h-5 shrink-0 text-surface-500 dark:text-surface-400" />
                                <h1
                                    class="m-0 text-2xl font-semibold truncate text-surface-900 dark:text-surface-0"
                                    :title="dashboard.name"
                                >
                                    {{ dashboard.name }}
                                </h1>
                                <Tag
                                    v-if="dashboard.shared"
                                    value="Shared"
                                    icon="pi pi-users"
                                    severity="secondary"
                                    class="dash-badge shrink-0"
                                />
                                <Tag
                                    v-if="editing"
                                    :value="dirty ? 'Unsaved changes' : 'Editing'"
                                    :icon="dirty ? 'pi pi-circle-fill' : 'pi pi-pencil'"
                                    :severity="dirty ? 'warn' : 'info'"
                                    class="dash-badge shrink-0"
                                    data-testid="dashboard-edit-state"
                                />
                            </div>
                            <div
                                v-if="dashboard.description"
                                class="mt-0.5 ml-7 text-surface-500 dark:text-surface-400 truncate"
                                :title="dashboard.description"
                            >
                                {{ dashboard.description }}
                            </div>
                        </div>
                        <div class="flex flex-wrap items-center gap-2">
                            <Button
                                v-if="zoomBase"
                                label="Reset zoom"
                                icon="pi pi-search-minus"
                                severity="secondary"
                                outlined
                                size="small"
                                v-tooltip.bottom="'Back to the range before zooming'"
                                data-testid="dashboard-reset-zoom"
                                @click="resetZoom"
                            />
                            <div class="dash-control dash-time">
                                <DatetimePicker
                                    :from="range.from"
                                    :to="range.to"
                                    :timeZone="timeZone"
                                    @rangeSelect="onRangeSelect"
                                />
                            </div>
                            <div class="dash-control flex items-stretch">
                                <Button
                                    :icon="refreshing ? 'pi pi-refresh pi-spin' : 'pi pi-refresh'"
                                    text
                                    severity="secondary"
                                    size="small"
                                    class="dash-refresh-btn"
                                    aria-label="Refresh"
                                    v-tooltip.bottom="'Refresh now'"
                                    @click="tick"
                                />
                                <Select
                                    v-model="draft.refresh"
                                    :options="refreshOptions"
                                    optionLabel="label"
                                    optionValue="value"
                                    size="small"
                                    class="dash-refresh-select"
                                    :class="{ 'dash-refresh-select--on': draft.refresh !== 'off' }"
                                    aria-label="Auto refresh"
                                    v-tooltip.bottom="'Auto refresh'"
                                >
                                    <template #value="{ value }">{{ value === 'off' ? 'Off' : value }}</template>
                                </Select>
                            </div>
                            <template v-if="dashboard.canEdit()">
                                <div class="hidden sm:block w-px h-6 mx-1 bg-surface-300 dark:bg-surface-700"></div>
                                <template v-if="editing">
                                    <Button
                                        label="Variables"
                                        icon="pi pi-sliders-h"
                                        severity="secondary"
                                        outlined
                                        size="small"
                                        :badge="variables.length ? String(variables.length) : undefined"
                                        badgeSeverity="secondary"
                                        @click="variablesVisible = true"
                                        data-testid="dashboard-variables-btn"
                                    />
                                    <Button
                                        label="Section"
                                        icon="pi pi-plus"
                                        severity="secondary"
                                        outlined
                                        size="small"
                                        data-testid="dashboard-add-section"
                                        @click="addSection"
                                    />
                                    <Button
                                        label="Add tile"
                                        icon="pi pi-plus"
                                        severity="secondary"
                                        outlined
                                        size="small"
                                        @click="openEditor(null)"
                                    />
                                    <Button label="Cancel" severity="secondary" text size="small" @click="cancelEdit" />
                                    <Button
                                        label="Save"
                                        icon="pi pi-check"
                                        size="small"
                                        :loading="saving"
                                        @click="save"
                                    />
                                </template>
                                <Button
                                    v-else
                                    label="Edit"
                                    icon="pi pi-pencil"
                                    severity="secondary"
                                    outlined
                                    size="small"
                                    @click="editing = true"
                                />
                            </template>
                            <Button
                                icon="pi pi-ellipsis-v"
                                severity="secondary"
                                outlined
                                size="small"
                                aria-label="Dashboard actions"
                                aria-haspopup="true"
                                @click="(e) => menu.toggle(e)"
                                data-testid="dashboard-menu-btn"
                            />
                            <Menu ref="menu" :model="menuItems" :popup="true" />
                        </div>
                    </div>
                    <div class="flex items-center gap-2 mt-3">
                        <IconField class="flex-1 min-w-0">
                            <InputIcon class="pi pi-filter" :class="{ 'text-primary': filterActive }" />
                            <InputText
                                v-model="filterInput"
                                size="small"
                                fluid
                                :class="{ 'dash-filter--active': filterActive }"
                                placeholder="Filter every tile with FlyQL, e.g. service = 'api' and level = 'ERROR'"
                                aria-label="Dashboard filter"
                                @keydown.enter="applyFilter"
                                @keydown.esc="filterInput = range.query"
                                data-testid="dashboard-filter"
                            />
                        </IconField>
                        <Button
                            v-if="filterDirty"
                            label="Apply"
                            icon="pi pi-arrow-right"
                            iconPos="right"
                            size="small"
                            outlined
                            v-tooltip.bottom="'Or press Enter'"
                            @click="applyFilter"
                        />
                        <Button
                            v-if="filterInput || range.query"
                            label="Clear"
                            icon="pi pi-times"
                            severity="secondary"
                            text
                            size="small"
                            @click="clearFilter"
                            data-testid="dashboard-filter-clear"
                        />
                    </div>
                    <VariableBar
                        :variables="variables"
                        :values="varValues"
                        :range="range"
                        :missing="range.missing"
                        @change="onVariableChange"
                    />
                </div>
                <div
                    v-if="!draft.tiles.length && !sections.length"
                    class="flex flex-1 items-start justify-center pt-12 pb-16"
                >
                    <div
                        class="flex flex-col items-center text-center max-w-md w-full px-8 py-12 rounded-xl border-2 border-dashed border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-900"
                    >
                        <div class="flex items-center justify-center w-12 h-12 mb-4 rounded-full dash-empty-icon">
                            <LayoutDashboard class="w-6 h-6 text-primary" />
                        </div>
                        <div class="text-base font-semibold text-surface-800 dark:text-surface-100">
                            This dashboard is empty
                        </div>
                        <p class="mt-1 mb-5 text-surface-500 dark:text-surface-400">
                            <template v-if="dashboard.canEdit()">
                                Add a tile to chart a query: time series, numbers, tables, top N lists or notes.
                            </template>
                            <template v-else>Its owner has not added any tiles yet.</template>
                        </p>
                        <Button
                            v-if="dashboard.canEdit()"
                            label="Add tile"
                            icon="pi pi-plus"
                            size="small"
                            @click="startAdd"
                        />
                    </div>
                </div>
                <template v-else>
                    <template v-for="group in groups" :key="group.id">
                        <div
                            v-if="group.section"
                            class="dash-section flex items-center gap-2 mt-3 mb-1 py-1.5 border-b border-surface-300 dark:border-surface-700"
                            data-testid="dashboard-section"
                        >
                            <Button
                                :icon="isCollapsed(group.section) ? 'pi pi-chevron-right' : 'pi pi-chevron-down'"
                                text
                                rounded
                                severity="secondary"
                                size="small"
                                :aria-label="isCollapsed(group.section) ? 'Expand section' : 'Collapse section'"
                                data-testid="dashboard-section-toggle"
                                @click="toggleSection(group.section)"
                            />
                            <InputText
                                v-if="editing"
                                v-model="group.section.title"
                                size="small"
                                maxlength="128"
                                class="font-semibold min-w-0 w-72"
                                placeholder="Section title"
                                aria-label="Section title"
                                @input="dirty = true"
                            />
                            <h2
                                v-else
                                class="m-0 text-lg font-semibold truncate text-surface-800 dark:text-surface-100 cursor-pointer"
                                @click="toggleSection(group.section)"
                            >
                                {{ group.section.title || 'Untitled section' }}
                            </h2>
                            <span class="text-sm text-surface-500 dark:text-surface-400 shrink-0">
                                {{ group.tiles.length }} {{ group.tiles.length === 1 ? 'tile' : 'tiles' }}
                            </span>
                            <div class="flex-1"></div>
                            <template v-if="editing">
                                <Button
                                    icon="pi pi-plus"
                                    label="Tile"
                                    text
                                    size="small"
                                    severity="secondary"
                                    @click="openEditor(null, group.id)"
                                />
                                <Button
                                    icon="pi pi-trash"
                                    text
                                    rounded
                                    size="small"
                                    severity="secondary"
                                    aria-label="Delete section"
                                    v-tooltip.top="'Delete section, keep its tiles'"
                                    @click="deleteSection(group.section)"
                                />
                            </template>
                        </div>
                        <GridLayout
                            v-if="
                                (group.section
                                    ? !isCollapsed(group.section)
                                    : group.tiles.length || !sections.length) && layouts[group.id]
                            "
                            v-model:layout="layouts[group.id]"
                            :col-num="GRID_COLUMNS"
                            :row-height="32"
                            :margin="[8, 8]"
                            :is-draggable="editing"
                            :is-resizable="editing"
                            :vertical-compact="true"
                            @layout-updated="syncLayout"
                            class="dash-grid -mx-2"
                            :class="{ 'dash-grid--editing': editing, 'min-h-16': group.section && editing }"
                        >
                            <GridItem
                                v-for="item in layouts[group.id]"
                                :key="item.i"
                                :x="item.x"
                                :y="item.y"
                                :w="item.w"
                                :h="item.h"
                                :i="item.i"
                                :min-h="2"
                                :min-w="2"
                                :max-h="48"
                                drag-allow-from=".tile-drag-handle"
                                drag-ignore-from="button"
                                @moved="dirty = true"
                                @resized="dirty = true"
                            >
                                <Tile
                                    :tile="tileById[item.i]"
                                    :range="range"
                                    :timeZone="timeZone"
                                    :editing="editing"
                                    :canEdit="dashboard.canEdit()"
                                    :queue="queue"
                                    :refreshTick="refreshTick"
                                    :kiosk="kiosk"
                                    :sections="sections"
                                    @edit="openEditor(tileById[item.i])"
                                    @duplicate="duplicateTile(tileById[item.i])"
                                    @delete="deleteTile(tileById[item.i])"
                                    @move="(section) => moveTile(tileById[item.i], section)"
                                    @rangeSelected="onZoom"
                                />
                            </GridItem>
                        </GridLayout>
                    </template>
                </template>
            </template>
        </DataView>
        <TileEditor
            v-model:visible="editorVisible"
            :tile="editorTile"
            :sources="sources || []"
            :range="range"
            :timeZone="timeZone"
            :sections="sections"
            :rawSql="true"
            @apply="onEditorApply"
        />
        <VariablesEditor
            v-model:visible="variablesVisible"
            :variables="variables"
            :sources="sources || []"
            @apply="onVariablesApply"
        />
    </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { useEventListener } from '@vueuse/core'
import {
    Button,
    ConfirmDialog,
    IconField,
    InputIcon,
    InputText,
    Menu,
    Select,
    Tag,
    useConfirm,
    useToast,
} from 'primevue'
import { GridLayout, GridItem } from 'grid-layout-plus'
import { LayoutDashboard } from 'lucide-vue-next'

import DataView from '@/components/common/DataView.vue'
import DatetimePicker from '@/components/explorer/controls/DatetimePicker.vue'
import Tile from '@/components/dashboards/Tile.vue'
import TileEditor from '@/components/dashboards/TileEditor.vue'
import VariableBar from '@/components/dashboards/variables/VariableBar.vue'
import VariablesEditor from '@/components/dashboards/variables/VariablesEditor.vue'
import { rangeText } from '@/components/dashboards/charts/format.js'
import { useGetDashboard, useSaveDashboard } from '@/composables/dashboards/useDashboardService'
import { useGetSources } from '@/composables/sources/useSourceService'
import { Dashboard } from '@/sdk/models/dashboard'
import { DashboardService } from '@/sdk/services/dashboard'
import { createRequestQueue } from '@/utils/requestQueue'
import {
    GRID_COLUMNS,
    REFRESH_MS,
    bottomY,
    REFRESH_OPTIONS,
    VARIABLE_URL_PREFIX,
    defaultTileSize,
    missingRequired,
    newTileId,
    newTilePosition,
    upgradeDashboardData,
    variableParams,
    variableRouteQuery,
    variableValues,
} from '@/utils/dashboards'
import { exportDashboard } from '@/utils/dashboardFile'
import { availableTimeZones } from '@/utils/datetimeranges'
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
// Grid items per section id; '' holds the tiles outside any section.
const layouts = ref({})
const collapsed = ref({})
const kiosk = computed(() => route.query.kiosk === '1')
const editing = ref(route.query.edit === '1' && !kiosk.value)
// Set by user edits only, so the grid's own compaction on load never counts as a change.
const dirty = ref(false)
const saving = ref(false)
const refreshTick = ref(0)
const filterInput = ref('')
const menu = ref()
const editorVisible = ref(false)
const editorTile = ref(null)
const variablesVisible = ref(false)

const toMillisOrString = (value) => (/^\d+$/.test(String(value)) ? parseInt(value) : value)

const variables = computed(() => draft.value?.variables || [])
const varValues = computed(() => variableValues(variables.value, route.query))

// URL query params override the saved range, filter, time zone and variables until Save.
const range = computed(() => ({
    from: toMillisOrString(route.query.from ?? draft.value?.time.from),
    to: toMillisOrString(route.query.to ?? draft.value?.time.to),
    query: route.query.query ?? draft.value?.query ?? '',
    params: variableParams(variables.value, varValues.value),
    missing: missingRequired(variables.value, varValues.value),
}))
const validZone = (tz) => (availableTimeZones.includes(tz) ? tz : null)
const timeZone = computed(() => validZone(route.query.time_zone) ?? validZone(draft.value?.time.time_zone) ?? 'UTC')
const refreshOptions = REFRESH_OPTIONS.map((v) => ({ value: v, label: v === 'off' ? 'Off' : `Every ${v}` }))
const refreshing = computed(() => queue.pending.value > 0)
// Kiosk mode always refreshes, every minute unless the dashboard sets an interval.
const refreshValue = computed(() => (kiosk.value && draft.value?.refresh === 'off' ? '1m' : draft.value?.refresh))
const rangeLabel = computed(() => `${rangeText(range.value.from, range.value.to, timeZone.value)} (${timeZone.value})`)
const filterActive = computed(() => !!range.value.query && filterInput.value === range.value.query)
const filterDirty = computed(() => filterInput.value !== range.value.query)
const tileById = computed(() => Object.fromEntries((draft.value?.tiles || []).map((t) => [t.id, t])))
const sections = computed(() => draft.value?.sections || [])
const groups = computed(() => [
    { id: '', section: null, tiles: (draft.value?.tiles || []).filter((t) => !t.section) },
    ...sections.value.map((section) => ({
        id: section.id,
        section,
        tiles: draft.value.tiles.filter((t) => t.section === section.id),
    })),
])

const rebuildLayout = () => {
    const result = { '': [] }
    for (const section of sections.value) result[section.id] = []
    for (const t of draft.value.tiles) {
        ;(result[t.section || ''] || result['']).push({ i: t.id, x: t.x, y: t.y, w: t.w, h: t.h })
    }
    layouts.value = result
}

const syncLayout = () => {
    for (const items of Object.values(layouts.value)) {
        for (const item of items) {
            const tile = tileById.value[item.i]
            if (tile) Object.assign(tile, { x: item.x, y: item.y, w: item.w, h: item.h })
        }
    }
}

// In view mode a collapse is local; while editing it is saved with the dashboard.
const isCollapsed = (section) => collapsed.value[section.id] ?? !!section.collapsed
const toggleSection = (section) => {
    const value = !isCollapsed(section)
    collapsed.value = { ...collapsed.value, [section.id]: value }
    if (editing.value) {
        section.collapsed = value
        dirty.value = true
    }
}

const addSection = () => {
    syncLayout()
    const used = [...draft.value.tiles, ...sections.value]
    draft.value.sections = [...sections.value, { id: newTileId(used), title: 'New section', collapsed: false }]
    dirty.value = true
    rebuildLayout()
}

// Its tiles move below the tiles outside any section.
const deleteSection = (section) => {
    syncLayout()
    let y = bottomY(draft.value.tiles.filter((t) => !t.section))
    for (const t of draft.value.tiles.filter((t) => t.section === section.id).sort((a, b) => a.y - b.y)) {
        delete t.section
        t.y = y + t.y
    }
    draft.value.sections = sections.value.filter((s) => s.id !== section.id)
    dirty.value = true
    rebuildLayout()
}

const resetDraft = () => {
    draft.value = upgradeDashboardData(JSON.parse(JSON.stringify(dashboard.value.data)))
    collapsed.value = {}
    dirty.value = false
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
    zoomBase.value = null
    const query = { from: params.from, to: params.to }
    if (params.timeZone) query.time_zone = params.timeZone
    setQuery(query)
}

// The range before the first drag-to-zoom on any tile; Reset zoom returns to it. Kiosk never zooms.
const zoomBase = ref(null)
const onZoom = (params) => {
    if (kiosk.value) return
    if (!zoomBase.value) zoomBase.value = { from: route.query.from, to: route.query.to }
    setQuery({ from: params.from, to: params.to })
}
const resetZoom = () => {
    const query = { ...route.query, ...zoomBase.value }
    for (const key of ['from', 'to']) if (query[key] === undefined) delete query[key]
    zoomBase.value = null
    router.replace({ query })
}

const enterKiosk = () => setQuery({ kiosk: '1' })
const exitKiosk = () => {
    const query = { ...route.query }
    delete query.kiosk
    router.replace({ query })
}
useEventListener(window, 'keydown', (e) => {
    if (e.key === 'Escape' && kiosk.value && !document.querySelector('.p-dialog')) exitKiosk()
})

const onVariableChange = (variable, value) => setQuery(variableRouteQuery(variable, value))

const onVariablesApply = (list) => {
    draft.value.variables = list
    dirty.value = true
    const names = new Set(list.map((v) => v.name))
    const stale = Object.keys(route.query).filter(
        (k) => k.startsWith(VARIABLE_URL_PREFIX) && !names.has(k.slice(VARIABLE_URL_PREFIX.length)),
    )
    if (stale.length) {
        const query = { ...route.query }
        stale.forEach((k) => delete query[k])
        router.replace({ query })
    }
}

const applyFilter = () => setQuery({ query: filterInput.value.trim() })

const clearFilter = () => {
    filterInput.value = ''
    if (range.value.query) setQuery({ query: '' })
}

const tick = () => {
    refreshTick.value++
}

watch(
    () => draft.value?.refresh,
    (value, old) => {
        if (editing.value && old !== undefined) dirty.value = true
    },
)

let timer = null
watch(refreshValue, (value) => {
    clearInterval(timer)
    timer = null
    if (REFRESH_MS[value]) {
        timer = setInterval(() => {
            if (!document.hidden) tick()
        }, REFRESH_MS[value])
    }
})
onBeforeUnmount(() => clearInterval(timer))

const confirmDiscard = () =>
    !dirty.value ||
    new Promise((resolve) => {
        confirm.require({
            header: 'Discard unsaved changes?',
            message: 'Your changes to this dashboard have not been saved.',
            icon: 'pi pi-exclamation-triangle',
            rejectProps: { label: 'Keep editing', severity: 'secondary', outlined: true },
            acceptProps: { label: 'Discard', severity: 'danger' },
            accept: () => resolve(true),
            reject: () => resolve(false),
            onHide: () => resolve(false),
        })
    })

onBeforeRouteLeave(() => confirmDiscard())
onBeforeRouteUpdate((to, from) => to.params.dashboardSlug === from.params.dashboardSlug || confirmDiscard())
useEventListener(window, 'beforeunload', (e) => {
    if (dirty.value) e.preventDefault()
})

const cancelEdit = async () => {
    if (!(await confirmDiscard())) return
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
    data.variables = data.variables.map((v) => {
        const { default: _old, ...rest } = v
        const value = varValues.value[v.name]
        return [].concat(value).length && value !== '' ? { ...rest, default: value } : rest
    })
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
    if (created.validation && !created.validation.result) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'This dashboard failed validation', life: 6000 })
    } else if (created.result) {
        router.push({ name: 'dashboard', params: { dashboardSlug: created.data.slug } })
    }
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
            if (response.result) {
                editing.value = false
                dirty.value = false
                router.push({ name: 'dashboards' }).then(() => response.sendToastMessages(toast))
            }
        },
    })
}

const menuItems = computed(() => {
    const d = dashboard.value
    if (!d) return []
    const items = [
        { label: 'Kiosk mode', icon: 'pi pi-desktop', command: enterKiosk, disabled: editing.value },
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
    if (d.canDelete())
        items.push({ separator: true }, { label: 'Delete', icon: 'pi pi-trash', command: deleteDashboard })
    return items
})

const startAdd = () => {
    editing.value = true
    openEditor(null)
}

// `section` presets the section of a new tile.
const openEditor = (tile, section = '') => {
    editing.value = true
    editorTile.value = tile || (section ? { section } : null)
    editorVisible.value = true
}

const tileExtras = (extras) => {
    const result = {}
    if (extras.description) result.description = extras.description
    if (extras.section) result.section = extras.section
    return result
}

const addTile = (title, chart, size = defaultTileSize(chart.display), extras = {}) => {
    syncLayout()
    const siblings = draft.value.tiles.filter((t) => (t.section || '') === (extras.section || ''))
    draft.value.tiles.push({
        id: newTileId([...draft.value.tiles, ...sections.value]),
        ...newTilePosition(siblings, size.w),
        ...size,
        title,
        ...tileExtras(extras),
        chart,
    })
    dirty.value = true
    rebuildLayout()
}

// Puts the tile at the bottom of its new section.
const placeInSection = (tile, section) => {
    if ((tile.section || '') === (section || '')) return
    const siblings = draft.value.tiles.filter((t) => t !== tile && (t.section || '') === (section || ''))
    tile.y = bottomY(siblings)
    tile.x = 0
    if (section) tile.section = section
    else delete tile.section
}

const onEditorApply = ({ title, description, section, chart }) => {
    const existing = editorTile.value?.id && tileById.value[editorTile.value.id]
    if (!existing) return addTile(title, chart, undefined, { description, section })
    syncLayout()
    existing.title = title
    existing.chart = chart
    if (description) existing.description = description
    else delete existing.description
    placeInSection(existing, section)
    dirty.value = true
    rebuildLayout()
}

const moveTile = (tile, section) => {
    syncLayout()
    placeInSection(tile, section)
    dirty.value = true
    rebuildLayout()
}

const duplicateTile = (tile) => {
    addTile(tile.title, JSON.parse(JSON.stringify(tile.chart)), { w: tile.w, h: tile.h }, tile)
}

const deleteTile = (tile) => {
    syncLayout()
    draft.value.tiles = draft.value.tiles.filter((t) => t.id !== tile.id)
    dirty.value = true
    rebuildLayout()
}
</script>

<style scoped>
.dash-control {
    border: 1px solid var(--p-surface-300);
    border-radius: var(--p-border-radius-md);
    background: var(--p-surface-0);
}
.dark .dash-control {
    border-color: var(--p-surface-700);
    background: var(--p-surface-900);
}
.dash-time :deep(.p-button) {
    margin: 0;
    color: var(--p-text-color);
}
.dash-refresh-btn {
    border-radius: 0;
    border-right: 1px solid var(--p-surface-300);
}
.dark .dash-refresh-btn {
    border-right-color: var(--p-surface-700);
}
.dash-refresh-select {
    border: 0;
    box-shadow: none;
    background: transparent;
    min-width: 4.5rem;
}
.dash-refresh-select--on :deep(.p-select-label) {
    color: var(--p-primary-color);
    font-weight: 600;
}
.dash-badge {
    font-size: 0.75rem;
    padding: 0.125rem 0.5rem;
}
.dash-badge :deep(.p-tag-icon) {
    font-size: 0.65rem;
}
.dash-filter--active {
    border-color: var(--p-primary-color);
    background: color-mix(in srgb, var(--p-primary-color) 5%, var(--p-inputtext-background));
}
.dash-page--kiosk {
    position: fixed;
    inset: 0;
    z-index: 900;
    overflow: auto;
}
.dash-live-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--p-green-500);
}
.dash-live-dot--busy {
    animation: dash-pulse 1s ease-in-out infinite;
}
@keyframes dash-pulse {
    50% {
        opacity: 0.35;
    }
}
.dash-empty-icon {
    background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.dash-grid {
    --vgl-placeholder-bg: var(--p-primary-color);
    --vgl-placeholder-opacity: 15%;
    --vgl-resizer-size: 14px;
    --vgl-resizer-border-color: var(--p-surface-400);
}
.dash-grid :deep(.vgl-item--placeholder) {
    border-radius: 0.5rem;
}
.dash-grid :deep(.vgl-item__resizer) {
    right: 3px;
    bottom: 3px;
}
.dash-grid :deep(.vgl-item__resizer:hover) {
    --vgl-resizer-border-color: var(--p-primary-color);
}
.dash-grid--editing {
    background-image: radial-gradient(var(--p-surface-300) 1px, transparent 1px);
    background-size: 16px 16px;
    border-radius: 0.5rem;
}
.dark .dash-grid--editing {
    background-image: radial-gradient(var(--p-surface-700) 1px, transparent 1px);
}
</style>
