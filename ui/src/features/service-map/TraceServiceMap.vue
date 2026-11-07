<template>
    <div
        v-if="data && data.edges.length"
        class="border border-surface-200 dark:border-surface-700 rounded"
        data-testid="trace-service-map"
    >
        <div class="flex items-center justify-between px-3 py-1.5 text-sm">
            <span class="font-medium">Service map</span>
            <router-link
                :to="{ name: 'serviceMap', query: { source: slug, from: data.from - 1800000, to: data.to + 1800000 } }"
                class="text-primary hover:underline"
                data-testid="trace-service-map-open"
                >Open around this trace</router-link
            >
        </div>
        <div class="h-[220px]">
            <ServiceMapGraph :data="data" :flowId="`trace-map-${traceId}`" compact testid="trace-service-map-graph" />
        </div>
    </div>
    <Error v-else-if="error" :error="error" />
</template>

<script setup>
import { watch } from 'vue'

import Error from '@/components/common/Error.vue'
import { useServiceMap } from '@/features/service-map/service.js'
import ServiceMapGraph from '@/features/service-map/ServiceMapGraph.vue'

// The calls between services in one trace; edge labels are span counts.
const props = defineProps({
    slug: { type: String, required: true },
    traceId: { type: String, required: true },
    startMs: { type: Number, required: true },
    durationNs: { type: Number, required: true },
})
const { data, error, load } = useServiceMap()

watch(
    () => [props.traceId, props.startMs],
    () =>
        load(props.slug, {
            trace_id: props.traceId,
            from: props.startMs,
            to: props.startMs + Math.ceil(props.durationNs / 1e6) + 1,
        }),
    { immediate: true },
)
</script>
