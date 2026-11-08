<template>
    <Drawer
        v-model:visible="visible"
        :modal="false"
        position="right"
        pt:root:style="width:70%;"
        data-testid="detail-drawer"
    >
        <template #container="{ closeCallback }">
            <Row
                :source="source"
                :row="selectedRow"
                :timeZone="props.timeZone"
                :index="selectedIndex"
                :count="rows.length"
                @prev="step(-1)"
                @next="step(1)"
                @close="closeCallback"
            ></Row>
        </template>
    </Drawer>
    <ContextMenu ref="cellMenu" :model="cellMenuItems" data-testid="cell-menu" />
    <div
        class="overflow-x-auto"
        v-if="rows && rows.length > 0"
        data-testid="explorer-table"
        ref="tableRef"
        title="Click a row for details; right-click a value to copy or filter"
    >
        <table class="w-full min-w-full text-sm">
            <thead>
                <tr>
                    <th class="border-b border-neutral-200 dark:border-neutral-700"></th>
                    <th
                        class="pl-2 pr-2 text-left border-l border-b border-neutral-200 dark:border-neutral-700 font-medium"
                        :title="`Time (${timeZone})`"
                    >
                        Time
                    </th>
                    <th
                        class="relative pl-2 pr-2 text-left border-l border-b border-neutral-200 dark:border-neutral-700 font-medium group/th"
                        v-for="(column, i) in shownColumns"
                        :key="column.name"
                        :style="widthStyle(column)"
                        :data-testid="`column-header-${column.name}`"
                    >
                        <div class="flex items-center gap-1">
                            <span class="truncate" :title="column.name">{{ column.display_name }}</span>
                            <template v-if="interactive">
                                <button
                                    v-if="i > 0"
                                    :class="ACTION_CLASS"
                                    :aria-label="`Move ${column.name} left`"
                                    v-tooltip.top="'Move left'"
                                    @click="
                                        emitColumns(swapColumns(store.columns, column.name, shownColumns[i - 1].name))
                                    "
                                    :data-testid="`column-left-${column.name}`"
                                >
                                    <i class="pi pi-angle-left text-xs"></i>
                                </button>
                                <button
                                    v-if="i < shownColumns.length - 1"
                                    :class="ACTION_CLASS"
                                    :aria-label="`Move ${column.name} right`"
                                    v-tooltip.top="'Move right'"
                                    @click="
                                        emitColumns(swapColumns(store.columns, column.name, shownColumns[i + 1].name))
                                    "
                                    :data-testid="`column-right-${column.name}`"
                                >
                                    <i class="pi pi-angle-right text-xs"></i>
                                </button>
                                <button
                                    :class="ACTION_CLASS"
                                    :aria-label="`Remove column ${column.name}`"
                                    v-tooltip.top="'Remove column'"
                                    @click="emitColumns(removeColumn(store.columns, column.name))"
                                    :data-testid="`column-remove-${column.name}`"
                                >
                                    <i class="pi pi-times text-xs"></i>
                                </button>
                            </template>
                        </div>
                        <div
                            class="absolute top-0 -right-1 w-2 h-full z-10 cursor-col-resize hover:bg-sky-400/60"
                            role="separator"
                            aria-orientation="vertical"
                            :aria-label="`Resize ${column.name}`"
                            title="Drag to resize, double-click to reset"
                            @mousedown.prevent="startResize($event, column)"
                            @dblclick="resetWidth(column)"
                            :data-testid="`column-resize-${column.name}`"
                        ></div>
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr
                    class="hover:bg-slate-100 dark:hover:bg-neutral-800 hover:cursor-pointer"
                    :class="{ 'bg-sky-100 dark:bg-sky-900/40': visible && index === selectedIndex }"
                    v-for="(row, index) in rows"
                    :key="row.record_id"
                    @click="handleRowClick(index)"
                    :data-testid="`table-row-${index}`"
                    :data-selected="visible && index === selectedIndex ? 'true' : undefined"
                >
                    <td class="pl-1 pr-2 w-1 m-w-1 border-b border-neutral-200 dark:border-neutral-700">
                        <div
                            v-if="row.severity && row.severity !== ''"
                            class="rounded w-2 h-5"
                            :style="{ 'background-color': getColor(row.severity) }"
                            :title="row.severity"
                            role="img"
                            :aria-label="`Severity ${row.severity}`"
                        ></div>
                    </td>
                    <td
                        class="text-nowrap pt-1 pb-1 pl-2 pr-2 font-mono border-l border-b border-neutral-200 dark:border-neutral-700 dark:text-neutral-300"
                        style="width: 50px"
                        :title="fullTime(row.time)"
                    >
                        <pre>{{ getTime(row.time) }}<span v-if="precision" class="text-neutral-500 dark:text-neutral-400">{{ fraction(row.time) }}</span></pre>
                    </td>
                    <td
                        class="pt-1 pb-1 pl-2 pr-2 font-mono border-l border-b border-neutral-200 dark:border-neutral-700 dark:text-neutral-300"
                        v-for="column in shownColumns"
                        :key="column.name"
                        @contextmenu="openCellMenu($event, column, row)"
                    >
                        <div
                            :class="wrap ? 'whitespace-pre-wrap break-words' : 'truncate whitespace-pre'"
                            :style="cellStyle(column)"
                            :title="wrap ? undefined : rawText(column, row.data)"
                        >
                            <span
                                v-if="column.name === source.severityColumn && !cell(column, row.data).isHtml"
                                class="px-1.5 rounded font-medium"
                                :style="{ backgroundColor: tint(cell(column, row.data).value) }"
                                data-testid="severity-value"
                                >{{ display(cell(column, row.data).value) }}</span
                            >
                            <span v-else-if="cell(column, row.data).isHtml" v-html="cell(column, row.data).value" />
                            <template v-else>{{ display(cell(column, row.data).value) }}</template>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    <div v-else-if="interactive" class="flex flex-col items-center py-12 text-center" data-testid="explorer-empty">
        <i class="pi pi-search text-4xl mb-3 text-neutral-400 dark:text-neutral-500"></i>
        <p class="font-semibold text-lg">{{ store.live ? 'Waiting for new rows' : 'No matching rows' }}</p>
        <p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
            {{
                store.live
                    ? 'Live tail shows rows as they arrive.'
                    : 'Nothing in this time range matches the current filters.'
            }}
        </p>
        <div class="flex flex-wrap justify-center gap-2">
            <Button
                label="Search a 4x longer range"
                icon="pi pi-history"
                size="small"
                severity="secondary"
                outlined
                @click="emit('emptyAction', 'widen')"
                data-testid="explorer-empty-widen"
            />
            <Button
                v-if="store.query"
                label="Clear the query"
                icon="pi pi-filter-slash"
                size="small"
                severity="secondary"
                outlined
                @click="emit('emptyAction', 'clearQuery')"
                data-testid="explorer-empty-clear-query"
            />
            <Button
                v-if="store.text"
                label="Clear the text search"
                icon="pi pi-times"
                size="small"
                severity="secondary"
                outlined
                @click="emit('emptyAction', 'clearText')"
                data-testid="explorer-empty-clear-text"
            />
        </div>
    </div>
    <div v-else>
        <p class="font-medium">No data to display</p>
        <p>The query was successful, but returned no results. Please check your filters or time range.</p>
    </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'

