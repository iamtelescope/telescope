<template>
    <div ref="rootRef" class="flex flex-col gap-3 p-4" data-testid="context-tab">
        <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-medium w-20">Window</span>
            <SelectButton
                v-model="range"
                :options="CONTEXT_RANGES"
                optionLabel="label"
                optionValue="value"
                :allowEmpty="false"
                size="small"
                data-testid="context-range"
            />
            <span class="font-mono text-sm text-neutral-500" data-testid="context-range-label">±{{ rangeLabel }}</span>
        </div>
        <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-medium w-20">Match on</span>
            <SelectButton
                :modelValue="displayedPreset"
                @update:modelValue="onPreset"
                :options="presets"
                optionLabel="label"
                optionValue="value"
                :allowEmpty="false"
                size="small"
                data-testid="context-preset"
            />
        </div>
        <div v-if="preset === 'custom'" class="flex items-center gap-2">
            <InputText
                v-model="customDraft"
                class="flex-1 font-mono"
                size="small"
                placeholder="FlyQL, e.g. level = 'error'"
                @keydown.enter="applyCustom"
                data-testid="context-custom-query"
            />
            <Button label="Apply" size="small" severity="secondary" @click="applyCustom" />
        </div>
        <div v-if="filters.length" class="flex flex-wrap gap-1.5" data-testid="context-filters">
            <button
                v-for="filter in filters"
                :key="filter.id"
                type="button"
                class="inline-flex items-center gap-1 max-w-sm rounded px-2 py-0.5 text-xs border font-mono"
                :class="
                    selected.includes(filter.id)
                        ? 'border-amber-500 bg-amber-50 dark:bg-amber-500/15 text-amber-900 dark:text-amber-200'
                        : 'border-dashed border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                "
                :title="filter.expr"
                :aria-pressed="selected.includes(filter.id)"
                :data-testid="`context-filter-${filter.id}`"
                @click="toggle(filter.id)"
            >
                <i
                    :class="selected.includes(filter.id) ? 'pi pi-check' : 'pi pi-plus opacity-50'"
                    class="text-[10px]"
                ></i>
                <span class="font-semibold shrink-0">{{ filter.label }}</span>
                <span class="opacity-60">=</span>
                <span class="truncate">{{ filter.value }}</span>
            </button>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
            <span class="text-neutral-600 dark:text-neutral-400" data-testid="context-summary">
                <template v-if="rows">
                    <span class="font-medium text-neutral-900 dark:text-neutral-100" data-testid="context-count">{{
                        rows.length
                    }}</span>
                    {{ rows.length === 1 ? 'row' : 'rows' }}
                    <span v-if="truncated">(newest {{ CONTEXT_LIMIT }} shown, narrow the window to see all)</span>
                </template>
                <code v-if="query" class="ml-2 text-xs" data-testid="context-query">{{ query }}</code>
            </span>
            <a
                :href="explorerHref"
                target="_blank"
                rel="noopener"
                class="text-sm text-primary hover:underline"
                data-testid="context-open-explorer"
                >Open in explorer <i class="pi pi-external-link text-xs"></i
            ></a>
        </div>
        <Error v-if="error" :error="error" />
        <ValidationError
            v-if="validation && !validation.result"
            :validation="validation"
            message="Failed to load context: invalid parameters given"
        />
        <Skeleton v-if="loading && rows === null" width="100%" height="200px" />
        <div
            v-if="rows && rows.length"
            ref="scrollRef"
            class="relative overflow-auto max-h-[60vh] border border-neutral-200 dark:border-neutral-700 rounded"
            data-testid="context-table"
        >
            <table class="w-full text-sm">
                <thead class="sticky top-0 z-10 bg-white dark:bg-neutral-900">
                    <tr>
                        <th class="w-1"></th>
                        <th class="px-2 text-left font-medium">Time</th>
                        <th class="px-2 text-right font-medium">Offset</th>
                        <th v-for="column in shownColumns" :key="column.name" class="px-2 text-left font-medium">
                            {{ column.display_name }}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="(item, index) in rows"
                        :key="index"
                        :class="
                            index === currentIndex
                                ? 'bg-amber-100 dark:bg-amber-500/20 font-medium'
                                : 'hover:bg-slate-100 dark:hover:bg-neutral-800'
                        "
                        :data-current="index === currentIndex ? 'true' : undefined"
                        :data-testid="`context-row-${index}`"
                    >
                        <td class="pl-1 border-t border-neutral-200 dark:border-neutral-700">
                            <div
                                v-if="item.severity"
                                class="rounded w-1.5 h-5"
                                :style="{ backgroundColor: getColor(item.severity) }"
                                :title="item.severity"
                            ></div>
                        </td>
                        <td class="px-2 py-1 font-mono text-nowrap border-t border-neutral-200 dark:border-neutral-700">
                            {{ formatTime(item.time) }}
                        </td>
                        <td
                            class="px-2 py-1 font-mono text-nowrap text-right text-xs text-neutral-500 border-t border-neutral-200 dark:border-neutral-700"
                        >
                            {{ index === currentIndex ? 'this row' : formatOffset(item.time) }}
                        </td>
                        <td
                            v-for="column in shownColumns"
                            :key="column.name"
                            class="px-2 py-1 font-mono border-t border-neutral-200 dark:border-neutral-700 dark:text-neutral-300"
                        >
                            <div
                                v-if="renderCell(column, item.data).isHtml"
                                v-html="renderCell(column, item.data).value"
                            />
                            <span v-else :class="cellClass(renderCell(column, item.data).value)">{{
                                display(renderCell(column, item.data).value)
                            }}</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <p v-else-if="rows" class="text-sm text-neutral-600 dark:text-neutral-400">No rows in this window.</p>
    </div>
