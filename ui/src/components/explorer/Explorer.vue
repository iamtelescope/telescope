<template>
    <div class="p-2" data-testid="explorer" ref="rootRef">
        <Controls
            ref="controlsRef"
            @searchRequest="onSearchRequest"
            @searchCancel="onSearchCancel"
            @shareURL="onShareURL"
            @download="onDownload"
            :savedView="savedView"
            :source="source"
            :loading="loading"
            :paramsChanged="paramsChanged"
            :contextColumnsData="contextColumnsData"
            @graphVisibilityChanged="onGraphVisibilityChanged"
            :groupByInvalid="!!(graphValidation && !graphValidation.result && graphValidation.columns.group_by)"
        />
        <FlyqlDiagnostics v-if="flyqlDiagnostics.length" :diagnostics="flyqlDiagnostics" />
        <div class="flex flex-row gap-2">
            <FacetSidebar
                :source="source"
                :searchSeq="searchSeq"
                :queryInvalid="flyqlDiagnostics.length > 0"
                @searchRequest="controlsRef.runSearch()"
            />
            <div class="flex-1 min-w-0">
                <BorderCard
                    class="mb-2"
                    :loading="graphLoading"
                    v-if="
                        sourceControlsStore.showGraph &&
                        !showInitialMessage &&
                        !(error && graphError) &&
                        !flyqlDiagnostics.length
                    "
                    data-testid="explorer-graph"
                >
                    <Skeleton v-if="graphLoading && graphData === null" width="100%" height="235px"></Skeleton>
                    <SearchError v-if="graphError" :error="graphError" title="Chart failed" />
                    <ValidationError
                        v-if="graphValidation && !graphValidation.result"
                        :validation="graphValidation"
                        message="Failed to load graph: invalid parameters given"
                    />
                    <Histogramm
                        v-else-if="showHistogramm && graphValidation.result"
                        :stats="graphData"
                        :source="source"
                        @rangeSelected="onHistogrammRangeSelected"
                        :canUndoZoom="zoomHistory.length > 0"
                        @undoZoom="onUndoZoom"
                        :rows="rows"
                        :timeZone="displayTimeZone"
                        :groupByLabel="sourceControlsStore.graphGroupBy"
                    />
                </BorderCard>
                <BorderCard
                    :loading="loading"
                    data-testid="explorer-results"
                    @mouseenter="liveTail.hovering.value = sourceControlsStore.live"
                    @mouseleave="liveTail.hovering.value = false"
                >
                    <div class="flex flex-wrap items-center gap-3 mb-2">
                        <SelectButton
                            v-if="resultsModes.length > 1"
                            v-model="resultsMode"
                            :options="resultsModes"
                            optionLabel="label"
                            optionValue="value"
                            :allowEmpty="false"
                            size="small"
                            data-testid="explorer-results-mode"
                        />
                        <span class="flex-1"></span>
                        <span
                            v-if="sourceControlsStore.live"
                            class="inline-flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-300"
                            role="status"
                            data-testid="explorer-live-badge"
                        >
                            <span class="relative flex w-2.5 h-2.5">
                                <span
                                    v-if="!liveTail.paused.value"
                                    class="absolute inline-flex w-full h-full rounded-full bg-green-500 opacity-75 animate-ping"
                                ></span>
                                <span
                                    class="relative inline-flex w-2.5 h-2.5 rounded-full"
                                    :class="liveTail.paused.value ? 'bg-amber-500' : 'bg-green-500'"
                                ></span>
                            </span>
                            <span class="font-semibold">{{ liveTail.paused.value ? 'Live paused' : 'Live' }}</span>
                            <span>every {{ sourceControlsStore.liveInterval }}s</span>
                            <span v-if="lastUpdate">· updated {{ lastUpdate }}</span>
                        </span>
                        <label
                            v-if="resultsMode === 'rows'"
                            class="inline-flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-300 cursor-pointer"
                        >
                            <ToggleSwitch
                                v-model="wrapLines"
                                class="scale-75"
                                aria-label="Wrap long values"
                                data-testid="explorer-wrap-toggle"
                            />
                            Wrap lines
                        </label>
                    </div>
                    <!-- The query is checked before it is sent: nothing ran, so nothing stale is shown. -->
                    <SearchError
                        v-if="flyqlDiagnostics.length"
                        title="Query not run"
                        :error="flyqlDiagnostics.map((d) => `${d.section}: ${d.message}`)"
                        data-testid="explorer-query-invalid"
                    />
                    <PatternsView
                        v-else-if="resultsMode === 'patterns' && patternsAvailable(source)"
                        :source="source"
                        :searchSeq="searchSeq"
                        :timeZone="displayTimeZone"
                        @searchRequest="onPatternFilter"
                    />
                    <DeltasView
                        v-else-if="resultsMode === 'deltas' && deltasAvailable(source)"
                        :source="source"
                        :searchSeq="searchSeq"
                        :timeZone="displayTimeZone"
                        @searchRequest="controlsRef.runSearch()"
                    />
                    <template v-else>
                        <Skeleton v-if="loading && rows === null" width="100%" height="400px"></Skeleton>
                        <SearchError v-if="error" :error="error" />
                        <ValidationError
                            v-if="validation && !validation.result"
                            :validation="validation"
                            message="Failed to load logs data: invalid parameters given"
                        />
                        <div
                            v-if="showInitialMessage"
                            class="flex flex-col items-center justify-center py-16 text-gray-600 dark:text-gray-400"
                        >
                            <i class="pi pi-database text-6xl mb-4 opacity-30"></i>
                            <h3 class="text-xl font-semibold mb-2">Ready to explore</h3>
                            <p class="text-sm mb-4">This source is configured not to load data automatically.</p>
                            <p class="text-sm">Click the <strong>Execute</strong> button to load data.</p>
                        </div>
                        <LimitMessage
                            v-if="rows && !error && (graphData || message)"
                            :rowsCount="rows.length"
                            :totalCount="graphData?.total"
                            :message="message"
                        ></LimitMessage>
                        <ExplorerTable
                            v-if="showSourceDataTable"
                            :source="source"
                            :rows="rows"
                            :columns="columns"
                            :timeZone="displayTimeZone"
                            :wrap="wrapLines"
                            interactive
                            @columnsChanged="onColumnsChanged"
                            @emptyAction="onEmptyAction"
                            @searchRequest="controlsRef.runSearch()"
                        />
                        <div
                            v-if="showLoadMore"
                            class="flex items-center justify-center gap-3 pt-3 pb-1"
                            data-testid="explorer-load-more"
                        >
                            <Button
                                label="Load more"
                                icon="pi pi-angle-double-down"
                                size="small"
                                severity="secondary"
                                outlined
                                :loading="loadingMore"
                                @click="onLoadMore"
                                data-testid="explorer-load-more-btn"
                            />
                            <span
                                class="text-sm text-neutral-500 dark:text-neutral-400"
                                data-testid="explorer-rows-shown"
                            >
                                {{ rows.length }} rows shown
                            </span>
                        </div>
                    </template>
                </BorderCard>
            </div>
        </div>
        <div
            v-if="sourceControlsStore.live && liveTail.paused.value"
            class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-full border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 shadow-lg pl-4 pr-2 py-1 text-sm"
            :class="{ 'pointer-events-none': !liveTail.scrolled.value }"
            role="status"
            data-testid="explorer-live-paused"
        >
            <i class="pi pi-pause-circle text-amber-600 dark:text-amber-400"></i>
            <span v-if="liveTail.scrolled.value">Live tail paused while scrolled</span>
            <span v-else>Live tail paused while the pointer is over the results</span>
            <Button
                v-if="liveTail.scrolled.value"
                label="Resume"
                icon="pi pi-play"
                size="small"
                rounded
                @click="liveTail.resume"
                data-testid="explorer-live-resume"
            />
        </div>
    </div>
