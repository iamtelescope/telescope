<template>
    <Content>
        <template #header>
            <ListHeader>
                <template #title>
                    <div class="flex items-center">
                        <ChartLine class="mr-3 w-8 h-8" />
                        Charts
                    </div>
                </template>
                <template #actions>
                    <div class="flex flex-wrap items-center gap-2">
                        <DatetimePicker :from="range.from" :to="range.to" :timeZone="timeZone" @rangeSelect="onRange" />
                        <template v-if="config">
                            <Button
                                label="Edit chart"
                                icon="pi pi-pencil"
                                severity="secondary"
                                outlined
                                size="small"
                                data-testid="chart-edit"
                                @click="editorVisible = true"
                            />
                            <AddToDashboard :source="source" :tile="config" />
                            <span
                                v-tooltip.bottom="
                                    canAlert
                                        ? ''
                                        : 'Alerts watch a count, sum, avg, min, max, percentile or uniq series'
                                "
                            >
                                <Button
                                    label="Create alert"
                                    icon="pi pi-bell"
                                    text
                                    size="small"
                                    :disabled="!canAlert"
                                    data-testid="chart-create-alert"
                                    @click="createAlert"
                                />
                            </span>
                        </template>
                    </div>
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <div
                    v-if="config"
                    class="flex flex-col min-h-[32rem] h-[calc(100vh-12rem)] border rounded-lg border-surface-200 dark:border-surface-700 p-3 bg-surface-0 dark:bg-surface-900"
                    data-testid="chart-explorer"
                >
                    <div class="flex items-baseline gap-2 mb-2 min-w-0">
                        <span class="font-medium truncate" data-testid="chart-title">
                            {{ config.title || 'Untitled chart' }}
                        </span>
                        <span v-if="config.description" class="text-sm text-surface-500 truncate">
                            {{ config.description }}
                        </span>
                    </div>
                    <div class="flex-1 min-h-0">
                        <LogTileView
                            v-if="isLogTile(config.chart.display)"
                            :chart="config.chart"
                            :range="range"
                            :timeZone="timeZone"
                        />
                        <ChartView
                            v-else
                            :chart="config.chart"
                            :data="data.data.value"
                            :loading="data.loading.value"
                            :error="data.error.value"
                            :code="data.code.value"
                            :validation="data.validation.value"
                            :timeZone="timeZone"
                            @rangeSelected="onRange"
                        />
                    </div>
                </div>
                <div
                    v-else
                    class="flex flex-col items-center justify-center gap-3 py-24 text-center text-surface-500"
                    data-testid="chart-empty"
                >
                    <ChartLine class="w-10 h-10" />
                    <span>Build a chart from any source; its link keeps the whole chart.</span>
                    <Button label="Build a chart" icon="pi pi-plus" size="small" @click="editorVisible = true" />
                </div>
            </DataView>
            <TileEditor
                v-model:visible="editorVisible"
                :tile="config ? { id: 'chart', ...config } : null"
                :sources="sources || []"
                :range="range"
                :timeZone="timeZone"
                @apply="onApply"
            />
        </template>
    </Content>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button } from 'primevue'
import { ChartLine } from 'lucide-vue-next'

import Content from '@/components/common/Content.vue'
import DataView from '@/components/common/DataView.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import AddToDashboard from '@/components/dashboards/AddToDashboard.vue'
import ChartView from '@/components/dashboards/ChartView.vue'
import LogTileView from '@/components/dashboards/charts/LogTileView.vue'
import TileEditor from '@/components/dashboards/TileEditor.vue'
import DatetimePicker from '@/components/explorer/controls/DatetimePicker.vue'
import { useChartData } from '@/composables/dashboards/useDashboardService'
import { useGetSources } from '@/composables/sources/useSourceService'
import { availableTimeZones } from '@/utils/datetimeranges'
import { isLogTile } from '@/utils/dashboards'
import { alertQuery, alertSeries, parseConfig, serializeConfig } from '@/features/charts/config.js'

// Adapted from HyperDX DBChartPage: one chart, its config in the URL, saved to a dashboard or an alert.
const route = useRoute()
const router = useRouter()
const { sources, loading, error } = useGetSources()
const data = useChartData()
const editorVisible = ref(false)

const toMillisOrString = (value) => (/^\d+$/.test(String(value)) ? parseInt(value) : value)
const config = computed(() => parseConfig(route.query.config))
const range = computed(() => ({
    from: toMillisOrString(route.query.from || 'now-1h'),
    to: toMillisOrString(route.query.to || 'now'),
    query: '',
    params: {},
}))
const timeZone = computed(() => (availableTimeZones.includes(route.query.time_zone) ? route.query.time_zone : 'UTC'))
const source = computed(() => (sources.value || []).find((s) => s.slug === config.value?.chart.source) || null)
const canAlert = computed(() => !!source.value && !!alertSeries(config.value?.chart))

// A new chart opens the editor once the sources load, so it starts on the first source.
watch(sources, (list) => list && !config.value && (editorVisible.value = true), { once: true })

const onApply = (tile) => router.push({ query: { ...route.query, config: serializeConfig(tile) } })
const onRange = (r) => {
    const query = { ...route.query, from: String(r.from), to: String(r.to) }
    if (r.timeZone) query.time_zone = r.timeZone
    router.replace({ query })
}
const createAlert = () => router.push({ name: 'alertNew', query: alertQuery(config.value) })

watch(
    () => JSON.stringify([config.value?.chart, range.value.from, range.value.to]),
    () => {
        const c = config.value?.chart
        if (!c || c.display === 'text' || isLogTile(c.display)) return data.abort()
        data.load(c.source, {
            from: range.value.from,
            to: range.value.to,
            query: c.query || '',
            dashboard_query: '',
            raw_query: c.raw_query || '',
            context_columns: c.context_columns || {},
            display: c.display,
            series: c.series,
            group_by: c.group_by || '',
            granularity: c.granularity || 'auto',
            limit: c.limit ?? 10,
            params: {},
            ...(c.compare ? { compare: true } : {}),
            ...(c.sparkline ? { sparkline: true } : {}),
        })
    },
    { immediate: true },
)
</script>
