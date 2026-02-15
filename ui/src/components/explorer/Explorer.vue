<template>
    <div class="p-2">
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
        <BorderCard class="mb-2" :loading="graphLoading" v-if="sourceControlsStore.showGraph && !showInitialMessage">
            <Skeleton v-if="graphLoading && graphData === null" width="100%" height="235px"></Skeleton>
            <Error v-if="graphError" :error="graphError"></Error>
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
                :rows="rows"
                :timeZone="displayTimeZone"
                :groupByLabel="sourceControlsStore.graphGroupBy"
            />
        </BorderCard>
        <BorderCard :loading="loading">
            <Skeleton v-if="loading && rows === null" width="100%" height="400px"></Skeleton>
            <Error v-if="error" :error="error"></Error>
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
            />
        </BorderCard>
    </div>
</template>

<script setup>
import { ref, onBeforeMount, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useToast } from 'primevue'
import { Skeleton } from 'primevue'
import { useSourceControlsStore } from '@/stores/sourceControls'
import {
    useGetSourceData,
    useGetSourceGraphData,
    useGetSourceDataAndGraph,
} from '@/composables/sources/useSourceService'

import Controls from '@/components/explorer/controls/Controls.vue'
import BorderCard from '@/components/common/BorderCard.vue'
import Error from '@/components/common/Error.vue'
import ValidationError from '@/components/common/ValidationError.vue'
import ExplorerTable from '@/components/explorer/results/ExplorerTable.vue'
import Histogramm from '@/components/explorer/results/Histogramm.vue'
import LimitMessage from '@/components/explorer/controls/LimitMessage.vue'
import { localTimeZone } from '@/utils/datetimeranges'

const controlsRef = ref(null)

const route = useRoute()
const router = useRouter()
const toast = useToast()
const sourceControlsStore = useSourceControlsStore()

const lastSearchRouteQuery = ref(null)
const displayTimeZone = ref(localTimeZone)
const props = defineProps(['source', 'savedView', 'contextColumnsData'])

// Determine query mode
const useCombinedMode = computed(() => props.source?.queryMode === 'combined')

// Separate mode (ClickHouse)
const {
    rows: separateRows,
    columns: separateColumns,
    message: separateMessage,
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
    lastSearchRouteQuery.value = sourceControlsStore.routeQuery
    displayTimeZone.value = sourceControlsStore.timeZone
    router.push({ path: route.path, query: sourceControlsStore.routeQuery })

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

const onDownload = () => {
    const data = JSON.stringify(rows.value, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'telescope_data.json'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
}

const onHistogrammRangeSelected = (params) => {
    sourceControlsStore.setFrom(params.from)
    sourceControlsStore.setTo(params.to)
    controlsRef.value.handleSearch()
}

onBeforeMount(() => {
    sourceControlsStore.$reset()
    sourceControlsStore.init(props.source, props.savedView)
})
</script>
