<template>
    <Content>
        <template #header>
            <ListHeader>
                <template #title>
                    <div class="flex items-center">
                        <Activity class="mr-3 w-8 h-8" />
                        Metrics
                    </div>
                </template>
                <template #actions>
                    <DatetimePicker :from="state.from" :to="state.to" timeZone="UTC" @rangeSelect="onRange" />
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <div v-if="!metricSources.length" class="p-6 text-surface-500" data-testid="metrics-no-source">
                    No OTel metrics source yet. Create a ClickHouse source on an otel_metrics_* table and its metric
                    tables are detected.
                </div>
                <div v-else class="flex flex-col lg:flex-row gap-5 p-1" data-testid="metrics-explorer">
                    <div class="flex flex-col gap-4 lg:w-96 shrink-0">
                        <div class="flex flex-col gap-1">
                            <label class="font-medium">Source</label>
                            <Select
                                :modelValue="state.source"
                                :options="metricSources"
                                optionLabel="name"
                                optionValue="slug"
                                size="small"
                                data-testid="metrics-source"
                                @update:modelValue="
                                    (v) => set({ source: v, metric: '', type: '', group: '', filter: '' })
                                "
                            />
                        </div>
                        <div class="flex flex-col gap-1">
                            <label class="font-medium">Metric</label>
                            <div class="flex items-center gap-1">
                                <MetricNamePicker
                                    :source="state.source"
                                    :range="range"
                                    :modelValue="metric"
                                    class="flex-1 min-w-0"
                                    @update:modelValue="onMetric"
                                />
                                <Select
                                    v-if="metric"
                                    :modelValue="metric.agg"
                                    :options="aggOptions"
                                    optionLabel="label"
                                    optionValue="value"
                                    size="small"
                                    class="w-28 shrink-0"
                                    data-testid="metric-agg"
                                    @update:modelValue="(v) => set({ agg: v })"
                                />
                            </div>
                        </div>
                        <div class="flex flex-col gap-1">
                            <label class="font-medium">Filter</label>
                            <InputText
                                v-model="filterInput"
                                size="small"
                                class="font-mono"
                                placeholder="FlyQL, e.g. ServiceName = 'frontend'"
                                data-testid="metrics-filter"
                                @keydown.enter="set({ filter: filterInput })"
                                @blur="set({ filter: filterInput })"
                            />
                        </div>
                        <div class="flex flex-col gap-1">
                            <label class="font-medium">Group by</label>
                            <div class="flex items-center gap-2">
                                <span
                                    class="flex-1 min-w-0 truncate font-mono text-sm"
                                    :class="state.group ? '' : 'text-surface-500'"
                                    data-testid="metrics-group"
                                    >{{ state.group || 'None' }}</span
                                >
                                <Button
                                    v-if="state.group"
                                    icon="pi pi-times"
                                    text
                                    size="small"
                                    severity="secondary"
                                    aria-label="Clear group by"
                                    @click="set({ group: '' })"
                                />
                            </div>
                        </div>
                        <div v-if="metric" class="flex flex-col gap-1">
                            <label class="font-medium">Attributes</label>
                            <AttributePicker
                                :source="state.source"
                                :range="range"
                                :metric="metric"
                                @group="(path) => set({ group: path })"
                                @filter="addFilter"
                            />
                        </div>
                    </div>
                    <div
                        class="flex-1 min-w-0 min-h-[28rem] border rounded-lg border-surface-200 dark:border-surface-700 p-3 bg-surface-0 dark:bg-surface-900 flex flex-col"
                        data-testid="metrics-chart"
                    >
                        <div class="font-medium mb-2 truncate font-mono text-sm">
                            {{ metric ? metricLabel(metric) : '' }}
                            <span v-if="state.group" class="text-surface-500"> by {{ state.group }}</span>
                        </div>
                        <div class="flex-1 min-h-0">
                            <ChartView
                                v-if="chart"
                                :chart="chart"
                                :data="data.data.value"
                                :loading="data.loading.value"
                                :error="data.error.value"
                                :code="data.code.value"
                                :validation="data.validation.value"
                                timeZone="UTC"
                                @rangeSelected="onRange"
                            />
                            <div v-else class="flex items-center justify-center h-full text-sm text-surface-500">
                                Choose a metric to chart it
                            </div>
                        </div>
                    </div>
                </div>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, InputText, Select } from 'primevue'
