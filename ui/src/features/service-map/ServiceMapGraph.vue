<template>
    <div ref="container" class="service-map relative w-full h-full" :data-testid="testid">
        <VueFlow
            :id="flowId"
            :nodes="flowNodes"
            :edges="flowEdges"
            :nodes-connectable="false"
            :min-zoom="0.2"
            :max-zoom="1.25"
            @node-click="({ node }) => emit('select', { kind: 'node', id: node.id })"
            @edge-click="({ edge }) => emit('select', { kind: 'edge', id: edge.id })"
            @pane-click="emit('select', null)"
            fit-view-on-init
            @pane-ready="onReady"
            @nodes-initialized="fit"
        >
            <template #node-service="{ data }">
                <div
                    class="flex flex-col items-center gap-1 cursor-pointer"
                    :data-testid="`service-map-node-${data.service}`"
                    :data-error-level="data.level"
                >
                    <Handle type="target" :position="Position.Left" class="!invisible" />
                    <div
                        class="rounded-full"
                        :class="
                            data.selected
                                ? 'ring-2 ring-offset-2 ring-primary ring-offset-[var(--p-content-background)]'
                                : ''
                        "
                        :style="{
                            width: data.size + 'px',
                            height: data.size + 'px',
                            background: data.colors.fill,
                            border: `${data.colors.dashed ? '1px dashed' : '1px solid'} ${data.colors.border}`,
                        }"
                    />
                    <Handle type="source" :position="Position.Right" class="!invisible" />
                    <span class="text-xs font-medium whitespace-nowrap">{{ data.service }}</span>
                </div>
            </template>
        </VueFlow>
        <div
            v-if="!compact"
            class="absolute top-2 right-2 rounded border border-surface-200 dark:border-surface-700 bg-[var(--p-content-background)] px-3 py-2 text-xs"
            data-testid="service-map-legend"
        >
            <div class="mb-1">{{ legendLabel }}</div>
            <div class="h-2 w-40 rounded" :style="{ background: legendGradient(metric) }" />
            <div class="flex justify-between mt-1 text-surface-500">
                <template v-if="metric === 'errorRate'"> <span>0</span><span>1%</span><span>5%+</span> </template>
                <template v-else>
                    <span>0</span><span>{{ legendMax }}</span>
                </template>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useResizeObserver } from '@vueuse/core'
import { Handle, MarkerType, Position, VueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'

import {
    ERROR_HIGH,
    METRICS,
    errorLevel,
    formatMs,
    formatPercent,
    formatRate,
    layout,
    legendGradient,
    metricValue,
    nodeColors,
    nodeSize,
} from '@/features/service-map/utils.js'

// `rangeSeconds` turns counts into rates; null (one trace) shows counts.
const props = defineProps({
    data: { type: Object, required: true },
    metric: { type: String, default: 'errorRate' },
    rangeSeconds: { type: Number, default: null },
    selected: { type: Object, default: null },
    flowId: { type: String, default: 'service-map' },
    compact: { type: Boolean, default: false },
    testid: { type: String, default: 'service-map-graph' },
})
const emit = defineEmits(['select'])
const container = ref(null)
let flow = null

const nodes = computed(() => {
    const outgoing = {}
    for (const e of props.data.edges) outgoing[e.client] = (outgoing[e.client] || 0) + e.requests
    return props.data.nodes.map((n) => ({ ...n, outgoing: outgoing[n.service] || 0 }))
})
const max = computed(() =>
    Object.fromEntries(METRICS.map((m) => [m.value, Math.max(0, ...nodes.value.map((n) => metricValue(n, m.value)))])),
)
const volume = (requests) =>
    props.rangeSeconds ? formatRate(requests / props.rangeSeconds) : `${requests} ${requests === 1 ? 'call' : 'calls'}`

const flowNodes = computed(() => {
    const positions = layout(
        nodes.value.map((n) => n.service),
        props.data.edges,
        props.compact ? 170 : 220,
        props.compact ? 90 : 150,
    )
    return nodes.value.map((n) => ({
        id: n.service,
        type: 'service',
        position: positions[n.service],
        data: {
            service: n.service,
            level: n.requests ? errorLevel(n.error_rate) : 'none',
            colors: nodeColors(n, props.metric, max.value[props.metric]),
            size: nodeSize(n.requests + n.outgoing, max.value.throughput) * (props.compact ? 0.7 : 1),
            selected: props.selected?.kind === 'node' && props.selected.id === n.service,
        },
    }))
})

const edgeId = (e) => `${e.client}->${e.server}`
const flowEdges = computed(() => {
    const top = Math.max(1, ...props.data.edges.map((e) => e.requests))
    return props.data.edges.map((e) => {
        const selected = props.selected?.kind === 'edge' && props.selected.id === edgeId(e)
        const color =
            e.error_rate >= ERROR_HIGH ? 'hsl(0 72% 50%)' : selected ? 'var(--p-primary-color)' : 'var(--p-surface-400)'
        return {
            id: edgeId(e),
            source: e.client,
            target: e.server,
            label:
                props.compact || !e.errors
                    ? volume(e.requests)
                    : `${volume(e.requests)} · ${formatPercent(e.error_rate)} err`,
            markerEnd: { type: MarkerType.ArrowClosed, color },
            style: { stroke: color, strokeWidth: (selected ? 1.5 : 1) * (1 + 2.5 * Math.sqrt(e.requests / top)) },
            labelStyle: { fill: 'var(--p-text-color)', fontSize: '11px' },
            labelBgStyle: { fill: 'var(--p-content-background)' },
            class: 'cursor-pointer',
        }
    })
})

const legendLabel = computed(() => {
    if (props.metric === 'latency') return 'p95 latency'
    if (props.metric === 'throughput') return 'Throughput (in + out)'
    return 'Error rate'
})
const legendMax = computed(() => {
    const m = max.value[props.metric]
    return props.metric === 'latency' ? formatMs(m) : volume(m)
})

const fit = () => flow?.fitView({ padding: props.compact ? 0.15 : 0.2 })
const onReady = (instance) => {
    flow = instance
    fit()
}
useResizeObserver(container, () => fit())
watch(
    () => props.data,
    () => nextTick(fit),
)
</script>

<style scoped>
.service-map :deep(.vue-flow__node-service) {
    background: transparent;
    border: none;
    padding: 0;
}
.service-map :deep(.vue-flow__edge-textbg) {
    rx: 3;
}
</style>
