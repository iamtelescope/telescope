<template>
    <div class="flex flex-col gap-2 text-sm" data-testid="trace-waterfall">
        <div class="flex flex-wrap items-center gap-2">
            <Button
                label="Expand all"
                icon="pi pi-angle-double-down"
                size="small"
                severity="secondary"
                text
                @click="collapsed = new Set()"
                data-testid="trace-expand-all"
            />
            <Button
                label="Collapse all"
                icon="pi pi-angle-double-up"
                size="small"
                severity="secondary"
                text
                @click="collapsed = new Set(collapsibleIndexes(trace.spans))"
                data-testid="trace-collapse-all"
            />
            <Button
                v-if="zoomed"
                label="Reset zoom"
                icon="pi pi-search-minus"
                size="small"
                severity="secondary"
                text
                @click="resetZoom"
                data-testid="trace-reset-zoom"
            />
            <div class="flex flex-wrap items-center gap-3 ml-auto" data-testid="trace-legend">
                <span v-for="service in trace.services" :key="service" class="inline-flex items-center gap-1.5">
                    <span class="w-2.5 h-2.5 rounded-sm" :style="{ backgroundColor: colors[service] }"></span>
                    <span class="text-neutral-700 dark:text-neutral-300">{{ service }}</span>
                </span>
                <span class="inline-flex items-center gap-1.5">
                    <span class="w-2.5 h-2.5 rounded-sm" :style="{ backgroundColor: ERROR_COLOR }"></span>
                    <span class="text-neutral-700 dark:text-neutral-300">error</span>
                </span>
                <span class="inline-flex items-center gap-1.5">
                    <span class="w-4 h-1 rounded-sm bg-neutral-900 dark:bg-white opacity-70"></span>
                    <span class="text-neutral-700 dark:text-neutral-300">critical path</span>
                </span>
            </div>
        </div>

        <svg
            ref="minimapRef"
            class="w-full h-16 rounded border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900 cursor-crosshair select-none touch-none"
            :viewBox="`0 0 1000 ${MINIMAP_HEIGHT}`"
            preserveAspectRatio="none"
            data-testid="trace-minimap"
            @pointerdown="onMinimapDown"
            @pointermove="onMinimapMove"
            @pointerup="onMinimapUp"
        >
            <rect
                v-for="span in trace.spans"
                :key="span.index"
                :x="(span.offset_ns / total) * 1000"
                :y="span.index * rowHeight"
                :width="Math.max((span.duration_ns / total) * 1000, 1)"
                :height="Math.max(rowHeight, 0.5)"
                :fill="barColor(span)"
            />
            <rect
                v-if="zoomed"
                x="0"
                y="0"
                :width="(view.from / total) * 1000"
                :height="MINIMAP_HEIGHT"
                class="minimap-dim"
            />
            <rect
                v-if="zoomed"
                :x="(view.to / total) * 1000"
                y="0"
                :width="1000 - (view.to / total) * 1000"
                :height="MINIMAP_HEIGHT"
                class="minimap-dim"
            />
            <rect
                v-if="drag"
                :x="Math.min(drag.a, drag.b) * 1000"
                y="0"
                :width="Math.abs(drag.b - drag.a) * 1000"
                :height="MINIMAP_HEIGHT"
                class="fill-amber-400/30 stroke-amber-500"
                stroke-width="1"
                vector-effect="non-scaling-stroke"
            />
        </svg>

        <div class="flex border-b border-neutral-200 dark:border-neutral-700 text-xs text-neutral-500">
            <div class="label-col px-2 py-1 font-medium">Service · span</div>
            <div class="relative flex-1 h-6">
                <span
                    v-for="(tick, i) in axis"
                    :key="i"
                    class="absolute top-1 font-mono whitespace-nowrap"
                    :style="tickStyle(i)"
                    >{{ formatDuration(Math.round(tick)) }}</span
                >
            </div>
        </div>

        <div class="overflow-auto" :class="maxHeightClass" data-testid="trace-rows">
            <div
                v-for="span in rows"
                :key="span.index"
                class="flex h-7 cursor-pointer border-b border-neutral-100 dark:border-neutral-800"
                :class="rowClass(span)"
                :data-testid="`span-row-${span.index}`"
                :data-span-id="span.id"
                :data-depth="span.depth"
                :data-error="span.error ? 'true' : undefined"
                :data-synthetic="span.synthetic ? 'true' : undefined"
                :data-selected="span.index === selected ? 'true' : undefined"
                @click="emit('select', span.index)"
            >
                <div
                    class="label-col flex items-center gap-1 min-w-0 pr-2"
                    :style="{ paddingLeft: `${span.depth * 14 + 4}px` }"
                >
                    <button
                        v-if="span.children"
                        type="button"
                        class="w-4 shrink-0 text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100"
                        :aria-label="collapsed.has(span.index) ? 'Expand' : 'Collapse'"
                        :data-testid="`span-toggle-${span.index}`"
                        @click.stop="toggle(span.index)"
                    >
                        <i
                            :class="collapsed.has(span.index) ? 'pi pi-angle-right' : 'pi pi-angle-down'"
                            class="text-xs"
                        ></i>
                    </button>
                    <span v-else class="w-4 shrink-0"></span>
                    <span class="w-1 h-4 rounded-sm shrink-0" :style="{ backgroundColor: barColor(span) }"></span>
                    <template v-if="span.synthetic">
                        <span class="italic text-neutral-500 truncate" :title="`span ${span.id} was not found`"
                            >missing span {{ span.id }}</span
                        >
                    </template>
                    <template v-else>
                        <span class="font-medium shrink-0 text-neutral-800 dark:text-neutral-200">{{
                            span.service
                        }}</span>
                        <span class="truncate text-neutral-600 dark:text-neutral-400" :title="span.name">{{
                            span.name
                        }}</span>
                    </template>
                    <i
                        v-if="span.error"
                        class="pi pi-exclamation-circle text-red-500 text-xs shrink-0"
                        title="error"
                    ></i>
                    <span
                        v-if="collapsed.has(span.index)"
                        class="ml-auto shrink-0 text-xs text-neutral-500"
                        :title="`${span.children} children hidden`"
                        >+{{ span.children }}</span
                    >
                </div>
                <div class="relative flex-1 overflow-hidden">
                    <div
                        class="absolute top-1.5 h-4 rounded-sm"
                        :class="span.synthetic ? 'border border-dashed border-neutral-400 bg-transparent' : ''"
                        :style="barStyle(span)"
                        :title="`${span.name || 'missing span'}: ${formatDuration(span.duration_ns)}`"
                        data-testid="span-bar"
                    ></div>
                    <div
                        v-for="(seg, i) in span.critical"
                        :key="`c${i}`"
                        class="absolute bottom-0.5 h-1 rounded-sm bg-neutral-900 dark:bg-white opacity-70"
                        :style="segmentStyle(seg)"
                        data-testid="critical-segment"
                    ></div>
                    <span
                        v-for="(event, i) in span.events"
                        :key="`e${i}`"
                        class="absolute top-2.5 w-1.5 h-1.5 rounded-full ring-1 ring-white dark:ring-neutral-900"
                        :class="isException(event) ? 'bg-red-600' : 'bg-neutral-800 dark:bg-neutral-100'"
                        :style="{ left: `calc(${pct(event.offset_ns)}% - 3px)` }"
                        :title="event.name"
                    ></span>
                    <span
                        class="absolute top-1.5 text-xs font-mono whitespace-nowrap text-neutral-600 dark:text-neutral-400"
                        :style="labelStyle(span)"
                        >{{ formatDuration(span.duration_ns) }}</span
                    >
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button } from 'primevue'

