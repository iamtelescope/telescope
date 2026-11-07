<template>
    <Dialog
        :visible="visible"
        @update:visible="(v) => emit('update:visible', v)"
        modal
        :header="isNew ? 'New tile' : 'Edit tile'"
        :style="{ width: '95vw', maxWidth: '1600px' }"
        :breakpoints="{ '960px': '98vw' }"
        data-testid="tile-editor"
    >
        <div v-if="form" class="flex flex-col lg:flex-row gap-4">
            <div class="flex flex-col gap-3 lg:w-[30rem] shrink-0">
                <div class="flex flex-col gap-1">
                    <label class="font-medium">Title</label>
                    <InputText v-model="form.title" size="small" maxlength="128" />
                </div>
                <div class="flex flex-col gap-1">
                    <label class="font-medium">Display</label>
                    <SelectButton
                        v-model="chart.display"
                        :options="DISPLAYS"
                        optionLabel="label"
                        optionValue="value"
                        :allowEmpty="false"
                        size="small"
                        @change="onDisplayChange"
                    />
                </div>
                <template v-if="chart.display === 'text'">
                    <div class="flex flex-col gap-1">
                        <label class="font-medium">Text</label>
                        <Textarea v-model="chart.text" rows="10" maxlength="10000" autoResize />
                    </div>
                </template>
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
                            :invalid="!!fieldError('source')"
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
                        <ErrorText v-if="!source && chart.source" :text="`source ${chart.source} is not available`" />
                    </div>
                    <template v-if="source">
                        <div class="flex flex-col gap-1">
                            <label class="font-medium">Series</label>
                            <div v-for="(s, idx) in chart.series" :key="idx" class="flex flex-wrap items-center gap-1">
                                <Select
                                    v-model="s.agg"
                                    :options="aggOptions"
                                    optionLabel="label"
                                    optionValue="value"
                                    optionDisabled="disabled"
                                    size="small"
                                    class="w-28"
                                    @change="onAggChange(s)"
                                />
                                <Select
                                    v-if="s.agg !== 'count'"
                                    v-model="s.column"
                                    :options="columnOptions(s.agg)"
                                    filter
                                    size="small"
                                    class="w-40"
                                    placeholder="Column"
                                />
                                <Select
                                    v-if="s.agg === 'quantile'"
                                    v-model="s.level"
                                    :options="QUANTILE_LEVELS"
                                    size="small"
                                    class="w-24"
                                />
                                <InputText
                                    v-model="s.alias"
                                    size="small"
                                    class="w-28"
                                    placeholder="Alias"
                                    maxlength="64"
                                />
                                <Button
                                    v-if="chart.series.length > 1"
                                    icon="pi pi-times"
                                    text
                                    size="small"
                                    severity="secondary"
                                    @click="chart.series.splice(idx, 1)"
                                />
                            </div>
                            <div>
                                <Button
                                    v-if="chart.series.length < maxSeries"
                                    icon="pi pi-plus"
                                    label="Add series"
                                    text
                                    size="small"
                                    @click="chart.series.push({ agg: 'count' })"
                                />
                            </div>
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
                            <label class="font-medium">Query</label>
                            <QueryEditor
                                :key="source.slug"
                                :source="source"
                                :value="chart.query"
                                :from="range.from"
                                :to="range.to"
                                @change="(v) => (chart.query = v)"
                                @submit="runPreview"
                            />
                        </div>
                        <div v-if="source.isRawQueryAllowed()" class="flex flex-col gap-1">
                            <label class="font-medium">RAW query (SQL WHERE statement)</label>
                            <RawQueryEditor
                                :key="source.slug"
                                :source="source"
                                :value="chart.raw_query"
                                @change="(v) => (chart.raw_query = v)"
                                @submit="runPreview"
                            />
                        </div>
                        <div v-if="chart.display !== 'number'" class="flex flex-col gap-1">
                            <label class="font-medium"
                                >Group by{{ chart.display === 'bar' ? '' : ' (optional)' }}</label
                            >
                            <Select
                                v-model="groupBy"
                                :options="groupByOptions"
                                optionLabel="name"
                                editable
                                :showClear="!!chart.group_by"
                                size="small"
                                :invalid="!!groupByProblem"
                                @change="onGroupByChange"
                            />
                            <ErrorText v-if="groupByProblem" :text="groupByProblem" />
                        </div>
                        <div class="flex flex-row gap-3">
                            <div v-if="isTimeseries(chart.display)" class="flex flex-col gap-1">
                                <label class="font-medium">Granularity</label>
                                <Select
                                    v-model="chart.granularity"
                                    :options="granularityOptions"
                                    optionLabel="label"
                                    optionValue="value"
                                    size="small"
                                    class="w-28"
                                />
                            </div>
                            <div v-if="chart.display !== 'number'" class="flex flex-col gap-1">
                                <label class="font-medium">Limit</label>
                                <InputNumber
                                    v-model="chart.limit"
                                    :min="1"
                                    :max="maxLimit(chart.display)"
                                    size="small"
                                    inputClass="w-20"
                                    showButtons
                                />
                            </div>
                        </div>
                        <div v-if="hasNumberFormat" class="flex flex-row gap-3">
                            <div class="flex flex-col gap-1">
                                <label class="font-medium">Unit</label>
                                <Select v-model="numberFormat.unit" :options="NUMBER_UNITS" size="small" class="w-36" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="font-medium">Decimals</label>
                                <InputNumber
                                    v-model="numberFormat.decimals"
                                    :min="0"
                                    :max="6"
                                    size="small"
                                    inputClass="w-16"
                                    showButtons
                                />
                            </div>
                        </div>
                    </template>
                </template>
            </div>
            <div class="flex flex-col flex-1 min-w-0 gap-2">
                <div class="flex items-center justify-between">
                    <span class="font-medium">Preview</span>
                    <Button
                        v-if="chart.display !== 'text'"
                        label="Run"
                        icon="pi pi-caret-right"
                        size="small"
                        :disabled="!canPreview"
                        :loading="preview.loading.value"
                        @click="runPreview"
                    />
                </div>
                <div
                    class="h-[60vh] border rounded-lg border-neutral-300 dark:border-neutral-600 p-2"
                    data-testid="tile-editor-preview"
                >
                    <ChartView
                        v-if="chart.display === 'text' || previewChart"
                        :chart="chart.display === 'text' ? chart : previewChart"
                        :data="preview.data.value"
                        :loading="preview.loading.value"
                        :error="preview.error.value"
                        :code="preview.code.value"
                        :validation="preview.validation.value"
                        :timeZone="timeZone"
                    />
                    <div v-else class="flex items-center justify-center h-full text-sm text-surface-500">
                        Press Run to preview
                    </div>
                </div>
            </div>
        </div>
        <template #footer>
            <Button label="Cancel" severity="secondary" outlined size="small" @click="emit('update:visible', false)" />
            <Button label="Apply" size="small" :disabled="!!problem" v-tooltip.top="problem" @click="onApply" />
        </template>
    </Dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Dialog, Button, InputText, InputNumber, Select, SelectButton, Textarea } from 'primevue'

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