</template>

<script>
// Row.vue renders this only when available(source, row) is true.
export function available(source, row) {
    return !!(source && row && row.time && row.time.unixtime !== undefined)
}
</script>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useElementVisibility } from '@vueuse/core'
import { Button, InputText, SelectButton, Skeleton } from 'primevue'
import { DateTime } from 'luxon'

import Error from '@/components/common/Error.vue'
import ValidationError from '@/components/common/ValidationError.vue'
import { useGetSourceData } from '@/composables/sources/useSourceService'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { applyColumnPipeline } from '@/utils/flyql-registries.js'
import { getColor } from '@/utils/colors.js'
import {
    CONTEXT_LIMIT,
    CONTEXT_RANGES,
    DEFAULT_CONTEXT_RANGE,
    availablePresets,
    buildContextQuery,
    contextWindow,
    extractQuickFilters,
    isSameRow,
    presetFilterIds,
} from '@/utils/context.js'

const props = defineProps(['source', 'row', 'timeZone'])

const router = useRouter()
const store = useSourceControlsStore()
const { rows, columns, error, loading, validation, load, controller } = useGetSourceData()
// Time is its own column, so a plain copy of the source time column is not repeated.
const shownColumns = computed(() =>
    (columns.value || []).filter(
        (c) => !(c.name === props.source.timeColumn && c.display_name === c.name && !c.transformers?.length),
    ),
)

const rootRef = ref(null)
const scrollRef = ref(null)
const visible = useElementVisibility(rootRef)

const range = ref(DEFAULT_CONTEXT_RANGE)
const preset = ref('all')
const selected = ref([])
const customDraft = ref('')
const custom = ref('')

const filters = computed(() => extractQuickFilters(props.source, props.row))
const presets = computed(() => availablePresets(filters.value, props.source))
// A hand-picked set of chips shows no preset as selected.
const displayedPreset = computed(() => (preset.value === 'custom' || selected.value.length ? preset.value : 'all'))
const rangeLabel = computed(() => CONTEXT_RANGES.find((r) => r.value === range.value)?.label)
const timeWindow = computed(() => contextWindow(props.row, range.value))
const query = computed(() =>
    buildContextQuery(selected.value, filters.value, preset.value === 'custom' ? custom.value : ''),
)
const explorerColumns = computed(() => store.columns || props.source.defaultChosenColumns.join(', '))
const contextColumns = computed(() => structuredClone(store.contextColumns || {}))
const truncated = computed(() => rows.value && rows.value.length >= CONTEXT_LIMIT)
const currentIndex = computed(() => (rows.value ? rows.value.findIndex((r) => isSameRow(r, props.row)) : -1))

const explorerHref = computed(() => {
    const q = {
        from: timeWindow.value.from,
        to: timeWindow.value.to,
        columns: explorerColumns.value,
        timeZone: props.timeZone,
    }
    if (query.value) q.query = query.value
    for (const [key, value] of Object.entries(contextColumns.value)) q[`ctx_${key}`] = value
    return router.resolve({ name: 'explore', params: { sourceSlug: props.source.slug }, query: q }).href
})

const onPreset = (value) => {
    preset.value = value
    selected.value = value === 'all' || value === 'custom' ? [] : presetFilterIds(value, filters.value, props.source)
}

const toggle = (id) => {
    selected.value = selected.value.includes(id) ? selected.value.filter((x) => x !== id) : [...selected.value, id]
    if (preset.value !== 'custom') preset.value = null
}

const applyCustom = () => {
    custom.value = customDraft.value
}

const fetchContext = async () => {
    controller.value?.abort()
    await load(props.source.slug, {
        columns: explorerColumns.value,
        limit: CONTEXT_LIMIT,
        from: timeWindow.value.from,
        to: timeWindow.value.to,
        query: query.value,
        context_columns: contextColumns.value,
    })
    await nextTick()
    const el = scrollRef.value?.querySelector('[data-current="true"]')
    if (el) scrollRef.value.scrollTop = el.offsetTop - scrollRef.value.clientHeight / 2
}

watch(
    () => props.row,
    () => {
        preset.value = 'all'
        selected.value = []
        customDraft.value = ''
        custom.value = ''
        rows.value = null
    },
)

// Fetch only while the tab is shown: hidden tab panels stay mounted.
watch(
    [visible, () => props.row, range, query],
    () => {
        if (visible.value) fetchContext()
    },
    { immediate: true },
)

const formatTime = (time) => {
    const dt = DateTime.fromMillis(time.unixtime, { zone: props.timeZone }).toFormat('yyyy-MM-dd HH:mm:ss')
    return `${dt}.${time.microseconds}`
}

const formatOffset = (time) => {
    const base = props.row.time
    const us = (time.unixtime - base.unixtime) * 1000 + (time.microseconds % 1000) - (base.microseconds % 1000)
    const abs = Math.abs(us) / 1000
    const text = abs >= 1000 ? `${(abs / 1000).toFixed(3)}s` : `${+abs.toFixed(3)}ms`
    return `${us < 0 ? '-' : '+'}${text}`
}

const display = (value) => {
    if (value === null || value === undefined || value === '') return '–'
    return typeof value === 'object' ? JSON.stringify(value) : value
}

const cellClass = (value) => (String(display(value)).length > 50 ? 'whitespace-pre-wrap break-words' : 'text-nowrap')

const renderCell = (column, data) => {
    let raw = data[column.root_name]
    if (column.is_segmented) {
        raw = data
        for (const seg of column.segments || column.name.split('.')) {
            raw = raw !== null && typeof raw === 'object' ? raw[seg] : undefined
        }
    }
    return applyColumnPipeline(column, raw)
}
</script>
