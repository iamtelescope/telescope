<template>
    <div>
        <Toolbar
            class="toolbar-slim border-none p-0 mb-2 whitespace-nowrap gap-y-1"
            :pt="{ start: { class: 'flex-wrap gap-y-1' }, end: { class: 'flex-wrap gap-y-1' } }"
            data-testid="explorer-controls"
        >
            <template #start>
                <Button
                    :class="{
                        'mr-2': true,
                        'bg-orange-600 border-orange-700 hover:bg-orange-700 dark:hover:text-white': paramsChanged,
                    }"
                    :label="loading ? 'Cancel' : 'Execute'"
                    size="small"
                    @click="handleSearch"
                    data-testid="explorer-execute-btn"
                >
                    <template #icon>
                        <i v-if="loading" class="pi pi-spin pi-spinner"></i>
                        <i v-else class="pi pi-caret-right"></i>
                    </template>
                </Button>
                <Button
                    icon="pi pi-share-alt"
                    class="mr-2"
                    severity="secondary"
                    outlined
                    aria-label="Share URL"
                    v-tooltip.bottom="'Copy a link to this search'"
                    size="small"
                    @click="handleShareURL"
                    :disabled="loading"
                    data-testid="explorer-share-btn"
                />
                <Button
                    icon="pi pi-download"
                    class="mr-2"
                    severity="secondary"
                    outlined
                    aria-label="Download"
                    v-tooltip.bottom="'Download the rows shown'"
                    size="small"
                    @click="(event) => downloadMenu.toggle(event)"
                    :disabled="loading"
                    aria-haspopup="true"
                    data-testid="explorer-download-btn"
                />
                <Menu ref="downloadMenu" :model="downloadItems" :popup="true" data-testid="explorer-download-menu" />
                <FloatLabel variant="on">
                    <Select
                        v-model="limit"
                        :options="limits"
                        placeholder="Limit"
                        size="small"
                        class="mr-2"
                        @update:model-value="sourceControlsStore.setLimit"
                    />
                    <label>Limit</label>
                </FloatLabel>
                <DatetimePicker
                    @rangeSelect="onRangeSelect"
                    :from="sourceControlsStore.from"
                    :to="sourceControlsStore.to"
                    :timeZone="sourceControlsStore.timeZone"
                />
                <Button
                    label="Live"
                    :icon="sourceControlsStore.live ? 'pi pi-pause' : 'pi pi-play'"
                    :severity="sourceControlsStore.live ? 'success' : 'secondary'"
                    :text="!sourceControlsStore.live"
                    size="small"
                    class="mr-2"
                    :aria-pressed="sourceControlsStore.live ? 'true' : 'false'"
                    @click="onLiveChange(!sourceControlsStore.live)"
                    v-tooltip.bottom="sourceControlsStore.live ? 'Stop live tail' : 'Start live tail'"
                    data-testid="explorer-live-btn"
                />
                <Select
                    v-if="sourceControlsStore.live"
                    :modelValue="sourceControlsStore.liveInterval"
                    @update:modelValue="sourceControlsStore.setLiveInterval"
                    :options="liveIntervals"
                    optionLabel="label"
                    optionValue="value"
                    size="small"
                    class="mr-2"
                    aria-label="Live refresh interval"
                    data-testid="explorer-live-interval"
                />
                <QuerySettings
                    :source="source"
                    :enableRawQueryEditorInitial="showRawQueryEditor"
                    @enableRawQueryEditorChange="onEnableRawQueryEditorChange"
                />
                <GraphSettings
                    :source="source"
                    :groupByInvalid="groupByInvalid"
                    :showGraph="sourceControlsStore.showGraph"
                    :graphGroupBy="sourceControlsStore.graphGroupBy"
                    @graphVisibilityChanged="onGraphVisibilityChanged"
                />
                <AddToDashboard :source="source" />
                <ControlsExtras :source="source" />
            </template>
            <template #end>
                <SavedViews :savedView="savedView" :source="source" class="mr-2" @change="onSavedViewChanged" />
                <ToggleButton
                    v-model="hideFilters"
                    onLabel="Show"
                    offLabel="Hide"
                    onIcon="pi pi-eye"
                    offIcon="pi pi-eye-slash"
                    size="small"
                    data-testid="explorer-toggle-controls-btn"
                />
            </template>
        </Toolbar>
        <div :class="{ hidden: hideFilters }" data-testid="explorer-filters">
            <div class="mb-2">
                <ContextColumns
                    v-if="source.contextColumns"
                    :source="source"
                    :contextColumns="sourceControlsStore.contextColumns"
                    :contextColumnsData="contextColumnsData"
                    @columnChanged="onContextFieldChanged"
                />
            </div>
            <div class="mb-2" data-testid="explorer-columns-editor">
                <ColumnsEditor
                    id="columns_editor"
                    @change="onFieldsChange"
                    :source="source"
                    :value="sourceControlsStore.columns"
                    :from="sourceControlsStore.from"
                    :to="sourceControlsStore.to"
                    @submit="handleSearch"
                />
            </div>
            <div v-if="textColumn" class="mb-2" data-testid="explorer-text-search">
                <IconField>
                    <InputIcon class="pi pi-search" />
                    <InputText
                        :modelValue="sourceControlsStore.text"
                        @update:modelValue="sourceControlsStore.setText"
                        @keydown.enter="handleSearch"
                        :placeholder="`Search text in ${textColumn} (case-insensitive)`"
                        :aria-label="`Search text in ${textColumn}`"
                        size="small"
                        fluid
                        data-testid="explorer-text-search-input"
                    />
                </IconField>
            </div>
            <div class="mb-2 flex items-start gap-1" data-testid="explorer-flyql-editor">
                <div class="flex-1 min-w-0">
                    <QueryEditor
                        id="flyql_editor"
                        @change="onQueryChange"
                        :source="source"
                        :value="sourceControlsStore.query"
                        :from="sourceControlsStore.from"
                        :to="sourceControlsStore.to"
                        @submit="handleSearch"
                    />
                </div>
                <Button
                    icon="pi pi-history"
                    severity="secondary"
                    text
                    aria-label="Query history"
                    v-tooltip.bottom="'Recent queries'"
                    aria-haspopup="true"
                    @click="(event) => historyMenu.toggle(event)"
                    data-testid="explorer-query-history-btn"
                />
                <Menu ref="historyMenu" :model="historyItems" :popup="true" data-testid="explorer-query-history">
                    <template #item="{ item, props: itemProps }">
                        <a
                            v-bind="itemProps.action"
                            class="flex items-center gap-2 max-w-[36rem]"
                            :class="{ 'opacity-60': item.disabled }"
                        >
                            <i v-if="item.icon" :class="item.icon" class="text-xs"></i>
                            <span :class="{ 'font-mono text-sm truncate': item.query }" :title="item.query">{{
                                item.label
                            }}</span>
                        </a>
                    </template>
                </Menu>
            </div>
            <div
                v-if="source.isRawQueryAllowed() && showRawQueryEditor"
                class="mb-2"
                data-testid="explorer-raw-query-editor"
            >
                <IftaLabel>
                    <RawQueryEditor
                        id="raw_query_editor"
                        @change="onRawQueryChange"
                        :source="source"
                        :value="sourceControlsStore.rawQuery"
                        @submit="handleSearch"
                    />
                    <label for="raw_query_editor">RAW query (SQL WHERE statement)</label>
                </IftaLabel>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'