import {
    ERROR_COLOR,
    collapsibleIndexes,
    formatDuration,
    isException,
    serviceColors,
    ticks,
    visibleSpans,
} from '@/features/traces/trace.js'

const props = defineProps({
    trace: { type: Object, required: true },
    selected: { type: Number, default: null },
    highlightSpanId: { type: String, default: null },
    maxHeightClass: { type: String, default: 'max-h-[60vh]' },
})
const emit = defineEmits(['select'])

const MINIMAP_HEIGHT = 64
const collapsed = ref(new Set())
const view = ref({ from: 0, to: 0 })
const drag = ref(null)
const minimapRef = ref(null)

const total = computed(() => Math.max(props.trace.duration_ns, 1))
const colors = computed(() => serviceColors(props.trace.services))
const rows = computed(() => visibleSpans(props.trace.spans, collapsed.value))
const rowHeight = computed(() => MINIMAP_HEIGHT / Math.max(props.trace.spans.length, 1))
const zoomed = computed(() => view.value.from > 0 || view.value.to < total.value)
const axis = computed(() => ticks(view.value.from, view.value.to))

const resetZoom = () => {
    view.value = { from: 0, to: total.value }
}
watch(
    () => props.trace,
    () => {
        collapsed.value = new Set()
        resetZoom()
    },
    { immediate: true },
)