import { Activity } from 'lucide-vue-next'

import Content from '@/components/common/Content.vue'
import DataView from '@/components/common/DataView.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import ChartView from '@/components/dashboards/ChartView.vue'
import AttributePicker from '@/components/dashboards/metrics/AttributePicker.vue'
import MetricNamePicker from '@/components/dashboards/metrics/MetricNamePicker.vue'
import {
    METRIC_AGGS,
    METRIC_AGG_LABELS,
    defaultMetricAgg,
    isMetricsSource,
    metricLabel,
} from '@/components/dashboards/metrics/metrics'
import DatetimePicker from '@/components/explorer/controls/DatetimePicker.vue'
import { useChartData } from '@/composables/dashboards/useDashboardService'
import { useGetSources } from '@/composables/sources/useSourceService'

// Ported in spirit from HyperDX components/MetricExplorer: one metric, its attributes and a chart.
const route = useRoute()
const router = useRouter()
const { sources, loading, error } = useGetSources()
const data = useChartData()

const toMillisOrString = (value) => (/^\d+$/.test(String(value)) ? parseInt(value) : value)
const metricSources = computed(() => (sources.value || []).filter(isMetricsSource))
const state = computed(() => {
    const q = route.query
    return {
        source: q.source || metricSources.value[0]?.slug || '',
        metric: q.metric || '',
        type: q.type || '',
        agg: q.agg || '',
        filter: q.filter || '',
        group: q.group || '',
        from: toMillisOrString(q.from || 'now-1h'),
        to: toMillisOrString(q.to || 'now'),
    }
})
const range = computed(() => ({ from: state.value.from, to: state.value.to }))
const metric = computed(() => {
    const { metric: name, type, agg } = state.value
    if (!name || !METRIC_AGGS[type]) return null
    return { name, type, agg: METRIC_AGGS[type].includes(agg) ? agg : defaultMetricAgg(type) }
})
const aggOptions = computed(() =>
    (METRIC_AGGS[metric.value?.type] || []).map((a) => ({ value: a, label: METRIC_AGG_LABELS[a] || a })),
)
const filterInput = ref(state.value.filter)
watch(
    () => state.value.filter,
    (v) => (filterInput.value = v),
)

const set = (changes) => {
    const query = { ...route.query, ...changes }
    for (const key of Object.keys(query)) if (query[key] === '' || query[key] == null) delete query[key]
    router.replace({ query })
}
const onMetric = (m) => set({ metric: m.name, type: m.type, agg: defaultMetricAgg(m.type), group: '' })
const onRange = (r) => set({ from: String(r.from), to: String(r.to) })
const addFilter = (condition) => {
    const filter = state.value.filter ? `${state.value.filter} and ${condition}` : condition
    set({ filter })
}

const chart = computed(() => {
    if (!metric.value || !state.value.source) return null
    return {
        source: state.value.source,
        display: 'line',
        series: [{ agg: 'metric', metric: metric.value }],
        group_by: state.value.group,
    }
})

watch(
    () => JSON.stringify([chart.value, state.value.filter, range.value]),
    () => {
        if (!chart.value) return
        data.load(chart.value.source, {
            from: range.value.from,
            to: range.value.to,
            query: state.value.filter,
            raw_query: '',
            context_columns: {},
            display: 'line',
            series: chart.value.series,
            group_by: chart.value.group_by,
            granularity: 'auto',
            limit: 10,
        })
    },
    { immediate: true },
)
</script>
