<template>
    <div ref="rootRef" class="flex flex-col gap-3 p-4" data-testid="trace-tab">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <span class="font-mono break-all" data-testid="trace-tab-id">{{ traceId }}</span>
            <template v-if="trace && trace.found">
                <span
                    >Duration <span class="font-mono font-medium">{{ formatDuration(trace.duration_ns) }}</span></span
                >
                <span
                    ><span class="font-medium" data-testid="trace-span-count">{{ trace.span_count }}</span> spans</span
                >
                <span :class="trace.error_count ? 'text-red-600 dark:text-red-400' : ''"
                    >{{ trace.error_count }} {{ trace.error_count === 1 ? 'error' : 'errors' }}</span
                >
            </template>
            <router-link
                :to="traceRoute(slug, traceId, aroundMs, spanId)"
                class="ml-auto text-primary hover:underline"
                data-testid="trace-tab-open"
                >Open trace <i class="pi pi-arrow-right text-xs"></i
            ></router-link>
        </div>
        <Error v-if="error" :error="error" />
        <Skeleton v-if="loading && !trace" height="200px" />
        <Message v-if="trace && !trace.found" severity="warn" :closable="false" data-testid="trace-not-found">
            No spans with this trace ID within an hour of this row.
        </Message>
        <TraceWaterfall
            v-if="trace && trace.found"
            :trace="trace"
            :selected="selected"
            :highlightSpanId="spanId"
            maxHeightClass="max-h-[45vh]"
            @select="(i) => (selected = i === selected ? null : i)"
        />
        <div v-if="selectedSpan" class="border border-neutral-200 dark:border-neutral-700 rounded p-3">
            <SpanDetail :span="selectedSpan" :slug="slug" :aroundMs="aroundMs" @close="selected = null" />
        </div>
    </div>
</template>

<script>
// The traces source for a row: the source itself for spans, the linked one for logs.
function tracesSlug(source) {
    if (source?.otelSignal === 'traces') return source.slug
    if (source?.otelSignal === 'logs') return source.otelLink('traces')
    return null
}

// Row.vue renders this only when available(source, row) is true.
export function available(source, row) {
    const column = source?.otelRole?.('trace_id')
    return !!(tracesSlug(source) && column && row?.data?.[column])
}
</script>

<script setup>
import { computed, ref, watch } from 'vue'
import { useElementVisibility } from '@vueuse/core'
import { Message, Skeleton } from 'primevue'

import Error from '@/components/common/Error.vue'
import { useTrace } from '@/features/traces/service.js'
import { formatDuration, traceRoute } from '@/features/traces/trace.js'
import SpanDetail from '@/features/traces/SpanDetail.vue'
import TraceWaterfall from '@/features/traces/TraceWaterfall.vue'

const props = defineProps(['source', 'row', 'timeZone'])

const rootRef = ref(null)
const visible = useElementVisibility(rootRef)
const { data: trace, error, loading, load } = useTrace()
const selected = ref(null)

const slug = computed(() => tracesSlug(props.source))
const traceId = computed(() => String(props.row.data[props.source.otelRole('trace_id')]))
const spanId = computed(() => {
    const column = props.source.otelRole('span_id')
    return column ? String(props.row.data[column] || '') || null : null
})
const aroundMs = computed(() => props.row.time.unixtime)
const selectedSpan = computed(() =>
    trace.value?.spans && selected.value !== null ? trace.value.spans[selected.value] : null,
)

watch(trace, (t) => {
    const index = t?.spans?.findIndex((s) => s.id === spanId.value) ?? -1
    selected.value = index >= 0 ? index : null
})

// Fetch only while the tab is shown: hidden tab panels stay mounted.
let loadedFor = null
watch(
    [visible, () => props.row],
    () => {
        if (!visible.value || loadedFor === props.row) return
        loadedFor = props.row
        load(slug.value, traceId.value, aroundMs.value)
    },
    { immediate: true },
)
</script>