const toggle = (index) => {
    const next = new Set(collapsed.value)
    next.has(index) ? next.delete(index) : next.add(index)
    collapsed.value = next
}

const barColor = (span) =>
    span.synthetic ? '#a3a3a3' : span.error ? ERROR_COLOR : colors.value[span.service] || '#6b7280'
const pct = (ns) => ((ns - view.value.from) / (view.value.to - view.value.from)) * 100
const width = (ns) => (ns / (view.value.to - view.value.from)) * 100

const barStyle = (span) => ({
    left: `${pct(span.offset_ns)}%`,
    width: `max(${width(span.duration_ns)}%, 2px)`,
    backgroundColor: span.synthetic ? undefined : barColor(span),
})
const segmentStyle = ([from, to]) => ({ left: `${pct(from)}%`, width: `max(${width(to - from)}%, 1px)` })
// After the bar, else before it, else inside it when the bar fills the view.
const labelStyle = (span) => {
    const start = pct(span.offset_ns)
    const end = pct(span.offset_ns + span.duration_ns)
    if (end <= 85) return { left: `calc(${Math.max(end, 0)}% + 4px)` }
    if (start >= 15) return { right: `calc(${100 - start}% + 4px)` }
    return { left: `calc(${Math.max(start, 0)}% + 4px)`, color: 'white' }
}
const tickStyle = (i) =>
    i === axis.value.length - 1 ? { right: '4px' } : { left: `calc(${(i * 100) / (axis.value.length - 1)}% + 2px)` }

const rowClass = (span) => {
    if (span.index === props.selected) return 'bg-amber-50 dark:bg-amber-500/15'
    if (props.highlightSpanId && span.id === props.highlightSpanId) return 'bg-sky-50 dark:bg-sky-500/10'
    return 'hover:bg-neutral-50 dark:hover:bg-neutral-800/60'
}

const fraction = (event) => {
    const box = minimapRef.value.getBoundingClientRect()
    return Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1)
}
const onMinimapDown = (event) => {
    minimapRef.value.setPointerCapture?.(event.pointerId)
    const f = fraction(event)
    drag.value = { a: f, b: f }
}
const onMinimapMove = (event) => {
    if (drag.value) drag.value = { ...drag.value, b: fraction(event) }
}
const onMinimapUp = () => {
    if (!drag.value) return
    const [a, b] = [drag.value.a, drag.value.b].sort((x, y) => x - y)
    drag.value = null
    if (b - a < 0.005) return resetZoom()
    view.value = { from: a * total.value, to: b * total.value }
}
</script>

<style scoped>
.label-col {
    width: 38%;
    min-width: 260px;
    max-width: 520px;
    flex-shrink: 0;
}
.minimap-dim {
    fill: rgb(115 115 115 / 0.35);
}
</style>
