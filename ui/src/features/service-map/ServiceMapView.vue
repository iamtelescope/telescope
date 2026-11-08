<template>
    <div class="flex flex-col gap-3 p-4 h-full" data-testid="service-map-view">
        <div class="flex flex-wrap items-center gap-2">
            <h1 class="text-lg font-semibold mr-2 flex items-center gap-2"><Network class="w-5 h-5" />Service map</h1>
            <Select
                :modelValue="slug"
                :options="tracesSources"
                optionLabel="name"
                optionValue="slug"
                placeholder="Traces source"
                size="small"
                class="min-w-48"
                data-testid="service-map-source"
                @update:modelValue="(v) => setQuery({ source: v })"
            />
            <DatetimePicker :from="range.from" :to="range.to" :timeZone="timeZone" @rangeSelect="onRangeSelect" />
            <InputText
                v-model="queryDraft"
                size="small"
                class="flex-1 min-w-64 font-mono"
                placeholder="FlyQL filter on spans, e.g. SpanAttributes.http.route = '/api/cart'"
                data-testid="service-map-query"
                @keydown.enter="setQuery({ query: queryDraft || undefined })"
            />
            <Select
                :modelValue="sampling"
                :options="SAMPLINGS"
                optionLabel="label"
                optionValue="value"
                size="small"
                data-testid="service-map-sampling"
                @update:modelValue="onSampling"
            />
            <Button
                size="small"
                icon="pi pi-refresh"
                label="Run"
                :loading="loading"
                data-testid="service-map-run"
                @click="run"
            />
        </div>
        <div class="flex flex-wrap items-center gap-3 text-sm">
            <SelectButton
                :modelValue="metric"
                :options="METRICS"
                optionLabel="label"
                optionValue="value"
                :allowEmpty="false"
                size="small"
                data-testid="service-map-metric"
                @update:modelValue="(v) => setQuery({ metric: v })"
            />
            <span v-if="data" class="text-surface-500" data-testid="service-map-summary"
                >{{ data.nodes.length }} services, {{ data.edges.length }} edges<template v-if="data.sampling > 1">
                    · counts scaled from 1 in {{ data.sampling }} traces</template
                ></span
            >
        </div>
        <Message v-if="sources && !tracesSources.length" severity="info" :closable="false">
            No OTel traces source. Set the traces roles on a ClickHouse source to see its service map.
        </Message>
        <Error v-if="sourcesError" :error="sourcesError" />
        <Error v-if="error" :error="error" />
        <div v-if="slug" class="flex flex-col lg:flex-row gap-4 min-h-0 flex-1">
            <div
                class="relative flex-1 min-h-[480px] h-[68vh] border border-surface-200 dark:border-surface-700 rounded"
            >
                <ServiceMapGraph
                    v-if="data && data.nodes.length"
                    :data="data"
                    :metric="metric"
                    :rangeSeconds="(data.to - data.from) / 1000"
                    :selected="selected"
                    @select="(s) => (selected = s)"
                />
                <div
                    v-else-if="data"
                    class="absolute inset-0 flex items-center justify-center"
                    data-testid="service-map-empty"
                >
                    <EmptyState
                        :icon="Network"
                        title="No services found in this time range"
                        description="The map links services through Client spans and the Server spans they call."
                    >
                        <Button
                            v-if="range.from !== 'now-24h'"
                            size="small"
                            outlined
                            icon="pi pi-history"
                            label="Show the last 24 hours"
                            data-testid="service-map-widen"
                            @click="setQuery({ from: 'now-24h', to: 'now', timeZone: undefined })"
                        />
                    </EmptyState>
                </div>
                <Skeleton v-if="loading && !data" class="!absolute inset-0" height="100%" />
            </div>
            <ServiceMapPanel
                v-if="selectedItem"
                class="lg:w-[340px] shrink-0"
                :item="selectedItem"
                :data="data"
                :source="source"
                :query="appliedQuery"
                @close="selected = null"
            />
        </div>
    </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, InputText, Message, Select, SelectButton, Skeleton } from 'primevue'
import { Network } from 'lucide-vue-next'

import EmptyState from '@/components/common/EmptyState.vue'
import Error from '@/components/common/Error.vue'
import DatetimePicker from '@/components/explorer/controls/DatetimePicker.vue'
import { useGetSources } from '@/composables/sources/useSourceService'
import { useServiceMap } from '@/features/service-map/service.js'
import { METRICS } from '@/features/service-map/utils.js'
import ServiceMapGraph from '@/features/service-map/ServiceMapGraph.vue'
import ServiceMapPanel from '@/features/service-map/ServiceMapPanel.vue'
import { localTimeZone } from '@/utils/datetimeranges'
import { resolveTime } from '@/utils/explorerPaging'

const SAMPLING_KEY = 'telescope.serviceMap.sampling'
const SAMPLINGS = [1, 2, 5, 10, 20, 50, 100].map((n) => ({
    value: n,
    label: n === 1 ? 'All traces' : `1 in ${n} traces`,
}))

const route = useRoute()
const router = useRouter()
const { sources, error: sourcesError } = useGetSources()
const { data, error, loading, load } = useServiceMap()
const selected = ref(null)

const storedSampling = () => {
    try {
        return Number(localStorage.getItem(SAMPLING_KEY)) || 1
    } catch {
        return 1
    }
}

const tracesSources = computed(() => (sources.value || []).filter((s) => s.otelSignal === 'traces'))
const slug = computed(() => route.query.source || tracesSources.value[0]?.slug || null)
const source = computed(() => tracesSources.value.find((s) => s.slug === slug.value) || null)
const asTime = (v, fallback) => (v === undefined ? fallback : /^\d+$/.test(String(v)) ? parseInt(v) : v)
const range = computed(() => ({ from: asTime(route.query.from, 'now-1h'), to: asTime(route.query.to, 'now') }))
const timeZone = computed(() => route.query.timeZone || localTimeZone)
const appliedQuery = computed(() => route.query.query || '')
const sampling = computed(() => Number(route.query.sampling) || storedSampling())
const metric = computed(() => (METRICS.some((m) => m.value === route.query.metric) ? route.query.metric : 'errorRate'))
const queryDraft = ref(appliedQuery.value)
watch(appliedQuery, (q) => (queryDraft.value = q))

const setQuery = (patch) => router.replace({ query: { ...route.query, ...patch } })
const onRangeSelect = (r) => setQuery({ from: r.from, to: r.to, timeZone: r.timeZone || undefined })
const onSampling = (value) => {
    try {
        localStorage.setItem(SAMPLING_KEY, String(value))
    } catch {
        // Storage may be unavailable; the URL still carries the choice.
    }
    setQuery({ sampling: value })
}

const run = () => {
    if (!slug.value) return
    const now = Date.now()
    load(slug.value, {
        from: resolveTime(range.value.from, now),
        to: resolveTime(range.value.to, now),
        query: appliedQuery.value,
        sampling: sampling.value,
    })
}
watch(
    () => [slug.value, range.value.from, range.value.to, appliedQuery.value, sampling.value],
    () => {
        selected.value = null
        run()
    },
    { immediate: true },
)

const selectedItem = computed(() => {
    const s = selected.value
    if (!s || !data.value) return null
    if (s.kind === 'node') {
        const node = data.value.nodes.find((n) => n.service === s.id)
        return node && { kind: 'node', ...node }
    }
    const edge = data.value.edges.find((e) => `${e.client}->${e.server}` === s.id)
    return edge && { kind: 'edge', ...edge }
})
</script>
