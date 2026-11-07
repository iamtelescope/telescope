<template>
    <Button
        icon="pi pi-th-large"
        class="mr-2"
        label="Add to dashboard"
        text
        size="small"
        @click="open"
        data-testid="add-to-dashboard-btn"
    />
    <Dialog
        v-model:visible="visible"
        modal
        :header="added ? 'Tile added' : 'Add to dashboard'"
        :style="{ width: '34rem' }"
        :breakpoints="{ '575px': '95vw' }"
        data-testid="add-to-dashboard"
    >
        <div v-if="added" class="flex flex-col items-center text-center gap-3 py-4">
            <div class="flex items-center justify-center w-12 h-12 rounded-full bg-green-100 dark:bg-green-900">
                <i class="pi pi-check text-xl text-green-700 dark:text-green-300" />
            </div>
            <div>
                <span class="font-medium">{{ added.title || 'The tile' }}</span> was added to
                <span class="font-medium">{{ added.name }}</span
                >.
            </div>
        </div>
        <div v-else class="flex flex-col gap-4">
            <div
                class="flex flex-col gap-1 p-3 rounded-md text-sm bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700"
            >
                <div class="flex gap-2">
                    <span class="w-20 shrink-0 text-surface-500">Source</span>
                    <span class="font-medium truncate">{{ source?.name || 'none' }}</span>
                </div>
                <div class="flex gap-2">
                    <span class="w-20 shrink-0 text-surface-500">Filter</span>
                    <span class="font-mono truncate" :title="summary.query">{{ summary.query || 'none' }}</span>
                </div>
                <div v-if="summary.rawQuery" class="flex gap-2">
                    <span class="w-20 shrink-0 text-surface-500">Raw SQL</span>
                    <span class="font-mono truncate" :title="summary.rawQuery">{{ summary.rawQuery }}</span>
                </div>
                <div class="flex gap-2">
                    <span class="w-20 shrink-0 text-surface-500">Chart</span>
                    <span>{{ summary.chart }}</span>
                </div>
            </div>

            <div class="flex flex-col gap-1">
                <label for="add_tile_title" class="font-medium">Tile title</label>
                <InputText
                    id="add_tile_title"
                    v-model="title"
                    size="small"
                    maxlength="128"
                    autofocus
                    @keydown.enter="add"
                />
            </div>

            <div class="grid grid-cols-2 gap-2" role="radiogroup">
                <button
                    v-for="m in modes"
                    :key="m.value"
                    type="button"
                    role="radio"
                    :aria-checked="mode === m.value"
                    :disabled="m.value === 'existing' && !loading && !editable.length"
                    class="flex items-start gap-2 p-3 rounded-md border text-left transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    :class="
                        mode === m.value
                            ? 'border-primary bg-highlight'
                            : 'border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-800'
                    "
                    @click="mode = m.value"
                >
                    <i :class="m.icon" class="mt-1" />
                    <span class="flex flex-col">
                        <span class="font-medium">{{ m.label }}</span>
                        <span class="text-xs text-surface-500 dark:text-surface-400">{{ m.hint }}</span>
                    </span>
                </button>
            </div>

            <div v-if="mode === 'existing'" class="flex flex-col gap-1">
                <label class="font-medium">Dashboard</label>
                <Select
                    v-model="dashboardSlug"
                    :options="editable"
                    optionLabel="name"
                    optionValue="slug"
                    filter
                    autoFilterFocus
                    size="small"
                    :loading="loading"
                    placeholder="Choose a dashboard"
                    emptyMessage="No dashboards you can edit"
                    data-testid="add-to-dashboard-select"
                >
                    <template #option="{ option }">
                        <div class="flex items-center justify-between w-full gap-3">
                            <span class="truncate">{{ option.name }}</span>
                            <span class="flex items-center gap-2 shrink-0 text-xs text-surface-500">
                                <i v-if="option.shared" class="pi pi-users" v-tooltip.top="'Shared'" />
                                {{ option.tilesCount }} {{ option.tilesCount === 1 ? 'tile' : 'tiles' }}
                            </span>
                        </div>
                    </template>
                </Select>
            </div>
            <div v-else class="flex flex-col gap-1">
                <label for="add_dashboard_name" class="font-medium">New dashboard name</label>
                <InputText
                    id="add_dashboard_name"
                    v-model="newName"
                    size="small"
                    maxlength="255"
                    placeholder="e.g. Service overview"
                    @keydown.enter="add"
                />
                <span class="text-sm text-surface-500 dark:text-surface-400">Created private; share it later.</span>
            </div>
            <ErrorText v-if="problem" :text="problem" />
        </div>
        <template #footer>
            <template v-if="added">
                <Button label="Close" severity="secondary" outlined size="small" @click="visible = false" />
                <Button
                    label="Open dashboard"
                    icon="pi pi-arrow-right"
                    iconPos="right"
                    size="small"
                    data-testid="add-to-dashboard-open"
                    @click="openDashboard"
                />
            </template>
            <template v-else>
                <Button label="Cancel" severity="secondary" outlined size="small" @click="visible = false" />
                <Button
                    label="Add tile"
                    size="small"
                    :disabled="!canAdd"
                    :loading="saving"
                    data-testid="add-to-dashboard-submit"
                    @click="add"
                />
            </template>
        </template>
    </Dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dialog, InputText, Select } from 'primevue'