</template>

<script setup>
import { ref, onBeforeMount, onMounted, computed, watch, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useToast } from 'primevue'
import { Skeleton, SelectButton, Button, ToggleSwitch } from 'primevue'
import { useSourceControlsStore } from '@/stores/sourceControls'
import {
    useGetSourceData,
    useGetSourceGraphData,
    useGetSourceDataAndGraph,
} from '@/composables/sources/useSourceService'

import Controls from '@/components/explorer/controls/Controls.vue'
import BorderCard from '@/components/common/BorderCard.vue'
import SearchError from '@/components/explorer/results/SearchError.vue'
import ValidationError from '@/components/common/ValidationError.vue'
import FlyqlDiagnostics from '@/components/common/FlyqlDiagnostics.vue'
import ExplorerTable from '@/components/explorer/results/ExplorerTable.vue'
import Histogramm from '@/components/explorer/results/Histogramm.vue'
import LimitMessage from '@/components/explorer/controls/LimitMessage.vue'
import FacetSidebar from '@/components/explorer/FacetSidebar.vue'
import PatternsView, { available as patternsAvailable } from '@/components/explorer/results/PatternsView.vue'
import DeltasView, { available as deltasAvailable } from '@/components/explorer/results/DeltasView.vue'
import { validateFlyqlInputs } from '@/sdk/flyql-validator'
import { localTimeZone } from '@/utils/datetimeranges'
import { SourceService } from '@/sdk/services/source'
import { useLiveTail } from '@/composables/useLiveTail'
import { resolveTime, mergeLiveRows, toCsv, downloadFile, postDownload, supportsPaging } from '@/utils/explorerPaging'
import { addColumn, hasColumn, removeColumn } from '@/components/explorer/results/columnsText'
import { DateTime } from 'luxon'

