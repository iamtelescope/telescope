<template>
    <div
        class="border border-surface-200 dark:border-surface-700 rounded p-3 text-sm flex flex-col gap-3"
        data-testid="service-map-panel"
    >
        <div class="flex items-start justify-between gap-2">
            <div class="font-semibold break-all" data-testid="service-map-panel-title">
                <template v-if="item.kind === 'node'">{{ item.service }}</template>
                <template v-else>{{ item.client }} → {{ item.server }}</template>
            </div>
            <Button icon="pi pi-times" text rounded size="small" aria-label="Close" @click="emit('close')" />
        </div>
        <div v-if="item.kind === 'node' && !item.requests" class="text-surface-500">
            No server spans: this service only calls others.
        </div>
        <dl v-else class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
            <dt class="text-surface-500">Requests</dt>
            <dd class="font-mono" data-testid="service-map-panel-requests">
                {{ data.sampling > 1 ? '~' : '' }}{{ item.requests.toLocaleString() }}
            </dd>
            <dt v-if="!data.trace_id" class="text-surface-500">Rate</dt>
            <dd v-if="!data.trace_id" class="font-mono">{{ formatRate(item.requests / seconds) }}</dd>
            <dt class="text-surface-500">Errors</dt>
            <dd
                class="font-mono"
                :class="item.error_rate >= ERROR_HIGH ? 'text-red-600 dark:text-red-400 font-semibold' : ''"
                data-testid="service-map-panel-error-rate"
            >
                {{ formatPercent(item.error_rate) }} ({{ item.errors.toLocaleString() }})
            </dd>
            <dt class="text-surface-500">p50 / p95 / p99</dt>
            <dd class="font-mono">{{ formatMs(item.p50) }} / {{ formatMs(item.p95) }} / {{ formatMs(item.p99) }}</dd>
        </dl>
        <div v-if="item.kind === 'node'" class="flex flex-col gap-1">
            <div v-if="callers.length" class="text-surface-500">
                Called by <span class="text-color">{{ callers.join(', ') }}</span>
            </div>
            <div v-if="callees.length" class="text-surface-500">
                Calls <span class="text-color">{{ callees.join(', ') }}</span>
            </div>
        </div>
        <div v-else class="text-surface-500">
            Latency and errors of {{ item.server }}'s server spans called from {{ item.client }}.
        </div>
        <div v-if="source" class="flex flex-wrap gap-2">
            <Button
                as="router-link"
                :to="explore(spansQuery)"
                size="small"
                outlined
                icon="pi pi-search"
                :label="spansLabel"
                data-testid="service-map-drill-traces"
            />
            <Button
                v-if="statusColumn"
                as="router-link"
                :to="explore(errorsQuery)"
                size="small"
                outlined
                severity="danger"
                icon="pi pi-exclamation-triangle"
                label="Errors"
                data-testid="service-map-drill-errors"
            />
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button } from 'primevue'

import { ERROR_HIGH, escapeFlyql, formatMs, formatPercent, formatRate } from '@/features/service-map/utils.js'

const props = defineProps({
    item: { type: Object, required: true },
    data: { type: Object, required: true },
    source: { type: Object, default: null },
    query: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const seconds = computed(() => Math.max(1, (props.data.to - props.data.from) / 1000))
const callers = computed(() => props.data.edges.filter((e) => e.server === props.item.service).map((e) => e.client))
const callees = computed(() => props.data.edges.filter((e) => e.client === props.item.service).map((e) => e.server))

const serviceColumn = computed(() => props.source.otelRole('service'))
const kindColumn = computed(() => props.source.otelRole('span_kind'))
const statusColumn = computed(() => props.source.otelRole('status_code'))

// FlyQL has no parent join, so an edge drills into the server's server spans.
const spansQuery = computed(() => {
    if (props.item.kind === 'node') return `${serviceColumn.value} = '${escapeFlyql(props.item.service)}'`
    return `${serviceColumn.value} = '${escapeFlyql(props.item.server)}' and ${kindColumn.value} in ['Server', 'Consumer']`
})
const spansLabel = computed(() => (props.item.kind === 'node' ? 'Traces' : `${props.item.server} server spans`))
const errorsQuery = computed(() => `${spansQuery.value} and ${statusColumn.value} = 'Error'`)

const explore = (q) => ({
    name: 'explore',
    params: { sourceSlug: props.source.slug },
    query: {
        from: props.data.from,
        to: props.data.to,
        query: props.query ? `(${props.query}) and ${q}` : q,
    },
})
</script>
