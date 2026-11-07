<template>
    <div class="flex flex-col h-full min-h-0">
        <div ref="wrapper" class="pie-body flex-1 min-h-0 flex gap-3 items-center" :class="{ 'flex-col': narrow }">
            <svg
                class="pie-svg shrink-0 min-h-0"
                :class="narrow ? 'w-full flex-1' : 'h-full max-w-[60%]'"
                viewBox="-1 -1 2 2"
                data-testid="pie-chart"
            >
                <g v-for="slice in slices" :key="slice.key">
                    <circle
                        v-if="slice.full"
                        r="0.75"
                        fill="none"
                        :stroke="slice.color"
                        stroke-width="0.45"
                        class="pie-slice"
                        :class="{ 'cursor-pointer': clickable, 'pie-slice--dim': active && active !== slice.key }"
                        @click="emit('rowClick', slice.groups || slice.group)"
                        @mouseenter="active = slice.key"
                        @mouseleave="active = null"
                    >
                        <title>{{ slice.title }}</title>
                    </circle>
                    <path
                        v-else
                        :d="slice.path"
                        :fill="slice.color"
                        class="pie-slice stroke-white dark:stroke-surface-900"
                        stroke-width="0.012"
                        :class="{ 'cursor-pointer': clickable, 'pie-slice--dim': active && active !== slice.key }"
                        @click="emit('rowClick', slice.groups || slice.group)"
                        @mouseenter="active = slice.key"
                        @mouseleave="active = null"
                    >
                        <title>{{ slice.title }}</title>
                    </path>
                </g>
                <text
                    x="0"
                    y="0.02"
                    text-anchor="middle"
                    dominant-baseline="middle"
                    class="pie-total fill-surface-900 dark:fill-surface-0 tabular-nums"
                >
                    {{ format(hovered ? hovered.value : total) }}
                </text>
                <text x="0" y="0.2" text-anchor="middle" class="pie-caption fill-surface-500 dark:fill-surface-400">
                    {{ hovered ? hovered.share : 'total' }}
                </text>
            </svg>
            <div
                class="pie-legend min-w-0 overflow-auto flex flex-col gap-0.5"
                :class="narrow ? 'w-full max-h-[40%]' : 'flex-1 max-h-full'"
            >
                <div
                    v-for="slice in slices"
                    :key="slice.key"
                    class="flex items-center gap-2 px-1 rounded text-sm"
                    :class="{
                        'cursor-pointer hover:bg-surface-100 dark:hover:bg-surface-800': clickable,
                        'bg-surface-100 dark:bg-surface-800': active === slice.key,
                    }"
                    :title="slice.title"
                    data-testid="pie-legend-item"
                    @click="emit('rowClick', slice.groups || slice.group)"
                    @mouseenter="active = slice.key"
                    @mouseleave="active = null"
                >
                    <span class="w-2.5 h-2.5 rounded-sm shrink-0" :style="{ background: slice.color }"></span>
                    <span
                        class="min-w-0 flex-1 truncate"
                        :class="isEmptyGroup(slice.group) ? 'italic text-surface-500 dark:text-surface-400' : ''"
                    >
                        {{ groupLabel(slice.group) }}
                    </span>
                    <span class="shrink-0 tabular-nums text-surface-700 dark:text-surface-200">{{
                        format(slice.value)
                    }}</span>
                    <span class="w-11 shrink-0 text-right tabular-nums text-surface-500 dark:text-surface-400">{{
                        slice.share
                    }}</span>
                </div>
            </div>
        </div>
        <TruncatedHint :truncated="data.truncated" :count="data.rows.length" />
    </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useDark } from '@vueuse/core'

import TruncatedHint from '@/components/dashboards/charts/TruncatedHint.vue'
import { seriesUnit, groupLabel, formatTileValue, exactNumber } from '@/components/dashboards/charts/format.js'
import {
    categoricalColor,
    isSeverityGrouping,
    severityColor,
    severityRank,
} from '@/components/dashboards/charts/palette.js'
import { visibleIndex } from '@/utils/dashboards.js'

const props = defineProps(['data', 'chart'])
const emit = defineEmits(['rowClick'])

const isDark = useDark()
const wrapper = ref(null)
const narrow = ref(false)
const active = ref(null)
let observer = null

const clickable = computed(() => !!props.chart.group_by)
const isEmptyGroup = (group) => group === '__none__' || group === ''
const index = computed(() => visibleIndex(props.chart.series))
const unit = computed(() => seriesUnit(props.chart.series?.[index.value], props.chart.number_format))
const format = (v) => formatTileValue(v, unit.value, props.chart.number_format, { compact: true })
const total = computed(() => slices.value.reduce((sum, s) => sum + s.value, 0))
const hovered = computed(() => slices.value.find((s) => s.key === active.value))

// Negative or missing values have no area, so they are left out of the pie.
const slices = computed(() => {
    const theme = isDark.value ? 'dark' : 'light'
    let items = props.data.rows
        .map((row) => ({ group: row.group, groups: row.groups, value: row.values[index.value] }))
        .filter((r) => r.value > 0)
    const severity = isSeverityGrouping(
        props.chart.group_by,
        items.map((r) => r.group),
    )
    items.sort((a, b) => (severity ? severityRank(a.group) - severityRank(b.group) : 0) || b.value - a.value)
    const sum = items.reduce((acc, r) => acc + r.value, 0)
    let angle = -Math.PI / 2
    return items.map((r, idx) => {
        const part = sum ? r.value / sum : 0
        const start = angle
        angle += part * 2 * Math.PI
        const color = (severity && severityColor(r.group, theme)) || categoricalColor(idx, theme)
        const share = `${(part * 100).toFixed(part < 0.1 ? 1 : 0)}%`
        return {
            ...r,
            key: `${r.group}`,
            color,
            share,
            full: part >= 0.9999,
            path: arc(start, angle),
            title: `${groupLabel(r.group)}: ${exactNumber(r.value)} (${share})`,
        }
    })
})

// A donut segment between two angles, outer radius 0.97 and inner 0.53.
const arc = (a0, a1) => {
    const [R, r] = [0.97, 0.53]
    const large = a1 - a0 > Math.PI ? 1 : 0
    const p = (radius, a) => `${(radius * Math.cos(a)).toFixed(4)},${(radius * Math.sin(a)).toFixed(4)}`
    return `M${p(R, a0)} A${R},${R} 0 ${large} 1 ${p(R, a1)} L${p(r, a1)} A${r},${r} 0 ${large} 0 ${p(r, a0)} Z`
}

onMounted(() => {
    observer = new ResizeObserver(([entry]) => {
        narrow.value = entry.contentRect.width < 1.6 * entry.contentRect.height
    })
    observer.observe(wrapper.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<style scoped>
.pie-slice {
    transition: opacity 0.15s;
}
.pie-slice--dim {
    opacity: 0.35;
}
.pie-total {
    font-size: 0.18px;
    font-weight: 600;
}
.pie-caption {
    font-size: 0.09px;
}
</style>