const controlsRef = ref(null)

const route = useRoute()
const router = useRouter()
const toast = useToast()
const sourceControlsStore = useSourceControlsStore()

const lastSearchRouteQuery = ref(null)
const displayTimeZone = ref(localTimeZone)
const flyqlDiagnostics = ref([])
const searchSeq = ref(0)
const resultsMode = computed({
    get: () => sourceControlsStore.resultsMode,
    set: (value) => (sourceControlsStore.resultsMode = value),
})
const props = defineProps(['source', 'savedView', 'contextColumnsData'])
const resultsModes = computed(() => [
    { label: 'Rows', value: 'rows' },
    ...(patternsAvailable(props.source) ? [{ label: 'Patterns', value: 'patterns' }] : []),
    ...(deltasAvailable(props.source) ? [{ label: 'Deltas', value: 'deltas' }] : []),
])

// Determine query mode
const useCombinedMode = computed(() => props.source?.queryMode === 'combined')

// Separate mode (ClickHouse, Starrocks)
const {
    rows: separateRows,
    columns: separateColumns,
    message: separateMessage,
    cursor: separateCursor,
    range: separateRange,
    error: separateError,
    loading: separateLoading,
    validation: separateValidation,
    load: separateLoad,
    controller: separateController,
} = useGetSourceData()

const {
    data: separateGraphData,
    error: separateGraphError,
    loading: separateGraphLoading,
    validation: separateGraphValidation,
    load: separateGraphLoad,
    controller: separateGraphController,
} = useGetSourceGraphData()

// Combined mode (Kubernetes, Docker)
const {
    rows: combinedRows,
    columns: combinedColumns,
    message: combinedMessage,
    graphData: combinedGraphData,
    error: combinedError,
    loading: combinedLoading,
    validation: combinedValidation,
    load: combinedLoad,
    controller: combinedController,
} = useGetSourceDataAndGraph()

// Computed properties to abstract away the mode difference
const rows = computed(() => (useCombinedMode.value ? combinedRows.value : separateRows.value))
const columns = computed(() => (useCombinedMode.value ? combinedColumns.value : separateColumns.value))
const message = computed(() => (useCombinedMode.value ? combinedMessage.value : separateMessage.value))
const error = computed(() => (useCombinedMode.value ? combinedError.value : separateError.value))
const loading = computed(() => (useCombinedMode.value ? combinedLoading.value : separateLoading.value))
const validation = computed(() => (useCombinedMode.value ? combinedValidation.value : separateValidation.value))