import Drawer from 'primevue/drawer'
import { Button, ContextMenu, useToast } from 'primevue'
import { useClipboard } from '@vueuse/core'

import Row from '@/components/explorer/results/Row.vue'

import { getColor } from '@/utils/colors.js'
import { applyColumnPipeline } from '@/utils/flyql-registries.js'
import { columnValue } from '@/utils/explorerPaging.js'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { removeColumn, swapColumns } from '@/components/explorer/results/columnsText.js'
import { DateTime } from 'luxon'
import { Operator as FlyQLOperator } from 'flyql'

// interactive: the explorer's own table (column edits, empty-state actions); dashboard tiles leave it off.
const props = defineProps({
    source: Object,
    rows: Array,
    columns: Array,
    timeZone: String,
    interactive: Boolean,
    wrap: Boolean,
})
const emit = defineEmits(['columnsChanged', 'emptyAction', 'searchRequest'])
const store = useSourceControlsStore()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })

const ACTION_CLASS =
    'hidden group-hover/th:inline-flex focus:inline-flex items-center justify-center w-5 h-5 rounded text-neutral-500 hover:text-primary hover:bg-neutral-200 dark:hover:bg-neutral-700'

const selectedIndex = ref(-1)
const visible = ref(false)
const tableRef = ref(null)
const selectedRow = computed(() => props.rows?.[selectedIndex.value] ?? null)