import {
    Button,
    Select,
    Toolbar,
    FloatLabel,
    IftaLabel,
    ToggleButton,
    Menu,
    InputText,
    IconField,
    InputIcon,
} from 'primevue'

import DatetimePicker from '@/components/explorer/controls/DatetimePicker.vue'
import GraphSettings from '@/components/explorer/controls/GraphSettings.vue'
import QuerySettings from '@/components/explorer/controls/QuerySettings.vue'
import ContextColumns from '@/components/explorer/controls/ContextColumns.vue'
import ColumnsEditor from '@/components/explorer/controls/ColumnsEditor.vue'
import QueryEditor from '@/components/explorer/controls/QueryEditor.vue'
import RawQueryEditor from '@/components/explorer/controls/RawQueryEditor.vue'
import SavedViews from '@/components/explorer/controls/saved_views/SavedViews.vue'
import AddToDashboard from '@/components/dashboards/AddToDashboard.vue'
import ControlsExtras from '@/components/explorer/controls/ControlsExtras.vue'
import { getLimits } from '@/utils/limits.js'
import { bodyColumn, LIVE_INTERVALS } from '@/utils/explorerPaging.js'

import { useSourceControlsStore } from '@/stores/sourceControls'

const props = defineProps(['source', 'loading', 'groupByInvalid', 'savedView', 'paramsChanged', 'contextColumnsData'])
const emit = defineEmits(['searchRequest', 'searchCancel', 'shareURL', 'download', 'graphVisibilityChanged'])