const graphData = computed(() => (useCombinedMode.value ? combinedGraphData.value : separateGraphData.value))
const graphError = computed(() => (useCombinedMode.value ? null : separateGraphError.value))
const graphLoading = computed(() => (useCombinedMode.value ? combinedLoading.value : separateGraphLoading.value))
const graphValidation = computed(() => (useCombinedMode.value ? { result: true } : separateGraphValidation.value))

const paramsChanged = computed(() => {
    return (
        lastSearchRouteQuery.value &&
        JSON.stringify(lastSearchRouteQuery.value) !== JSON.stringify(sourceControlsStore.routeQuery)
    )
})

const onSearchRequest = () => {
    if (sourceControlsStore.live && sourceControlsStore.to !== 'now') {
        // Live tail follows "now": an absolute range becomes the last 5 minutes.
        if (typeof sourceControlsStore.from !== 'string') sourceControlsStore.setFrom('now-5m')
        sourceControlsStore.setTo('now')
    }
    lastSearchRouteQuery.value = sourceControlsStore.routeQuery
    displayTimeZone.value = sourceControlsStore.timeZone
    router.push({ path: route.path, query: sourceControlsStore.routeQuery })

    const check = validateFlyqlInputs(props.source, {
        query: sourceControlsStore.query,
        columns: sourceControlsStore.columns,
    })
    if (!check.valid) {
        flyqlDiagnostics.value = check.diagnostics
        return
    }
    flyqlDiagnostics.value = []
    searchSeq.value++
    exportParams.value = sourceControlsStore.dataRequestParams
    const now = Date.now()
    searchParams.value = {
        ...sourceControlsStore.dataRequestParams,
        from: resolveTime(sourceControlsStore.from, now),
        to: resolveTime(sourceControlsStore.to, now),
    }
    loadMoreSeq++
    loadingMore.value = false

    if (useCombinedMode.value) {
        // Combined mode: single request with graph params merged
        const combinedParams = {
            ...sourceControlsStore.dataRequestParams,
            group_by: sourceControlsStore.showGraph ? sourceControlsStore.graphRequestParams.group_by : '',
        }
        combinedLoad(props.source.slug, combinedParams)
    } else {
        // Separate mode: two requests
        separateLoad(props.source.slug, sourceControlsStore.dataRequestParams)
        if (sourceControlsStore.showGraph) {
            separateGraphLoad(props.source.slug, sourceControlsStore.graphRequestParams)
        }
    }
}

const onSearchCancel = () => {
    if (useCombinedMode.value) {
        combinedController.value.abort()
    } else {
        separateController.value.abort()
        separateGraphController.value.abort()
    }
}

const onGraphVisibilityChanged = () => {
    if (useCombinedMode.value) {
        // In combined mode, need to refetch with updated group_by
        if (sourceControlsStore.showGraph) {
            const combinedParams = {
                ...sourceControlsStore.dataRequestParams,
                group_by: sourceControlsStore.graphRequestParams.group_by,
            }
            combinedLoad(props.source.slug, combinedParams)
        } else {
            // Hide graph, but keep existing data
            combinedGraphData.value = null
        }
    } else {
        // Separate mode
        if (sourceControlsStore.showGraph) {
            separateGraphLoad(props.source.slug, sourceControlsStore.graphRequestParams)
        } else {
            separateGraphData.value = null
        }
    }
}

const showHistogramm = computed(() => {
    return (
        graphData.value !== null &&
        graphData.value !== undefined &&
        !graphError.value &&
        graphValidation.value &&
        graphValidation.value.result
    )
})

const showSourceDataTable = computed(() => {
    return rows.value !== null && !error.value && validation.value && validation.value.result
})

const showInitialMessage = computed(() => {
    return (
        !props.source.executeQueryOnOpen &&
        rows.value === null &&
        !error.value &&
        !loading.value &&
        (!validation.value || validation.value.result)
    )
})