// The fixed Time column already shows the source's time column, so a plain copy of it is not repeated.
const shownColumns = computed(() =>
    (props.columns || []).filter(
        (c) =>
            !(
                c.name === props.source.timeColumn &&
                c.display_name === c.name &&
                !c.transformers?.length &&
                !c.renderers?.length
            ),
    ),
)

const micros = (time) => String(time.microseconds ?? '').padStart(6, '0')

// Milliseconds unless some row has sub-millisecond digits.
const precision = computed(() => {
    const us = props.rows.map((row) => micros(row.time))
    if (us.some((v) => v.slice(3) !== '000')) return 6
    return us.some((v) => v !== '000000') ? 3 : 0
})

const dateFormat = computed(() => {
    const dateTimes = props.rows.map((r) => DateTime.fromMillis(r.time.unixtime, { zone: props.timeZone }))
    const today = DateTime.now().setZone(props.timeZone)
    const same = (values, todayValue) => values.every((v) => v === todayValue)
    if (
        !same(
            dateTimes.map((d) => d.year),
            today.year,
        )
    )
        return 'yyyy MMM dd, HH:mm:ss'
    if (
        !same(
            dateTimes.map((d) => d.month),
            today.month,
        ) ||
        !same(
            dateTimes.map((d) => d.day),
            today.day,
        )
    )
        return 'MMM dd, HH:mm:ss'
    return 'HH:mm:ss'
})

const getTime = (time) => DateTime.fromMillis(time.unixtime, { zone: props.timeZone }).toFormat(dateFormat.value)

const fraction = (time) => '.' + micros(time).slice(0, precision.value)

const fullTime = (time) =>
    DateTime.fromMillis(time.unixtime, { zone: props.timeZone }).toFormat('yyyy-MM-dd HH:mm:ss') +
    `.${micros(time)} ${props.timeZone}`

const handleRowClick = (index) => {
    selectedIndex.value = index
    visible.value = true
}

const step = (delta) => {
    const next = selectedIndex.value + delta
    if (next < 0 || next >= props.rows.length) return
    selectedIndex.value = next
    nextTick(() =>
        tableRef.value?.querySelector(`[data-testid="table-row-${next}"]`)?.scrollIntoView({ block: 'nearest' }),
    )
}

// Up/Down (or k/j) step through rows while the panel is open, unless the user is typing.
const onKeydown = (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return
    if (event.target?.closest?.('input, textarea, select, [contenteditable="true"], .monaco-editor')) return
    if (event.key === 'ArrowDown' || event.key === 'j') step(1)
    else if (event.key === 'ArrowUp' || event.key === 'k') step(-1)
    else return
    event.preventDefault()
}

watch(visible, (open) => {
    if (open) document.addEventListener('keydown', onKeydown)
    else document.removeEventListener('keydown', onKeydown)
})
// New results (a search, live tail) shift indexes: keep the open row if it is still there.
watch(
    () => props.rows,
    (rows, old) => {
        if (!visible.value) return
        const current = old?.[selectedIndex.value]
        const index = rows ? rows.findIndex((r) => r === current || r.record_id === current?.record_id) : -1
        if (index >= 0) selectedIndex.value = index
        else visible.value = false
    },
)
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

const cell = (column, data) => applyColumnPipeline(column, columnValue(column, data))

