<template>
    <div data-testid="deltas-view">
        <div class="flex flex-wrap items-center gap-3 pb-2 text-sm">
            <label class="flex items-center gap-2">
                <span class="text-neutral-500 dark:text-neutral-400">Value</span>
                <Select
                    v-model="column"
                    :options="columns"
                    size="small"
                    filter
                    @change="loadHeatmap"
                    data-testid="deltas-column"
                />
            </label>
            <label class="flex items-center gap-2">
                <span class="text-neutral-500 dark:text-neutral-400">Sample</span>
                <Select
                    v-model="sample"
                    :options="sampleOptions"
                    optionLabel="label"
                    optionValue="value"
                    size="small"
                    @change="loadDeltas"
                    data-testid="deltas-sample"
                />
            </label>
            <span v-if="heatmap" class="text-xs text-neutral-500 dark:text-neutral-400">
                {{ heatmap.total.toLocaleString() }} rows, {{ heatmap.granularity }} buckets
            </span>
            <Button
                v-if="selection"
                label="Clear selection"
                icon="pi pi-times"
                size="small"
                text
                severity="secondary"
                @click="clearSelection"
                data-testid="deltas-clear"
            />
        </div>
        <div v-if="error" class="text-sm text-red-600 dark:text-red-400 py-2" data-testid="deltas-error">
            {{ error }}
        </div>
        <Skeleton v-if="loading && !heatmap" width="100%" height="280px" />
        <div v-if="heatmap && !heatmap.cells.length" class="py-10 text-center text-sm text-neutral-500">
            No rows match the search.
        </div>
        <div v-else-if="heatmap" class="h-[280px]" data-testid="deltas-heatmap">
            <HeatmapChart
                :data="heatmap"
                :unit="unit"
                :timeZone="timeZone"
                :selection="selection"
                selectable
                @select="onSelect"
            />
        </div>

        <div
            v-if="heatmap && heatmap.cells.length && !selection"
            class="py-6 text-center text-sm text-neutral-500 dark:text-neutral-400"
            data-testid="deltas-hint"
        >
            Drag a rectangle over the heatmap, e.g. around slow outliers, to compare those rows with the rest.
        </div>

        <template v-if="selection">
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 pt-3 pb-2 text-sm" data-testid="deltas-summary">
                <span class="flex items-center gap-1.5">
                    <span class="inline-block w-2.5 h-2.5 rounded-sm" :style="{ background: colors.selection }"></span>
                    Selection
                    <span v-if="deltas" class="text-neutral-500 dark:text-neutral-400 tabular-nums">
                        {{ deltas.outlier.total.toLocaleString() }} rows{{ sampleNote(deltas.outlier) }}
                    </span>
                </span>
                <span class="flex items-center gap-1.5">
                    <span class="inline-block w-2.5 h-2.5 rounded-sm" :style="{ background: colors.background }"></span>
                    Background
                    <span v-if="deltas" class="text-neutral-500 dark:text-neutral-400 tabular-nums">
                        {{ deltas.inlier.total.toLocaleString() }} rows{{ sampleNote(deltas.inlier) }}
                    </span>
                </span>
                <span class="text-xs text-neutral-500 dark:text-neutral-400">
                    {{ rangeText }}
                </span>
            </div>
            <Skeleton v-if="deltasLoading" width="100%" height="160px" />
            <div
                v-else-if="deltas && !deltas.outlier.total"
                class="py-6 text-center text-sm text-neutral-500"
                data-testid="deltas-empty"
            >
                No rows in the selection.
            </div>
            <template v-else-if="deltas">
                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    <DeltaProperty
                        v-for="p in visible"
                        :key="p.key"
                        :property="p"
                        :colors="colors"
                        :filterable="!!propertyPath(source, p.key)"
                        @filter="(value, op) => onFilter(p, value, op)"
                    />
                </div>
                <button
                    v-if="hidden.length"
                    type="button"
                    class="flex items-center gap-2 mt-3 text-sm text-neutral-600 dark:text-neutral-300 hover:text-primary"
                    @click="showHidden = !showHidden"
                    data-testid="deltas-hidden-toggle"
                >
                    <i :class="showHidden ? 'pi pi-chevron-down' : 'pi pi-chevron-right'" class="text-xs"></i>
                    Lower-priority fields ({{ hidden.length }}): ids, per-index timestamps and mostly unique values
                </button>
                <div v-if="showHidden" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mt-2">
                    <DeltaProperty
                        v-for="p in hidden"
                        :key="p.key"
                        :property="p"
                        :colors="colors"
                        :filterable="!!propertyPath(source, p.key)"
                        @filter="(value, op) => onFilter(p, value, op)"
                    />
                </div>
            </template>
        </template>
    </div>
</template>

<script>
import { deltasAvailable } from '@/components/explorer/deltas/deltas'

// Explorer offers the Deltas mode only when available(source) is true.
export function available(source) {
    return deltasAvailable(source)
}
</script>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Button, Select, Skeleton } from 'primevue'
import { useDark } from '@vueuse/core'
import { DateTime } from 'luxon'