const onShareURL = () => {
    let url = window.location.origin + route.fullPath

    navigator.clipboard
        .writeText(url)
        .then(() => {
            toast.add({ severity: 'success', summary: 'Success', detail: 'URL copied to clipboard', life: 3000 })
        })
        .catch((err) => {
            toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to copy URL to clipboard', life: 6000 })
        })
}

const onDownload = (format, scope) => {
    if (scope === 'all') {
        // The last search, with a relative range resolved by the server when the request arrives.
        const { limit, ...params } = exportParams.value || sourceControlsStore.dataRequestParams
        postDownload(`ui/v1/sources/${props.source.slug}/export`, { ...params, format }, onDownloadError)
        toast.add({
            severity: 'info',
            summary: 'Download requested',
            detail: 'The file appears in your browser downloads once the first rows arrive.',
            life: 4000,
        })
    } else if (format === 'csv') {
        downloadFile(toCsv(columns.value || [], rows.value || []), 'text/csv;charset=utf-8', 'telescope_data.csv')
    } else {
        downloadFile(JSON.stringify(rows.value, null, 2), 'application/json', 'telescope_data.json')
    }
}

const onDownloadError = (text) => {
    let detail = text.trim().slice(0, 500) || 'The server did not send the file'
    try {
        const data = JSON.parse(text)
        detail = data.errors?.join(', ') || JSON.stringify(data.validation?.columns ?? {})
    } catch (err) {}
    toast.add({ severity: 'error', summary: 'Download failed', detail, life: 8000 })
}

// ---- Load more (keyset paging) and live tail
const srv = new SourceService()
const rootRef = ref(null)
const searchParams = ref(null)
const exportParams = ref(null)
const loadingMore = ref(false)
let loadMoreSeq = 0
let lastLiveGraph = 0

const showLoadMore = computed(
    () =>
        !useCombinedMode.value &&
        supportsPaging(props.source) &&
        !!separateCursor.value &&
        !sourceControlsStore.live &&
        showSourceDataTable.value &&
        rows.value.length > 0,
)

const onLoadMore = async () => {
    const seq = loadMoreSeq
    loadingMore.value = true
    // The first page's range as the server resolved it: the browser clock may be skewed.
    const params = { ...searchParams.value, ...(separateRange.value || {}), before: separateCursor.value }
    const response = await srv.getData(props.source.slug, params)
    if (seq !== loadMoreSeq) return
    loadingMore.value = false
    if (response.result) {
        separateRows.value = separateRows.value.concat(response.data.rows)
        separateCursor.value = response.data.cursor ?? null
    } else {
        const detail = response.errors.join(', ') || JSON.stringify(response.validation?.columns ?? {})
        toast.add({ severity: 'error', summary: 'Failed to load more rows', detail, life: 6000 })
    }
}

const liveTick = async () => {
    const shown = rows.value || []
    if (loading.value || !searchParams.value) return
    const boundary = shown.length ? shown[0].time.unixtime : (separateRange.value?.from ?? searchParams.value.from)
    const params = { ...searchParams.value, from: boundary, to: 'now' }
    const seq = loadMoreSeq
    let response
    if (useCombinedMode.value) {
        response = await srv.getDataAndGraph(props.source.slug, { ...params, group_by: '' })
    } else {
        response = await srv.getData(props.source.slug, params)
    }
    if (seq !== loadMoreSeq || !sourceControlsStore.live || !response.result) return
    const fresh = response.data.rows
    const target = useCombinedMode.value ? combinedRows : separateRows
    if (fresh.length >= searchParams.value.limit) {
        // More new rows than one page: show the newest page, as a fresh search would.
        target.value = fresh
        if (!useCombinedMode.value) separateCursor.value = response.data.cursor ?? null
    } else {
        const merged = mergeLiveRows(shown, fresh, boundary)
        target.value = merged.rows
        if (merged.trimmed && !useCombinedMode.value) separateCursor.value = null
    }
    if (!useCombinedMode.value && sourceControlsStore.showGraph && Date.now() - lastLiveGraph > 10000) {
        lastLiveGraph = Date.now()
        separateGraphLoad(props.source.slug, sourceControlsStore.graphRequestParams)
    }
}