const rawText = (column, data, clip = true, raw = undefined) => {
    const value = raw !== undefined ? raw : columnValue(column, data)
    if (value === null || value === undefined) return ''
    const text = typeof value === 'object' ? JSON.stringify(value) : String(value)
    return clip && text.length > 2000 ? text.slice(0, 2000) + '…' : text
}

const display = (value) => {
    if (value === null || value === undefined || value === '') return '–'
    return typeof value === 'object' ? JSON.stringify(value) : value
}

// A light wash of the severity colour behind the text keeps it readable in both themes.
const tint = (value) => {
    const color = getColor(value)
    return /^#[0-9a-f]{6}$/i.test(color) ? `${color}40` : 'transparent'
}

const copyValue = async (text) => {
    try {
        await copy(text)
        toast.add({ severity: 'success', summary: 'Copied', detail: 'Value copied to clipboard', life: 2000 })
    } catch {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to copy to clipboard', life: 6000 })
    }
}

const emitColumns = (text) => emit('columnsChanged', text)

// Right-click on a value: copy it anywhere; in the explorer also filter on it or drop its column.
const cellMenu = ref(null)
const menuTarget = ref(null)
const openCellMenu = (event, column, row) => {
    if (window.getSelection()?.toString()) return
    menuTarget.value = { column, value: columnValue(column, row.data) }
    cellMenu.value.show(event)
}
const filterOn = (operator) => {
    const { column, value } = menuTarget.value
    store.addQueryExpression(column.name, operator, value)
    emit('searchRequest')
}
const cellMenuItems = computed(() => {
    const target = menuTarget.value
    if (!target) return []
    const items = [
        {
            label: 'Copy value',
            icon: 'pi pi-copy',
            disabled: target.value === null || target.value === undefined || target.value === '',
            command: () => copyValue(rawText(target.column, null, false, target.value)),
        },
    ]
    if (!props.interactive) return items
    const scalar = target.value !== null && typeof target.value !== 'object' && !target.column.transformers?.length
    if (scalar)
        items.push(
            {
                label: 'Filter for this value',
                icon: 'pi pi-search-plus',
                command: () => filterOn(FlyQLOperator.EQUALS),
            },
            {
                label: 'Exclude this value',
                icon: 'pi pi-search-minus',
                command: () => filterOn(FlyQLOperator.NOT_EQUALS),
            },
        )
    items.push({
        label: 'Remove column',
        icon: 'pi pi-times',
        command: () => emitColumns(removeColumn(store.columns, target.column.name)),
    })
    return items
})

// Column widths are a per-browser convenience, kept per source.
const widthsKey = computed(() => `telescope.columnWidths.${props.source.slug}`)
const loadWidths = () => {
    try {
        return JSON.parse(localStorage.getItem(widthsKey.value) || '{}') || {}
    } catch {
        return {}
    }
}
const widths = ref(loadWidths())
const saveWidths = () => {
    try {
        localStorage.setItem(widthsKey.value, JSON.stringify(widths.value))
    } catch {
        // storage unavailable: widths last for this page only
    }
}

const widthStyle = (column) => (widths.value[column.name] ? { width: `${widths.value[column.name]}px` } : {})

const cellStyle = (column) => {
    const width = widths.value[column.name]
    return width ? { width: `${width}px`, maxWidth: `${width}px` } : { maxWidth: '40rem' }
}

const startResize = (event, column) => {
    const th = event.target.closest('th')
    const startX = event.clientX
    const startWidth = th.getBoundingClientRect().width - 16
    const onMove = (e) => {
        widths.value = { ...widths.value, [column.name]: Math.max(48, Math.round(startWidth + e.clientX - startX)) }
    }
    const onUp = () => {
        document.removeEventListener('mousemove', onMove)
        document.removeEventListener('mouseup', onUp)
        saveWidths()
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
}

const resetWidth = (column) => {
    const { [column.name]: _, ...rest } = widths.value
    widths.value = rest
    saveWidths()
}
</script>
