<template>
    <div ref="rootRef" class="flex flex-col gap-4 p-4 text-sm" data-testid="row-infra">
        <div class="flex flex-wrap items-center gap-3">
            <span class="text-neutral-500">Around the row time</span>
            <SelectButton
                v-model="range"
                :options="INFRA_RANGES"
                optionLabel="label"
                optionValue="value"
                :allowEmpty="false"
                size="small"
                data-testid="row-infra-range"
            />
        </div>
        <Message v-if="!metricsSlug" severity="info" :closable="false" data-testid="row-infra-no-link">
            Link a metrics source to this source (OTel roles, links) to see pod and node metrics.
        </Message>
        <Error v-else-if="sourceError" :error="sourceError" />
        <template v-else>
            <section v-for="group in groups" :key="group.title" :data-testid="`row-infra-${group.title.toLowerCase()}`">
                <h4 class="font-medium mb-2">
                    {{ group.title }} <span class="font-mono font-normal">{{ group.value }}</span>
                </h4>
                <div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
                    <div
                        v-for="chart in group.charts"
                        :key="chart.key"
                        class="rounded border border-neutral-200 dark:border-neutral-700 p-2 flex flex-col"
                        :data-testid="`row-infra-${chart.key}`"
                    >
                        <div class="flex items-baseline justify-between gap-2 mb-1">
                            <span class="font-medium">{{ chart.title }}</span>
                            <span v-if="results[id(group, chart)]?.data" class="text-xs text-neutral-500">
                                at row time
                                <span class="font-mono font-medium text-color" data-testid="row-infra-value">{{
                                    format(chart, valueAt(results[id(group, chart)].data, row.time.unixtime))
                                }}</span>
                            </span>
                        </div>
                        <Error v-if="results[id(group, chart)]?.error" :error="results[id(group, chart)].error" />
                        <Skeleton v-else-if="!results[id(group, chart)]?.data" height="160px" />
                        <div v-else-if="!hasPoints(results[id(group, chart)].data)" class="text-neutral-500 py-6">
                            No data for {{ chart.metric }}
                        </div>
                        <div v-else class="h-40">
                            <TimeSeriesChart
                                :data="results[id(group, chart)].data"
                                :chart="results[id(group, chart)].chart"
                                :timeZone="timeZone"
                            />
                        </div>
                    </div>
                </div>
            </section>
        </template>
    </div>
</template>

<script>
import { infraAvailable } from '@/components/explorer/results/sections/rowpanel.js'

// Row.vue renders this only when available(source, row) is true.
export function available(source, row) {
    return infraAvailable(source, row)
}
</script>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useElementVisibility } from '@vueuse/core'
import { Message, SelectButton, Skeleton } from 'primevue'

import Error from '@/components/common/Error.vue'
import TimeSeriesChart from '@/components/dashboards/charts/TimeSeriesChart.vue'
import { formatNumber } from '@/components/dashboards/charts/format.js'
import { Source } from '@/sdk/models/source'
import { SourceService } from '@/sdk/services/source'
import { DashboardService } from '@/sdk/services/dashboard'
import {
    DEFAULT_INFRA_RANGE,
    INFRA_RANGES,
    infraChartRequest,
    infraGroups,
    infraWindow,
    valueAt,
} from '@/components/explorer/results/sections/rowpanel.js'

const props = defineProps(['source', 'row', 'timeZone'])

const sources = new SourceService()
const charts = new DashboardService()
const rootRef = ref(null)
const visible = useElementVisibility(rootRef)
const range = ref(DEFAULT_INFRA_RANGE)
const metricsSource = ref(null)
const sourceError = ref(null)
const results = reactive({})

const metricsSlug = computed(() => props.source.otelLink('metrics'))
const groups = computed(() => infraGroups(props.source, props.row))

const id = (group, chart) => `${group.title}:${chart.key}`
const hasPoints = (data) => data.series.some((s) => s.values.some((v) => v !== null))
const format = (chart, value) => (value === null ? '–' : formatNumber(value, chart.unit || 'number'))

let controller = null
const load = async () => {
    controller?.abort()
    controller = new AbortController()
    const signal = controller.signal
    for (const key of Object.keys(results)) delete results[key]
    if (!metricsSource.value) {
        const response = await sources.getSource(metricsSlug.value)
        if (signal.aborted) return
        if (!response.result) {
            sourceError.value = response.errors.join(', ') || 'metrics source not found'
            return
        }
        metricsSource.value = new Source(response.data)
    }
    const window = infraWindow(props.row, range.value, Date.now())
    for (const group of groups.value) {
        for (const chart of group.charts) {
            const params = infraChartRequest(metricsSource.value, group, chart, window)
            const chartDef = { ...params, number_format: { unit: chart.unit || 'number' } }
            charts.getChartData(metricsSlug.value, params, signal).then((r) => {
                if (signal.aborted) return
                results[id(group, chart)] = r.result
                    ? { data: r.data, chart: chartDef }
                    : { error: r.errors.join(', ') || 'chart request failed' }
            })
        }
    }
}

// Fetch only while the tab is shown: hidden tab panels stay mounted.
let loadedFor = null
watch(
    [visible, () => props.row, range],
    () => {
        const key = `${range.value}`
        if (!visible.value || !metricsSlug.value || (loadedFor?.row === props.row && loadedFor.key === key)) return
        loadedFor = { row: props.row, key }
        load()
    },
    { immediate: true },
)
</script>