const liveTail = useLiveTail({
    enabled: computed(() => sourceControlsStore.live),
    intervalSeconds: computed(() => sourceControlsStore.liveInterval),
    rootRef,
    tick: liveTick,
})

// Registered after mount so the store's init from the URL does not count as a toggle.
onMounted(() => {
    watch(
        () => sourceControlsStore.live,
        (live) => {
            router.replace({ path: route.path, query: sourceControlsStore.routeQuery })
            if (live) {
                lastLiveGraph = Date.now()
                onSearchRequest()
            }
        },
    )
    watch(
        () => sourceControlsStore.liveInterval,
        () => router.replace({ path: route.path, query: sourceControlsStore.routeQuery }),
    )
    watch([resultsMode, () => sourceControlsStore.deltas], () =>
        router.replace({ path: route.path, query: sourceControlsStore.routeQuery }),
    )
})

const onPatternFilter = () => {
    resultsMode.value = 'rows'
    controlsRef.value.runSearch()
}

// Brush-to-zoom keeps the ranges it replaced, so "Undo zoom" can step back.
const zoomHistory = ref([])
const onHistogrammRangeSelected = (params) => {
    zoomHistory.value = [...zoomHistory.value, { from: sourceControlsStore.from, to: sourceControlsStore.to }]
    sourceControlsStore.setFrom(params.from)
    sourceControlsStore.setTo(params.to)
    controlsRef.value.runSearch()
}
const onUndoZoom = () => {
    const previous = zoomHistory.value[zoomHistory.value.length - 1]
    if (!previous) return
    zoomHistory.value = zoomHistory.value.slice(0, -1)
    sourceControlsStore.setFrom(previous.from)
    sourceControlsStore.setTo(previous.to)
    controlsRef.value.runSearch()
}

// Wrapping long values is a per-browser preference.
const WRAP_KEY = 'telescope.explorer.wrapLines'
const readWrap = () => {
    try {
        return localStorage.getItem(WRAP_KEY) === '1'
    } catch {
        return false
    }
}
const wrapLines = ref(readWrap())
watch(wrapLines, (value) => {
    try {
        localStorage.setItem(WRAP_KEY, value ? '1' : '0')
    } catch {
        // storage unavailable: the choice lasts for this page only
    }
})

const lastUpdate = ref(null)
watch(rows, (value) => {
    if (value) lastUpdate.value = DateTime.now().setZone(displayTimeZone.value).toFormat('HH:mm:ss')
})

// Column edits from the table header and the row panel run the search again.
const onColumnsChanged = (text) => {
    sourceControlsStore.setFields(text)
    controlsRef.value.runSearch()
}
provide('explorerColumns', {
    has: (name) => hasColumn(sourceControlsStore.columns, name),
    toggle: (name) =>
        onColumnsChanged(
            hasColumn(sourceControlsStore.columns, name)
                ? removeColumn(sourceControlsStore.columns, name)
                : addColumn(sourceControlsStore.columns, name),
        ),
})

const RELATIVE = /^now-(\d+)([dhms])$/
const onEmptyAction = (action) => {
    if (action === 'clearQuery') sourceControlsStore.setQuery('')
    else if (action === 'clearText') sourceControlsStore.setText('')
    else if (action === 'widen') {
        const { from, to } = sourceControlsStore
        const match = typeof from === 'string' && to === 'now' ? RELATIVE.exec(from) : null
        if (match) sourceControlsStore.setFrom(`now-${parseInt(match[1]) * 4}${match[2]}`)
        else {
            const now = Date.now()
            const start = resolveTime(from, now)
            const end = resolveTime(to, now)
            const pad = Math.round((end - start) * 1.5)
            sourceControlsStore.setFrom(start - pad)
            sourceControlsStore.setTo(typeof to === 'string' ? to : Math.min(now, end + pad))
        }
    }
    controlsRef.value.runSearch()
}

onBeforeMount(() => {
    sourceControlsStore.$reset()
    sourceControlsStore.init(props.source, props.savedView)
})
</script>