import HeatmapChart from '@/components/dashboards/charts/HeatmapChart.vue'
import DeltaProperty from '@/components/explorer/deltas/DeltaProperty.vue'
import { durationUnit } from '@/components/dashboards/charts/heatmap.js'
import { formatNumber, seriesUnit } from '@/components/dashboards/charts/format.js'
import { categoricalColor } from '@/components/dashboards/charts/palette.js'
import { facetPath, typedValue } from '@/components/explorer/facets/facets.js'
import {
    buildRequest,
    defaultColumn,
    fetchDeltas,
    fetchHeatmap,
    numericColumns,
    propertyPath,
} from '@/components/explorer/deltas/deltas'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { resolveTime } from '@/utils/explorerPaging'

const props = defineProps(['source', 'searchSeq', 'timeZone'])
const emit = defineEmits(['searchRequest'])

const store = useSourceControlsStore()
const isDark = useDark()
const columns = computed(() => numericColumns(props.source))
const column = ref(defaultColumn(props.source))
const sample = ref(5000)
const sampleOptions = [1000, 5000, 20000].map((value) => ({ label: value.toLocaleString(), value }))
const heatmap = ref(null)
const deltas = ref(null)
const selection = ref(null)
const error = ref(null)
const loading = ref(false)
const deltasLoading = ref(false)
const showHidden = ref(false)
const unit = computed(
    () => durationUnit(props.source, column.value) || seriesUnit({ agg: 'max', column: column.value }),
)
const theme = computed(() => (isDark.value ? 'dark' : 'light'))
const colors = computed(() => ({
    selection: categoricalColor(1, theme.value),
    background: categoricalColor(0, theme.value),
}))
const visible = computed(() => (deltas.value?.properties || []).filter((p) => !p.hidden))
const hidden = computed(() => (deltas.value?.properties || []).filter((p) => p.hidden))
let heatmapController = null
// The heatmap's request with relative times pinned, so deltas read the rows that were drawn.
let request = null
let deltasController = null

const errorText = (response) =>
    response.validation && response.validation.result === false
        ? Object.values(response.validation.fields || {})
              .flat()
              .map((e) => (typeof e === 'string' ? e : JSON.stringify(e)))
              .concat(response.validation.non_field || [])
              .join(', ')
        : response.errors.join(', ')

const loadHeatmap = async () => {
    if (heatmapController) heatmapController.abort()
    if (deltasController) deltasController.abort()
    heatmapController = new AbortController()
    const signal = heatmapController.signal
    selection.value = null
    deltas.value = null
    loading.value = true
    const now = Date.now()
    const params = buildRequest(store, column.value)
    request = { ...params, from: resolveTime(params.from, now), to: resolveTime(params.to, now) }
    const response = await fetchHeatmap(props.source.slug, request, signal)
    if (signal.aborted) return
    loading.value = false
    heatmap.value = response.result ? response.data : null
    error.value = response.result ? null : errorText(response)
}

const loadDeltas = async () => {
    if (!selection.value) return
    if (deltasController) deltasController.abort()
    deltasController = new AbortController()
    const signal = deltasController.signal
    deltasLoading.value = true
    const body = { ...request, outlier: selection.value, sample: sample.value }
    const response = await fetchDeltas(props.source.slug, body, signal)
    if (signal.aborted) return
    deltasLoading.value = false
    deltas.value = response.result ? response.data : null
    error.value = response.result ? null : errorText(response)
}

const onSelect = (sel) => {
    selection.value = sel
    showHidden.value = false
    loadDeltas()
}

const clearSelection = () => {
    if (deltasController) deltasController.abort()
    selection.value = null
    deltas.value = null
    deltasLoading.value = false
}

const sampleNote = (group) => (group.sample < group.total ? `, ${group.sample.toLocaleString()} sampled` : '')

const rangeText = computed(() => {
    const s = selection.value
    const fmt = (ms) => DateTime.fromMillis(ms, { zone: props.timeZone || 'local' }).toFormat('MM-dd HH:mm')
    const value = (v) => formatNumber(v, unit.value, { compact: true })
    const low = s.y_min === null ? '' : `≥ ${value(s.y_min)}`
    const high = s.y_max === null ? '' : `< ${value(s.y_max)}`
    const range = [low, high].filter(Boolean).join(' and ') || 'any value'
    return `${column.value} ${range}, ${fmt(s.t_min)} – ${fmt(s.t_max + 1)}`
})

// Filter or exclude a value; the search runs again and the heatmap reloads.
const onFilter = (property, value, operator) => {
    const path = propertyPath(props.source, property.key)
    store.addQueryExpression(
        facetPath(path.column, path.key),
        operator,
        typedValue(props.source, path.column, path.key, value),
    )
    emit('searchRequest')
}

watch(
    () => props.searchSeq,
    () => loadHeatmap(),
)

onMounted(() => loadHeatmap())
</script>
