<template>
    <div class="flex flex-col gap-4 p-4" data-testid="trace-view">
        <div class="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h1 class="text-lg font-semibold">Trace</h1>
            <span class="font-mono text-sm break-all" data-testid="trace-id"
                >{{ traceId }} <Copy :value="traceId"
            /></span>
            <router-link
                v-if="source"
                :to="{ name: 'explore', params: { sourceSlug: slug } }"
                class="text-sm text-primary hover:underline"
                >{{ source.name }}</router-link
            >
        </div>
        <Error v-if="sourceError" :error="sourceError" />
        <Error v-if="error" :error="error" />
        <Skeleton v-if="loading && !trace" height="320px" />
        <template v-if="trace">
            <Message v-if="!trace.found" severity="warn" :closable="false" data-testid="trace-not-found">
                No spans with this trace ID between {{ formatTime(trace.window[0]) }} and
                {{ formatTime(trace.window[1]) }}.
                <router-link
                    v-if="searchRoute"
                    :to="searchRoute"
                    class="font-medium underline ml-1"
                    data-testid="trace-not-found-search"
                    >Search {{ source.name }} for it over the last 7 days</router-link
                >
            </Message>
            <template v-else>
                <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm" data-testid="trace-summary">
                    <span
                        >Start <span class="font-mono">{{ formatTime(trace.start_ms) }}</span></span
                    >
                    <span
                        >Duration
                        <span class="font-mono font-medium" data-testid="trace-duration">{{
                            formatDuration(trace.duration_ns)
                        }}</span></span
                    >
                    <span
                        ><span class="font-medium" data-testid="trace-span-count">{{ trace.span_count }}</span>
                        spans</span
                    >
                    <span
                        ><span class="font-medium" data-testid="trace-service-count">{{ trace.services.length }}</span>
                        services</span
                    >
                    <button
                        v-if="errorIndexes.length"
                        type="button"
                        class="inline-flex items-center gap-1 text-red-600 dark:text-red-400 hover:underline"
                        title="Select the next error span"
                        data-testid="trace-next-error"
                        @click="nextError"
                    >
                        <i class="pi pi-exclamation-circle text-xs" />
                        <span class="font-medium" data-testid="trace-error-count">{{ trace.error_count }}</span>
                        {{ trace.error_count === 1 ? 'error' : 'errors' }} <i class="pi pi-arrow-down text-xs" />
                    </button>
                    <span v-else
                        ><span class="font-medium" data-testid="trace-error-count">{{ trace.error_count }}</span>
                        {{ trace.error_count === 1 ? 'error' : 'errors' }}</span
                    >
                    <span v-if="trace.truncated" class="text-amber-600" data-testid="trace-truncated"
                        >Truncated to the first {{ trace.span_count }} spans</span
                    >
                </div>
                <div class="flex flex-col xl:flex-row gap-4">
                    <div class="min-w-0 flex-1">
                        <TraceWaterfall
                            :trace="trace"
                            :selected="selected"
                            :highlightSpanId="highlightSpanId"
                            maxHeightClass="max-h-[65vh]"
                            @select="select"
                        />
                    </div>
                    <div
                        v-if="selectedSpan"
                        class="xl:w-[420px] shrink-0 border border-neutral-200 dark:border-neutral-700 rounded p-3 overflow-auto xl:max-h-[75vh]"
                    >
                        <SpanDetail
                            :span="selectedSpan"
                            :color="spanColor(selectedSpan)"
                            :slug="slug"
                            :aroundMs="trace.start_ms"
                            @close="select(null)"
                        />
                    </div>
                </div>
                <TraceServiceMap
                    :slug="slug"
                    :traceId="traceId"
                    :startMs="trace.start_ms"
                    :durationNs="trace.duration_ns"
                />
                <TraceLogs
                    v-if="source && source.otelLink('logs')"
                    :slug="slug"
                    :traceId="traceId"
                    :aroundMs="trace.start_ms"
                    :startNs="trace.start_ns"
                    :selectedSpanId="selectedSpan && !selectedSpan.synthetic ? selectedSpan.id : null"
                    :timeZone="timeZone"
                    @selectSpan="selectById"
                />
            </template>
        </template>
    </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message, Skeleton } from 'primevue'
import { DateTime } from 'luxon'

import Copy from '@/components/common/Copy.vue'
import Error from '@/components/common/Error.vue'
import { useGetSource } from '@/composables/sources/useSourceService'
import { useTrace } from '@/features/traces/service.js'
import { ERROR_COLOR, formatDuration, serviceColors } from '@/features/traces/trace.js'
import SpanDetail from '@/features/traces/SpanDetail.vue'
import TraceServiceMap from '@/features/service-map/TraceServiceMap.vue'
import TraceLogs from '@/features/traces/TraceLogs.vue'
import TraceWaterfall from '@/features/traces/TraceWaterfall.vue'

const route = useRoute()
const router = useRouter()
const slug = route.params.sourceSlug
const traceId = computed(() => route.params.traceId)
const around = computed(() => (route.query.around ? Number(route.query.around) : null))
const timeZone = computed(() => route.query.timeZone || 'UTC')

const { source, error: sourceError } = useGetSource(slug)
const { data: trace, error, loading, load } = useTrace()
const selected = ref(null)

watch([traceId, around], () => load(slug, traceId.value, around.value), { immediate: true })

// The span the page was opened for (e.g. from a log row or a span link) stays marked.
const highlightSpanId = ref(route.query.span || null)
watch(traceId, () => (highlightSpanId.value = route.query.span || null))
const selectedSpan = computed(() =>
    trace.value?.spans && selected.value !== null ? trace.value.spans[selected.value] : null,
)

// Select the span from ?span= once the trace arrives.
watch(trace, (t) => {
    const index = t?.spans?.findIndex((s) => s.id === highlightSpanId.value) ?? -1
    selected.value = index >= 0 ? index : null
})

const select = (index) => {
    selected.value = index === selected.value ? null : index
}
const selectById = (spanId) => {
    const index = trace.value.spans.findIndex((s) => s.id === spanId && !s.synthetic)
    if (index >= 0) selected.value = index
}

const colors = computed(() => serviceColors(trace.value?.services || []))
const errorIndexes = computed(() =>
    (trace.value?.spans || []).filter((s) => s.error && !s.synthetic).map((s) => s.index),
)
const nextError = () => {
    const list = errorIndexes.value
    selected.value = list.find((i) => i > (selected.value ?? -1)) ?? list[0]
}
const searchRoute = computed(() => {
    const column = source.value?.otelRole('trace_id')
    if (!column) return null
    return {
        name: 'explore',
        params: { sourceSlug: slug },
        query: { query: `${column} = '${traceId.value}'`, from: 'now-7d', to: 'now' },
    }
})
const spanColor = (span) => (span.error ? ERROR_COLOR : colors.value[span.service] || '#6b7280')
const formatTime = (ms) => DateTime.fromMillis(ms, { zone: timeZone.value }).toFormat('yyyy-MM-dd HH:mm:ss.SSS')

watch(selected, (index) => {
    const span = index !== null ? trace.value?.spans[index] : null
    const query = { ...route.query, span: span && !span.synthetic ? span.id : undefined }
    if (query.span !== route.query.span) router.replace({ query })
})
</script>