import ErrorText from '@/components/common/ErrorText.vue'
import { Dashboard } from '@/sdk/models/dashboard'
import { DashboardService } from '@/sdk/services/dashboard'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { bottomY, defaultTileSize, emptyDashboardData, newTileId } from '@/utils/dashboards'
import { fieldErrorsText } from '@/utils/utils'

// `tile` ({title, description, chart}) replaces the explorer's count() chart, e.g. from the chart explorer.
const props = defineProps(['source', 'tile'])

const srv = new DashboardService()
const router = useRouter()
const store = useSourceControlsStore()

const modes = [
    { value: 'existing', label: 'Existing dashboard', hint: 'Append to one you can edit', icon: 'pi pi-th-large' },
    { value: 'new', label: 'New dashboard', hint: 'Start a new one with this tile', icon: 'pi pi-plus' },
]
const visible = ref(false)
const mode = ref('existing')
const dashboards = ref([])
const loading = ref(false)
const saving = ref(false)
const dashboardSlug = ref(null)
const newName = ref('')
const title = ref('')
const problem = ref('')
const added = ref(null)

const editable = computed(() => dashboards.value.filter((d) => d.canEdit()))
const summary = computed(() => {
    const c = props.tile?.chart
    if (!c) {
        const by = store.graphGroupBy ? ` by ${store.graphGroupBy}` : ''
        return { query: store.query, rawQuery: store.rawQuery, chart: `count(), stacked bars${by}` }
    }
    const series = c.series?.length > 1 ? `, ${c.series.length} series` : ''
    return {
        query: c.query,
        rawQuery: c.raw_query,
        chart: `${c.display}${series}${c.group_by ? ` by ${c.group_by}` : ''}`,
    }
})
const canAdd = computed(() => (mode.value === 'existing' ? !!dashboardSlug.value : !!newName.value.trim()))

const open = async () => {
    problem.value = ''
    added.value = null
    if (props.tile) title.value = props.tile.title
    else title.value = store.graphGroupBy ? `${props.source.name} by ${store.graphGroupBy}` : props.source.name
    visible.value = true
    loading.value = true
    const response = await srv.getDashboards()
    loading.value = false
    dashboards.value = response.result ? response.data.map((d) => new Dashboard(d)) : []
    problem.value = response.errors.join(', ')
    if (!editable.value.length) mode.value = 'new'
    else if (!editable.value.some((d) => d.slug === dashboardSlug.value)) {
        const latest = [...editable.value].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))[0]
        dashboardSlug.value = latest.slug
    }
}

const buildTile = (tiles) => {
    if (!props.tile) return explorerTile(tiles)
    const { description, chart } = props.tile
    const tile = {
        id: newTileId(tiles),
        x: 0,
        y: bottomY(tiles),
        ...defaultTileSize(chart.display),
        title: title.value,
    }
    if (description) tile.description = description
    return { ...tile, chart: JSON.parse(JSON.stringify(chart)) }
}

const explorerTile = (tiles) => ({
    id: newTileId(tiles),
    x: 0,
    y: bottomY(tiles),
    w: 12,
    h: 8,
    title: title.value,
    chart: {
        source: props.source.slug,
        display: 'stacked_bar',
        series: [{ agg: 'count' }],
        query: store.query || '',
        raw_query: store.rawQuery || '',
        context_columns: JSON.parse(JSON.stringify(store.contextColumns || {})),
        group_by: store.graphGroupBy || '',
        granularity: 'auto',
        limit: 10,
    },
})

const describe = (response) => {
    const fields = fieldErrorsText(response.validation?.fields)
    return [...response.errors, ...(response.validation?.non_field || []), fields].filter(Boolean).join('; ')
}

const add = async () => {
    if (!canAdd.value || saving.value) return
    problem.value = ''
    saving.value = true
    let response
    if (mode.value === 'new') {
        const data = emptyDashboardData()
        data.tiles.push(buildTile([]))
        response = await srv.createDashboard({ name: newName.value.trim(), description: '', shared: false, data })
    } else {
        response = await srv.getDashboard(dashboardSlug.value)
        if (response.result) {
            const d = response.data
            const data = structuredClone(d.data)
            data.tiles.push(buildTile(data.tiles))
            response = await srv.updateDashboard(d.slug, {
                name: d.name,
                description: d.description,
                shared: d.shared,
                data,
                version: d.version,
            })
        }
    }
    saving.value = false
    if (response.result) {
        added.value = { slug: response.data.slug, name: response.data.name, title: title.value }
        if (mode.value === 'new') newName.value = ''
        return
    }
    // A version conflict means someone saved in between; pressing Add again reloads and retries.
    problem.value = response.validation?.fields?.version
        ? `${response.validation.fields.version.join(', ')}. Press Add tile to reload and try again.`
        : describe(response)
}

const openDashboard = () => {
    visible.value = false
    router.push({ name: 'dashboard', params: { dashboardSlug: added.value.slug } })
}
</script>