const sourceControlsStore = useSourceControlsStore()

const hideFilters = ref(false)

const source = ref(props.source)
const showRawQueryEditor = ref(sourceControlsStore.rawQuery ? true : false)
const storedRawQuery = ref('')
const limit = ref(sourceControlsStore.limit)
const limits = ref(getLimits(sourceControlsStore.limit))
const downloadMenu = ref(null)
const downloadItems = [
    { label: 'JSON', icon: 'pi pi-code', command: () => emit('download', 'json') },
    { label: 'CSV (visible columns)', icon: 'pi pi-file', command: () => emit('download', 'csv') },
]
const liveIntervals = LIVE_INTERVALS.map((value) => ({ label: `Every ${value}s`, value }))
const textColumn = computed(() => bodyColumn(props.source))

const onLiveChange = (value) => {
    sourceControlsStore.setLive(value)
}

const onRangeSelect = (params) => {
    sourceControlsStore.setFrom(params.from)
    sourceControlsStore.setTo(params.to)
    sourceControlsStore.setTimeZone(params.timeZone)
}

const onFieldsChange = (value) => {
    sourceControlsStore.setFields(value)
}

const onQueryChange = (value) => {
    sourceControlsStore.setQuery(value)
}

const onEnableRawQueryEditorChange = (value) => {
    showRawQueryEditor.value = value
    if (showRawQueryEditor.value) {
        if (storedRawQuery.value) {
            sourceControlsStore.setRawQuery(storedRawQuery.value)
        }
    } else {
        storedRawQuery.value = sourceControlsStore.rawQuery
        sourceControlsStore.setRawQuery('')
    }
}

const onRawQueryChange = (value) => {
    sourceControlsStore.setRawQuery(value)
}

const onContextFieldChanged = (params) => {
    sourceControlsStore.setContextColumn(params.name, params.value)
}

const onGraphVisibilityChanged = () => {
    emit('graphVisibilityChanged')
}

const onSavedViewChanged = (view) => {
    sourceControlsStore.setView(view)
}

const handleSearch = () => {
    if (props.loading) {
        emit('searchCancel')
    } else {
        rememberQuery(sourceControlsStore.query)
        emit('searchRequest')
    }
}

// The last executed queries of this source, newest first, kept in this browser.
const HISTORY_SIZE = 20
const historyKey = computed(() => `telescope.queryHistory.${props.source.slug}`)
const historyMenu = ref(null)
const readHistory = () => {
    try {
        const value = JSON.parse(localStorage.getItem(historyKey.value) || '[]')
        return Array.isArray(value) ? value : []
    } catch {
        return []
    }
}
const queryHistory = ref(readHistory())
const writeHistory = (value) => {
    queryHistory.value = value
    try {
        localStorage.setItem(historyKey.value, JSON.stringify(value))
    } catch {
        // storage unavailable: history lasts for this page only
    }
}
const rememberQuery = (query) => {
    const text = (query || '').trim()
    if (!text) return
    writeHistory([text, ...queryHistory.value.filter((q) => q !== text)].slice(0, HISTORY_SIZE))
}
const historyItems = computed(() => {
    if (!queryHistory.value.length) return [{ label: 'Queries you run appear here', disabled: true }]
    return [
        ...queryHistory.value.map((query) => ({
            label: query,
            query,
            command: () => {
                sourceControlsStore.setQuery(query)
                handleSearch()
            },
        })),
        { separator: true },
        { label: 'Clear history', icon: 'pi pi-trash', command: () => writeHistory([]) },
    ]
})

const handleShareURL = () => {
    emit('shareURL')
}

// Auto-execute query when source is configured to do so
// Context columns are already loaded before Explorer opens
onMounted(() => {
    if (props.source.executeQueryOnOpen) {
        handleSearch()
    }
})

defineExpose({ onRangeSelect, handleSearch })

watch(
    () => sourceControlsStore.limit,
    (newLimit) => {
        limit.value = newLimit
    },
)
</script>
