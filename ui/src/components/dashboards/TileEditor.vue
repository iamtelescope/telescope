<template>
    <Dialog
        :visible="visible"
        @update:visible="(v) => (v ? emit('update:visible', true) : requestClose())"
        modal
        :closeOnEscape="false"
        :style="{ width: '95vw', maxWidth: '1600px' }"
        :breakpoints="{ '960px': '98vw' }"
        :pt="{ content: { class: 'pb-0' } }"
        data-testid="tile-editor"
    >
        <template #header>
            <div class="flex flex-col">
                <span class="text-xl font-semibold">{{ isNew ? 'New tile' : 'Edit tile' }}</span>
                <span class="text-sm text-surface-500 dark:text-surface-400"> Enter runs the preview, Esc closes </span>
            </div>
        </template>
        <div v-if="form" class="flex flex-col lg:flex-row gap-5 lg:h-[72vh]">
            <div class="flex flex-col gap-4 lg:w-[30rem] shrink-0 lg:overflow-y-auto lg:pr-2 pb-2">
                <div class="flex flex-col gap-1">
                    <label for="tile_title" class="font-medium">Title</label>
                    <InputText
                        id="tile_title"
                        v-model="form.title"
                        size="small"
                        maxlength="128"
                        placeholder="Untitled tile"
                        autofocus
                        @keydown.enter="runPreview"
                    />
                </div>
                <div class="flex flex-col gap-1">
                    <label class="font-medium">Display</label>
                    <div class="grid grid-cols-7 gap-1" role="radiogroup" data-testid="tile-display">
                        <button
                            v-for="d in DISPLAY_BUTTONS"
                            :key="d.value"
                            type="button"
                            role="radio"
                            :aria-checked="chart.display === d.value"
                            :data-display="d.value"
                            class="flex flex-col items-center gap-1 py-2 rounded-md border text-xs transition-colors"
                            :class="
                                chart.display === d.value
                                    ? 'border-primary bg-highlight font-medium'
                                    : 'border-surface-200 dark:border-surface-700 text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800'
                            "
                            @click="setDisplay(d.value)"
                        >
                            <component :is="d.icon" class="w-5 h-5" :stroke-width="1.75" />
                            {{ d.label }}
                        </button>
                    </div>
                </div>

                <div v-if="chart.display === 'text'" class="flex flex-col gap-1">
                    <label for="tile_text" class="font-medium">Text</label>
                    <Textarea
                        id="tile_text"
                        v-model="chart.text"
                        rows="12"
                        maxlength="10000"
                        autoResize
                        placeholder="Notes for this dashboard"
                    />
                </div>
                <template v-else>
                    <div class="flex flex-col gap-1">
                        <label class="font-medium">Source</label>
                        <Select
                            v-model="chart.source"
                            :options="sources"
                            optionLabel="name"
                            optionValue="slug"
                            filter
                            size="small"
                            placeholder="Choose a source"
                            :invalid="!!sourceError"
                            @change="onSourceChange"
                        >
                            <template #option="{ option }">
                                <div class="flex items-center">
                                    <img
                                        :src="require(`@/assets/${option.kind}.png`)"
                                        height="16px"
                                        width="16px"
                                        class="mr-2"
                                    />
                                    {{ option.name }} <span class="ml-2 text-surface-500">{{ option.slug }}</span>
                                </div>
                            </template>
                        </Select>
                        <ErrorText v-if="sourceError" :text="sourceError" class="text-sm" />
                    </div>

                    <template v-if="source">
                        <div class="flex flex-col gap-1">
                            <div class="flex items-center justify-between">
                                <label class="font-medium">Series</label>
                                <Button
                                    icon="pi pi-plus"
                                    label="Add series"
                                    text
                                    size="small"
                                    :disabled="chart.series.length >= maxSeries"
                                    v-tooltip.top="
                                        chart.series.length >= maxSeries ? `At most ${maxSeries} series here` : null
                                    "
                                    @click="addSeries"
                                />
                            </div>
                            <div
                                v-for="(s, idx) in chart.series"
                                :key="idx"
                                class="flex flex-col gap-1"
                                data-testid="tile-series"
                            >
                                <div class="flex items-center gap-1">
                                    <Select
                                        v-model="s.agg"
                                        :options="aggOptions"
                                        optionLabel="label"
                                        optionValue="value"
                                        optionDisabled="disabled"
                                        size="small"
                                        class="w-32 shrink-0"
                                        @change="onAggChange(s)"
                                    />
                                    <Select
                                        v-model="s.column"
                                        :options="columnOptions(s.agg)"
                                        filter
                                        size="small"
                                        class="flex-1 min-w-0"
                                        :placeholder="s.agg === 'count' ? 'all rows' : 'Column'"
                                        :disabled="s.agg === 'count'"
                                        :invalid="!!seriesErrors[idx]"
                                    />
                                    <Select
                                        v-if="s.agg === 'quantile'"
                                        v-model="s.level"
                                        :options="QUANTILE_LEVELS"
                                        size="small"
                                        class="w-24 shrink-0"
                                    />
                                    <Button
                                        icon="pi pi-times"
                                        text
                                        size="small"
                                        severity="secondary"
                                        class="shrink-0"
                                        :disabled="chart.series.length < 2"
                                        aria-label="Remove series"
                                        @click="chart.series.splice(idx, 1)"
                                    />
                                </div>
                                <InputText
                                    v-model="s.alias"
                                    size="small"
                                    :placeholder="`Alias: ${seriesLabel(s)}`"
                                    maxlength="64"
                                    aria-label="Alias"
                                    @keydown.enter="runPreview"
                                />
                                <ErrorText v-if="seriesErrors[idx]" :text="seriesErrors[idx]" class="text-sm" />
                            </div>
                            <ErrorText v-if="serverError('series')" :text="serverError('series')" class="text-sm" />
                        </div>

                        <div v-if="source.contextColumns && countOnly" class="flex flex-col gap-1">
                            <label class="font-medium">Context</label>
                            <ContextColumns
                                :key="source.slug"
                                :source="source"
                                :contextColumns="chart.context_columns"
                                :contextColumnsData="contextColumnsData"
                                @columnChanged="(p) => (chart.context_columns[p.name] = p.value)"
                            />
                        </div>

                        <div class="flex flex-col gap-1">
                            <label class="font-medium">Filter</label>
                            <QueryEditor
                                :key="source.slug"
                                :source="source"
                                :value="chart.query"
                                :from="range.from"
                                :to="range.to"
                                :placeholder="queryExample"
                                @change="(v) => (chart.query = v)"
                                @submit="runPreview"
                            />
                            <ErrorText v-if="serverError('query')" :text="serverError('query')" class="text-sm" />
                        </div>

                        <div class="grid grid-cols-[1fr_auto] gap-3">
                            <div class="flex flex-col gap-1 min-w-0">
                                <label class="font-medium" :class="{ 'opacity-50': !usesGroupBy }">
                                    Group by
                                    <span v-if="chart.display !== 'bar'" class="font-normal text-surface-500"
                                        >(optional)</span
                                    >
                                </label>
                                <Select
                                    v-model="groupBy"
                                    :options="groupByOptions"
                                    optionLabel="name"
                                    editable
                                    :showClear="!!chart.group_by && usesGroupBy"
                                    size="small"
                                    :disabled="!usesGroupBy"
                                    :placeholder="usesGroupBy ? 'None' : 'Not used by Number'"
                                    :invalid="!!groupByError"
                                    @change="onGroupByChange"
                                />
                                <ErrorText v-if="groupByError" :text="groupByError" class="text-sm" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="font-medium" :class="{ 'opacity-50': !usesLimit }">Top groups</label>
                                <InputNumber
                                    v-model="chart.limit"
                                    :min="1"
                                    :max="maxLimit(chart.display)"
                                    size="small"
                                    inputClass="w-16"
                                    showButtons
                                    :disabled="!usesLimit"
                                    :invalid="!!limitError"
                                    v-tooltip.top="`Groups to keep, 1..${maxLimit(chart.display)}`"
                                    @keydown.enter="runPreview"
                                />
                            </div>
                        </div>
                        <ErrorText v-if="limitError" :text="limitError" class="text-sm -mt-3" />

                        <div class="grid grid-cols-3 gap-3">
                            <div class="flex flex-col gap-1">
                                <label class="font-medium" :class="{ 'opacity-50': !timeseries }">Granularity</label>
                                <Select
                                    v-model="chart.granularity"
                                    :options="granularityOptions"
                                    optionLabel="label"
                                    optionValue="value"
                                    size="small"
                                    :disabled="!timeseries"
                                />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="font-medium" :class="{ 'opacity-50': !hasUnit }">Unit</label>
                                <Select
                                    v-model="numberFormat.unit"
                                    :options="NUMBER_UNITS"
                                    size="small"
                                    :disabled="!hasUnit"
                                />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="font-medium" :class="{ 'opacity-50': !hasNumberFormat }">Decimals</label>
                                <InputNumber
                                    v-model="numberFormat.decimals"
                                    :min="0"
                                    :max="6"
                                    size="small"
                                    fluid
                                    showButtons
                                    :disabled="!hasNumberFormat"
                                />
                            </div>
                        </div>

                        <div v-if="source.isRawQueryAllowed()" class="flex flex-col gap-2">
                            <button
                                type="button"
                                class="flex items-center gap-2 text-sm font-medium text-surface-600 dark:text-surface-300 hover:text-primary self-start"
                                data-testid="tile-advanced"
                                @click="advancedOpen = !advancedOpen"
                            >
                                <i
                                    :class="advancedOpen ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"
                                    class="text-xs"
                                />
                                Advanced
                                <Tag v-if="!advancedOpen && chart.raw_query" value="SQL" severity="secondary" />
                            </button>
                            <div v-if="advancedOpen" class="flex flex-col gap-1">
                                <label class="font-medium">Raw SQL condition</label>
                                <span class="text-sm text-surface-500 dark:text-surface-400">
                                    Added to the WHERE clause together with the filter
                                </span>
                                <RawQueryEditor
                                    :key="source.slug"
                                    :source="source"
                                    :value="chart.raw_query"
                                    @change="(v) => (chart.raw_query = v)"
                                    @submit="runPreview"
                                />
                                <ErrorText
                                    v-if="serverError('raw_query')"
                                    :text="serverError('raw_query')"
                                    class="text-sm"
                                />
                            </div>
                        </div>
                    </template>
                </template>
            </div>

            <div class="flex flex-col flex-1 min-w-0 gap-2 pb-2">
                <div class="flex items-center justify-between gap-2 min-h-8">
                    <div class="flex items-center gap-2 min-w-0">
                        <span class="font-medium">Preview</span>
                        <span v-if="chart.display !== 'text'" class="text-sm text-surface-500 truncate">
                            {{ rangeLabel }}
                        </span>
                    </div>
                    <Button
                        v-if="chart.display !== 'text'"
                        label="Run"
                        icon="pi pi-play"
                        size="small"
                        outlined
                        :disabled="!canPreview"
                        :loading="preview.loading.value"
                        data-testid="tile-run"
                        @click="runPreview"
                    />
                </div>
                <div
                    class="flex-1 min-h-[24rem] border rounded-lg border-surface-200 dark:border-surface-700 p-3 bg-surface-0 dark:bg-surface-900"
                    data-testid="tile-editor-preview"
                >
                    <div class="h-full flex flex-col">
                        <div v-if="form.title" class="font-medium mb-2 truncate">{{ form.title }}</div>
                        <div class="flex-1 min-h-0">
                            <ChartView
                                v-if="chart.display === 'text' || (previewChart && !problem)"
                                :chart="chart.display === 'text' ? chart : previewChart"
                                :data="preview.data.value"
                                :loading="preview.loading.value"
                                :error="preview.error.value"
                                :code="preview.code.value"
                                :validation="preview.validation.value"
                                :timeZone="timeZone"
                            />
                            <div
                                v-else
                                class="flex flex-col items-center justify-center h-full gap-2 text-sm text-surface-500"
                            >
                                <i class="pi pi-chart-line text-2xl opacity-60" />
                                {{ problem || 'The preview updates as you edit' }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <template #footer>
            <div class="flex items-center justify-end gap-2 w-full pt-3">
                <Button label="Cancel" severity="secondary" outlined size="small" @click="requestClose" />
                <Button
                    :label="isNew ? 'Add tile' : 'Apply'"
                    size="small"
                    :disabled="!!problem"
                    data-testid="tile-apply"
                    @click="onApply"
                />
            </div>
        </template>
    </Dialog>
    <ConfirmDialog group="tile-editor" />
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { Dialog, Button, ConfirmDialog, InputText, InputNumber, Select, Tag, Textarea, useConfirm } from 'primevue'
import { useDebounceFn } from '@vueuse/core'
import { ChartArea, ChartBarBig, ChartColumnStacked, ChartLine, Hash, Sheet, Type } from 'lucide-vue-next'

import ErrorText from '@/components/common/ErrorText.vue'
import ChartView from '@/components/dashboards/ChartView.vue'
import ContextColumns from '@/components/explorer/controls/ContextColumns.vue'
import QueryEditor from '@/components/explorer/controls/QueryEditor.vue'
import RawQueryEditor from '@/components/explorer/controls/RawQueryEditor.vue'
import { useChartData } from '@/composables/dashboards/useDashboardService'
import { SourceService } from '@/sdk/services/source'
import {
    AGGS,
    DISPLAYS,
    GRANULARITIES,
    MAX_SERIES,
    NUMBER_UNITS,
    QUANTILE_LEVELS,
    countOnlyKind,
    isNumericType,
    isTimeseries,
    maxLimit,
} from '@/utils/dashboards.js'

const props = defineProps(['visible', 'tile', 'sources', 'range', 'timeZone'])
const emit = defineEmits(['update:visible', 'apply'])

const ICONS = {
    line: ChartLine,
    stacked_area: ChartArea,
    stacked_bar: ChartColumnStacked,
    number: Hash,
    table: Sheet,
    bar: ChartBarBig,
    text: Type,
}
const DISPLAY_BUTTONS = DISPLAYS.map((d) => ({ ...d, icon: ICONS[d.value] }))

const sourceSrv = new SourceService()
const preview = useChartData()
const confirm = useConfirm()

const form = ref(null)
const numberFormat = ref({ unit: 'number', decimals: 0 })
const contextColumnsData = ref(null)
const groupBy = ref(null)
const previewChart = ref(null)
const advancedOpen = ref(false)
const confirming = ref(false)
let snapshot = ''

const isNew = computed(() => !props.tile?.id)
const chart = computed(() => form.value.chart)
const source = computed(() => (props.sources || []).find((s) => s.slug === chart.value.source) || null)
const countOnly = computed(() => !!source.value && countOnlyKind(source.value.kind))
const maxSeries = computed(() => (['number', 'bar'].includes(chart.value.display) ? 1 : MAX_SERIES))
const hasNumberFormat = computed(() => ['number', 'table', 'bar'].includes(chart.value.display))
const timeseries = computed(() => isTimeseries(chart.value.display))
const hasUnit = computed(() => hasNumberFormat.value || timeseries.value)
const usesGroupBy = computed(() => chart.value.display !== 'number')
const usesLimit = computed(() => usesGroupBy.value && !!chart.value.group_by)
const granularityOptions = GRANULARITIES.map((g) => ({ value: g, label: g === 'auto' ? 'Auto' : g }))
const rangeLabel = computed(() => (props.range ? `${props.range.from} → ${props.range.to}` : ''))

const defaultChart = () => ({
    source: props.sources?.[0]?.slug || '',
    display: 'line',
    series: [{ agg: 'count' }],
    query: '',
    raw_query: '',
    context_columns: {},
    group_by: '',
    granularity: 'auto',
    limit: 10,
})

const state = () => JSON.stringify([form.value, numberFormat.value])

const init = () => {
    const tile = props.tile ? JSON.parse(JSON.stringify(props.tile)) : {}
    const base = { ...defaultChart(), text: '', ...tile.chart }
    form.value = { title: tile.title || '', chart: base }
    numberFormat.value = { unit: 'number', decimals: 0, ...(tile.chart?.number_format || {}) }
    groupBy.value = base.group_by ? { name: base.group_by } : null
    advancedOpen.value = !!base.raw_query
    preview.abort()
    preview.data.value = null
    preview.validation.value = null
    previewChart.value = null
    snapshot = state()
    loadContextColumns()
}

const onKeydown = (event) => {
    // Editors that consume Esc (open dropdowns, autocomplete) mark it handled.
    if (event.key === 'Escape' && !event.defaultPrevented && !confirming.value) requestClose()
}

watch(
    () => props.visible,
    (visible) => {
        if (visible) {
            init()
            document.addEventListener('keydown', onKeydown)
        } else {
            preview.abort()
            document.removeEventListener('keydown', onKeydown)
        }
    },
    { immediate: true },
)
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

const requestClose = () => {
    if (!form.value || state() === snapshot) return emit('update:visible', false)
    confirming.value = true
    confirm.require({
        group: 'tile-editor',
        header: 'Discard changes?',
        message: 'This tile has unsaved changes.',
        icon: 'pi pi-exclamation-triangle',
        rejectProps: { label: 'Keep editing', severity: 'secondary', outlined: true, size: 'small' },
        acceptProps: { label: 'Discard', severity: 'danger', size: 'small' },
        accept: () => emit('update:visible', false),
        onHide: () => setTimeout(() => (confirming.value = false)),
    })
}

const loadContextColumns = async () => {
    contextColumnsData.value = null
    if (!source.value || !countOnlyKind(source.value.kind)) return
    const slug = source.value.slug
    const response = await sourceSrv.getContextColumnsData(slug)
    if (response.result && source.value?.slug === slug) contextColumnsData.value = response.data
}

const aggOptions = computed(() => AGGS.map((a) => ({ value: a, label: a, disabled: countOnly.value && a !== 'count' })))

const columnOptions = (agg) => {
    const result = []
    for (const [name, col] of Object.entries(source.value?.columns || {})) {
        if (agg === 'uniq' || isNumericType(col.type)) result.push(name)
    }
    return result
}

// A sensible first column: a duration-like numeric one, or a group-by column for uniq.
const defaultColumn = (agg) => {
    const options = columnOptions(agg)
    const columns = source.value?.columns || {}
    if (agg === 'uniq') return options.find((c) => columns[c].group_by) || options[0]
    return options.find((c) => /duration|latency|elapsed|bytes|size/i.test(c)) || options[0]
}

const seriesLabel = (s) => {
    if (s.agg === 'count') return 'count()'
    const column = s.column || '…'
    if (s.agg === 'quantile') return `p${Math.round((s.level ?? 0.95) * 100)}(${column})`
    return `${s.agg}(${column})`
}

// Short FlyQL example built from the source's own columns.
const queryExample = computed(() => {
    const columns = Object.entries(source.value?.columns || {})
    const level = columns.find(([name]) => /^(level|severity|severity_text)$/i.test(name))
    if (level) return `${level[0]} = 'ERROR'`
    const text = columns.find(([, col]) => col.group_by && String(col.type).toLowerCase().includes('string'))
    return text ? `${text[0]} = 'value'` : ''
})

// Same option logic as GraphSettings, driven by the chosen source.
const groupByOptions = computed(() => {
    let result = []
    for (const [key, value] of Object.entries(source.value?.columns || {})) {
        if (value.group_by) {
            result.push({ name: key })
        }
    }
    return result
})

const onGroupByChange = (event) => {
    let value = event.value
    if (typeof value == 'object') {
        if (value === null) {
            value = ''
        } else {
            value = value.name
        }
    }
    chart.value.group_by = value
}

const onAggChange = (s) => {
    if (s.agg === 'count') delete s.column
    else if (!s.column || !columnOptions(s.agg).includes(s.column)) s.column = defaultColumn(s.agg)
    if (s.agg === 'quantile') s.level = s.level ?? 0.95
    else delete s.level
}

const addSeries = () => {
    const s = countOnly.value ? { agg: 'count' } : { agg: 'avg' }
    onAggChange(s)
    chart.value.series.push(s)
}

const onSourceChange = () => {
    chart.value.context_columns = {}
    chart.value.group_by = ''
    groupBy.value = null
    if (countOnly.value) chart.value.series = chart.value.series.map(() => ({ agg: 'count' }))
    chart.value.series.forEach(onAggChange)
    loadContextColumns()
}

const setDisplay = (display) => {
    const c = chart.value
    c.display = display
    if (c.series.length > maxSeries.value) c.series = c.series.slice(0, maxSeries.value)
    if (c.display === 'number') {
        c.group_by = ''
        groupBy.value = null
    }
    if (c.limit > maxLimit(c.display)) c.limit = maxLimit(c.display)
}

// Client-side checks of spec 2.1, shown next to their fields; the server validates the rest.
const sourceError = computed(() => {
    if (!form.value || chart.value.display === 'text') return null
    if (!chart.value.source) return 'Choose a source'
    if (!source.value) return `Source ${chart.value.source} is not available`
    return serverError('source')
})

const seriesErrors = computed(() =>
    (form.value && source.value ? chart.value.series : []).map((s) => {
        if (countOnly.value && s.agg !== 'count') return `${s.agg} is not supported for ${source.value.kind}`
        if (s.agg !== 'count' && !s.column) return `Choose a column for ${s.agg}`
        return null
    }),
)

const groupByError = computed(() => {
    if (!form.value || !usesGroupBy.value) return null
    if (chart.value.display === 'bar' && !chart.value.group_by) return 'Top N needs a group by column'
    return serverError('group_by')
})

const limitError = computed(() => {
    if (!form.value || !usesLimit.value) return null
    const max = maxLimit(chart.value.display)
    const limit = chart.value.limit
    return !limit || limit < 1 || limit > max ? `Top groups must be 1..${max}` : null
})

const problem = computed(() => {
    if (!form.value || chart.value.display === 'text') return null
    if (sourceError.value && !source.value) return sourceError.value
    const series = seriesErrors.value.find(Boolean)
    if (series) return series
    if (chart.value.series.length > maxSeries.value) return `${chart.value.display} takes exactly 1 series`
    if (chart.value.display === 'bar' && !chart.value.group_by) return groupByError.value
    return limitError.value
})

const canPreview = computed(() => !!form.value && chart.value.display !== 'text' && !problem.value)

const cleanChart = () => {
    const c = chart.value
    if (c.display === 'text') return { display: 'text', text: c.text || '' }
    const result = {
        source: c.source,
        display: c.display,
        series: c.series.map((s) => {
            const item = { agg: s.agg }
            if (s.agg !== 'count') item.column = s.column
            if (s.agg === 'quantile') item.level = s.level
            if (s.alias) item.alias = s.alias
            return item
        }),
        query: c.query || '',
        raw_query: c.raw_query || '',
        context_columns: c.context_columns || {},
        group_by: c.display === 'number' ? '' : c.group_by || '',
        granularity: c.granularity || 'auto',
        limit: c.limit,
    }
    if (hasUnit.value) result.number_format = { ...numberFormat.value }
    return result
}

const flatten = (value) => {
    if (!value) return []
    if (typeof value === 'string') return [value]
    if (Array.isArray(value)) return value.flatMap(flatten)
    return Object.entries(value).flatMap(([k, v]) => flatten(v).map((t) => `${k}: ${t}`))
}

const serverError = (name) => flatten(preview.validation.value?.fields?.[name]).join('; ') || null

const runPreview = () => {
    if (!canPreview.value) return
    const c = cleanChart()
    previewChart.value = c
    preview.load(c.source, {
        from: props.range.from,
        to: props.range.to,
        query: c.query,
        dashboard_query: props.range.query || '',
        raw_query: c.raw_query,
        context_columns: c.context_columns,
        display: c.display,
        series: c.series,
        group_by: c.group_by,
        granularity: c.granularity,
        limit: c.limit,
    })
}

// Live preview: rerun shortly after the chart settings change.
const previewKey = computed(() => (props.visible && canPreview.value ? JSON.stringify(cleanChart()) : null))
const debouncedPreview = useDebounceFn(runPreview, 500)
watch(previewKey, (key) => key && debouncedPreview())

const onApply = () => {
    emit('apply', { title: form.value.title, chart: cleanChart() })
    emit('update:visible', false)
}
</script>
