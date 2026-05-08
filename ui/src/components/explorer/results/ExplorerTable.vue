<template>
    <Drawer
        v-model:visible="visible"
        :modal="false"
        position="right"
        pt:root:style="width:70%;"
        data-testid="detail-drawer"
    >
        <template #container>
            <Row :source="source" :row="selectedRow" :timeZone="props.timeZone"></Row>
        </template>
    </Drawer>
    <div class="overflow-x-auto" v-if="rows && rows.length > 0" data-testid="explorer-table">
        <table class="w-full min-w-full text-sm">
            <thead>
                <tr>
                    <th class="border-b border-neutral-200 dark:border-neutral-700"></th>
                    <th
                        class="pl-2 pr-2 text-left border-l border-b border-neutral-200 dark:border-neutral-700 font-medium"
                    >
                        Time
                    </th>
                    <th
                        class="pl-2 pr-2 text-left border-l border-b border-neutral-200 dark:border-neutral-700 font-medium"
                        v-for="column in columns"
                        :key="column.name"
                    >
                        {{ column.display_name }}
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr
                    class="hover:bg-slate-100 dark:hover:bg-neutral-800 hover:cursor-pointer"
                    v-for="(row, index) in rows"
                    :key="row.record_id"
                    @click="handleRowClick(row)"
                    :data-testid="`table-row-${index}`"
                >
                    <td class="pl-1 pr-2 w-1 m-w-1 border-b border-neutral-200 dark:border-neutral-700">
                        <div
                            v-if="row.severity && row.severity !== ''"
                            class="rounded w-2 h-6"
                            :style="{ 'background-color': getRowColor(row) }"
                            :title="row.severity"
                        ></div>
                    </td>
                    <td
                        class="text-nowrap pt-1 pb-1 pl-2 pr-2 font-mono border-l border-b border-neutral-200 dark:border-neutral-700 dark:text-neutral-300 hover:cursor-pointer hover:bg-slate-300 dark:hover:bg-neutral-900"
                        style="width: 50px"
                    >
                        <pre>{{ getTime(row.time) }}<span v-if="showMicroseconds">.<span class="text-xs text-neutral-500">{{
                            row.time.microseconds }}</span></span></pre>
                    </td>
                    <td
                        class="text-nowrap pt-1 pb-1 pl-2 pr-2 font-mono border-l border-b border-neutral-200 dark:border-neutral-700 dark:text-neutral-300 hover:cursor-pointer hover:bg-slate-300 dark:hover:bg-neutral-900"
                        v-for="column in columns"
                        :key="column.name"
                    >
                        <div
                            v-if="renderCell(column, row.data).isHtml"
                            :class="{ 'whitespace-pre-wrap break-all': getRowValueLength(column, row.data) > 50 }"
                            v-html="renderCell(column, row.data).value"
                        />
                        <pre
                            v-else
                            :class="{ 'whitespace-pre-wrap break-all': getRowValueLength(column, row.data) > 50 }"
                            >{{ renderCell(column, row.data).value || '&dash;' }}</pre
                        >
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    <div v-else>
        <p class="font-medium">No data to display</p>
        <p>The query was successful, but returned no results. Please check your filters or time range.</p>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'

import Drawer from 'primevue/drawer'

import Row from '@/components/explorer/results/Row.vue'

import { getColor } from '@/utils/colors.js'
import { applyColumnPipeline } from '@/utils/flyql-registries.js'
import { DateTime } from 'luxon'

const props = defineProps(['source', 'rows', 'columns', 'timeZone'])
const selectedRow = ref(null)
const visible = ref(false)

const showMicroseconds = computed(() => props.rows.some((row) => row.time.microseconds !== 0))

const dateFormat = computed(() => {
    const dateTimes = props.rows.map((r) => DateTime.fromMillis(r.time.unixtime, { zone: props.timeZone }))
    const today = DateTime.now().setZone(props.timeZone)

    const checkOmittable = (values, todayValue) => {
        const valueSet = new Set(values)
        if (valueSet.size !== 1) return false
        if (valueSet.values().next().value !== todayValue) return false
        return true
    }

    if (
        !checkOmittable(
            dateTimes.map((d) => d.year),
            today.year,
        )
    )
        return 'yyyy MMM dd, HH:mm:ss'

    if (
        !checkOmittable(
            dateTimes.map((d) => d.month),
            today.month,
        ) ||
        !checkOmittable(
            dateTimes.map((d) => d.day),
            today.day,
        )
    )
        return 'MMM dd, HH:mm:ss'

    return 'HH:mm:ss'
})

const getTime = (data) => {
    return DateTime.fromMillis(data.unixtime, { zone: props.timeZone }).toFormat(dateFormat.value)
}

const handleRowClick = (row) => {
    selectedRow.value = row
    visible.value = true
}

const getRowColor = (row) => {
    return getColor(row.severity)
}

const renderCell = (column, data) => {
    let raw
    if (column.is_segmented) {
        raw = extractSegment(column, data)
    } else {
        raw = data[column.root_name]
    }
    return applyColumnPipeline(column, raw)
}

const getRowValueLength = (column, data) => {
    const { value } = renderCell(column, data)
    if (typeof value === 'object') {
        return JSON.stringify(value).length
    }
    return String(value).length
}

const extractSegment = (column, data) => {
    // Walk flyql's parsed segments — they're already unquoted and split,
    // so a path like `labels.'app.kubernetes.io/component'` arrives as
    // ['labels', 'app.kubernetes.io/component'] and a literal-dot key
    // matches directly without the quote-stripping/prefix-peeling that
    // `column.name` would require.
    let segments = column.segments
    if (!segments || segments.length === 0) {
        // Fallback for older payloads that don't carry segments — split
        // by dot, ignoring quote handling. Top-level dotted column names
        // are still resolved via root_name elsewhere.
        segments = column.name ? column.name.split('.') : []
    }
    let cur = data
    for (let i = 0; i < segments.length; i++) {
        if (cur === null || typeof cur !== 'object') return undefined
        const seg = segments[i]
        if (!(seg in cur)) {
            // Tolerant lookup: the column might be a dotted top-level
            // name (e.g. `container.id`) that lives flat in `data`. Try
            // re-joining the remaining segments with dots.
            if (i === 0) {
                const rejoined = segments.join('.')
                if (rejoined in cur) return cur[rejoined]
            }
            return undefined
        }
        cur = cur[seg]
    }
    return cur
}
</script>