const sourceSrv = new SourceService()
const preview = useChartData()

const form = ref(null)
const numberFormat = ref({ unit: 'number', decimals: 0 })
const contextColumnsData = ref(null)
const groupBy = ref(null)
const previewChart = ref(null)

const isNew = computed(() => !props.tile?.id)
const chart = computed(() => form.value.chart)
const source = computed(() => (props.sources || []).find((s) => s.slug === chart.value.source) || null)
const countOnly = computed(() => !!source.value && countOnlyKind(source.value.kind))
const maxSeries = computed(() => (['number', 'bar'].includes(chart.value.display) ? 1 : MAX_SERIES))
const hasNumberFormat = computed(() => ['number', 'table', 'bar'].includes(chart.value.display))
const granularityOptions = GRANULARITIES.map((g) => ({ value: g, label: g === 'auto' ? 'Auto' : g }))

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

const init = () => {
    const tile = props.tile ? JSON.parse(JSON.stringify(props.tile)) : {}
    const base = { ...defaultChart(), text: '', ...tile.chart }
    form.value = { title: tile.title || '', chart: base }
    numberFormat.value = { unit: 'number', decimals: 0, ...(tile.chart?.number_format || {}) }
    groupBy.value = base.group_by ? { name: base.group_by } : null
    preview.abort()
    preview.data.value = null
    previewChart.value = null
    loadContextColumns()
    if (props.tile?.chart && base.display !== 'text') runPreview()
}

watch(
    () => props.visible,
    (visible) => {
        if (visible) init()
        else preview.abort()
    },
    { immediate: true },
)

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
    else if (s.column && !columnOptions(s.agg).includes(s.column)) delete s.column
    if (s.agg === 'quantile') s.level = s.level ?? 0.95
    else delete s.level
}

const onSourceChange = () => {
    chart.value.context_columns = {}
    chart.value.group_by = ''
    groupBy.value = null
    if (countOnly.value) chart.value.series = chart.value.series.map(() => ({ agg: 'count' }))
    chart.value.series.forEach(onAggChange)
    loadContextColumns()
}

const onDisplayChange = () => {
    const c = chart.value
    if (c.series.length > maxSeries.value) c.series = c.series.slice(0, maxSeries.value)
    if (c.display === 'number') {
        c.group_by = ''
        groupBy.value = null
    }
    if (c.limit > maxLimit(c.display)) c.limit = maxLimit(c.display)
    if (canPreview.value) runPreview()
}

const groupByProblem = computed(() =>
    chart.value.display === 'bar' && !chart.value.group_by ? 'Top N needs a group by column' : null,
)

// Client-side checks of spec 2.1; the server validates the rest.
const problem = computed(() => {
    if (!form.value) return null
    const c = chart.value
    if (c.display === 'text') return null
    if (!source.value) return 'Choose a source'
    for (const s of c.series) {
        if (s.agg !== 'count' && !s.column) return `Choose a column for ${s.agg}`
        if (countOnly.value && s.agg !== 'count')
            return `aggregation ${s.agg} is not supported for ${source.value.kind}`
    }
    if (c.series.length > maxSeries.value) return `${c.display} takes exactly 1 series`
    if (groupByProblem.value) return groupByProblem.value
    if (!c.limit || c.limit < 1 || c.limit > maxLimit(c.display)) return `Limit must be 1..${maxLimit(c.display)}`
    return null
})

const canPreview = computed(() => form.value && chart.value.display !== 'text' && !problem.value)

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
    if (hasNumberFormat.value) result.number_format = { ...numberFormat.value }
    return result
}

const fieldError = (name) => preview.validation.value?.fields?.[name]

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

const onApply = () => {
    emit('apply', { title: form.value.title, chart: cleanChart() })
    emit('update:visible', false)
}
</script>
