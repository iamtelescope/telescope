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
                    v-tooltip.bottom="compact ? null : { value: data.tooltip, class: 'service-map-tooltip' }"
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
            <template #edge-service="edge">
                <BaseEdge :id="edge.id" :path="edgePath(edge)" :marker-end="edge.markerEnd" :style="edge.style" />
                <EdgeLabelRenderer>
                    <div
                        class="service-map-edge-label absolute cursor-pointer rounded-sm px-1 text-[11px] whitespace-nowrap"
                        :style="labelPosition(edge)"
                        :data-id="edge.id"
                        data-testid="service-map-edge-label"
                        @click="emit('select', { kind: 'edge', id: edge.id })"
                    >
                        {{ edge.label }}
                    </div>
                </EdgeLabelRenderer>
            </template>
        </VueFlow>
        <div
            v-if="!compact"
            class="absolute bottom-2 right-2 flex flex-col overflow-hidden rounded border border-surface-200 dark:border-surface-700 bg-[var(--p-content-background)]"
            data-testid="service-map-zoom"
        >
            <Button
                v-for="c in ZOOM"
                :key="c.label"
                :icon="c.icon"
                text
                severity="secondary"
                size="small"
                class="!rounded-none"
                :aria-label="c.label"
                v-tooltip.left="c.label"
                :data-testid="`service-map-${c.id}`"
                @click="c.run"
            />
        </div>
        <div
            v-if="!compact"
            class="absolute top-2 right-2 rounded border border-surface-200 dark:border-surface-700 bg-[var(--p-content-background)] px-3 py-2 text-xs"
            data-testid="service-map-legend"
        >
            <div class="mb-1">{{ legendLabel }}</div>
            <div class="h-2 w-40 rounded" :style="{ background: legendGradient(metric) }" />
            <div class="flex justify-between mt-1 text-surface-500 dark:text-surface-400">
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
import { Button } from 'primevue'
import { BaseEdge, EdgeLabelRenderer, Handle, MarkerType, Position, VueFlow, getBezierPath } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'

import {
    ERROR_HIGH,
    METRICS,
    bezierPoint,
    errorLevel,
    formatMs,
    formatPercent,
    formatRate,
    labelSpots,
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

const positions = computed(() =>
    layout(
        nodes.value.map((n) => n.service),
        props.data.edges,
        props.compact ? 170 : 220,
        props.compact ? 90 : 150,
    ),
)
const sizes = computed(() =>
    Object.fromEntries(
        nodes.value.map((n) => [
            n.service,
            nodeSize(n.requests + n.outgoing, max.value.throughput) * (props.compact ? 0.7 : 1),
        ]),
    ),
)
const flowNodes = computed(() =>
    nodes.value.map((n) => ({
        id: n.service,
        type: 'service',
        position: positions.value[n.service],
        data: {
            service: n.service,
            level: n.requests ? errorLevel(n.error_rate) : 'none',
            colors: nodeColors(n, props.metric, max.value[props.metric]),
            size: sizes.value[n.service],
            selected: props.selected?.kind === 'node' && props.selected.id === n.service,
            tooltip: nodeTooltip(n),
        },
    })),
)

const nodeTooltip = (n) =>
    [
        n.service,
        `${volume(n.requests)} served`,
        n.requests ? `${formatPercent(n.error_rate)} errors` : null,
        n.p95 ? `p95 ${formatMs(n.p95)}` : null,
    ]
        .filter(Boolean)
        .join('\n')

const edgeId = (e) => `${e.client}->${e.server}`
const edgeLabel = (e) =>
    props.compact || !e.errors ? volume(e.requests) : `${volume(e.requests)} · ${formatPercent(e.error_rate)} err`
const flowEdges = computed(() => {
    const top = Math.max(1, ...props.data.edges.map((e) => e.requests))
    const labels = Object.fromEntries(props.data.edges.map((e) => [edgeId(e), edgeLabel(e)]))
    const spots = labelSpots(props.data.edges, positions.value, sizes.value, labels)
    return props.data.edges.map((e) => {
        const selected = props.selected?.kind === 'edge' && props.selected.id === edgeId(e)
        const color =
            e.error_rate >= ERROR_HIGH ? 'hsl(0 72% 50%)' : selected ? 'var(--p-primary-color)' : 'var(--p-surface-400)'
        return {
            id: edgeId(e),
            type: 'service',
            source: e.client,
            target: e.server,
            label: labels[edgeId(e)],
            data: { spot: spots[edgeId(e)] },
            markerEnd: { type: MarkerType.ArrowClosed, color },
            style: { stroke: color, strokeWidth: (selected ? 1.5 : 1) * (1 + 2.5 * Math.sqrt(e.requests / top)) },
            class: 'cursor-pointer',
        }
    })
})
// Labels sit above every edge line, at the spot labelSpots picked along their own curve.
const edgePath = (edge) => getBezierPath(edge)[0]
const labelPosition = (edge) => {
    const p = bezierPoint({ x: edge.sourceX, y: edge.sourceY }, { x: edge.targetX, y: edge.targetY }, edge.data.spot)
    return { transform: `translate(-50%, -50%) translate(${p.x}px, ${p.y}px)` }
}

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
const ZOOM = [
    { id: 'zoom-in', label: 'Zoom in', icon: 'pi pi-plus', run: () => flow?.zoomIn() },
    { id: 'zoom-out', label: 'Zoom out', icon: 'pi pi-minus', run: () => flow?.zoomOut() },
    { id: 'zoom-fit', label: 'Fit to view', icon: 'pi pi-expand', run: () => fit() },
]
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
:global(.service-map-tooltip .p-tooltip-text) {
    white-space: pre-line;
}
.service-map-edge-label {
    pointer-events: all;
    color: var(--p-text-color);
    background: var(--p-content-background);
}
</style>
