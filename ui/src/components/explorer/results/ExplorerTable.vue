<template>
    <Drawer v-model:visible="visible" :modal="false" position="right" pt:root:style="width:70%;">
        <template #container>
            <Row :source="source" :row="selectedRow"></Row>
        </template>
    </Drawer>
    <div class="overflow-x-auto" v-if="rows && rows.length > 0 && dateFormat">
        <table class="w-full min-w-full text-sm">
            <thead>
                <tr>
                    <th
                        v-if="source.severityField.length != 0"
                        class="border-b border-neutral-200 dark:border-neutral-700"
                    ></th>
                    <th class="pl-2 pr-2 text-left border-l border-b border-neutral-200 dark:border-neutral-700 font-medium">
                        Time
                    </th>
                    <th
                        class="pl-2 pr-2 text-left border-l border-b border-neutral-200 dark:border-neutral-700 font-medium"
                        v-for="field in fields"
                        :key="field.name"
                    >
                        {{ field.display_name }}
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr
                    class="hover:bg-slate-100 dark:hover:bg-neutral-800 hover:cursor-pointer"
                    v-for="row in rows"
                    :key="row.record_id"
                    @click="handleRowClick(row)"
                >
                    <td
                        v-if="source.severityField.length != 0"
                        class="pl-1 pr-2 w-1 m-w-1 border-b border-neutral-200 dark:border-neutral-700"
                    >
                        <div
                            class="rounded w-2 h-6"
                            :style="{ 'background-color': getRowColor(row) }"
                            :title="row.data[source.severityField]"
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
                        v-for="field in fields"
                        :key="field.name"
                    >
                        <div
                            v-if="containsHtmlModifiers(field)"
                            :class="{ 'whitespace-pre-wrap break-all': getRowValueLength(field, row.data) > 50 }"
                            v-html="getRowValue(field, row.data)"
                        />
                        <pre
                            v-else
                            :class="{ 'whitespace-pre-wrap break-all': getRowValueLength(field, row.data) > 50 }"
                            >{{ getRowValue(field, row.data) || '&dash;' }}</pre
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
import { ref, onMounted } from 'vue'
import { format } from 'date-fns'

import Drawer from 'primevue/drawer'

import Row from '@/components/explorer/results/Row.vue'

import { getColor } from '@/utils/colors.js'
import { MODIFIERS } from '@/utils/modifiers.js'

const props = defineProps(['source', 'rows', 'fields', 'timezone'])
const selectedRow = ref(null)
const visible = ref(false)
const dateFormat = ref(null)
const showMicroseconds = ref(false)

const getTime = (data) => {
    return format(new Date(data.datetime), dateFormat.value)
}

const handleRowClick = (row) => {
    selectedRow.value = row
    visible.value = true
}

const getRowColor = (row) => {
    return getColor(row.data[props.source.severityField])
}

const containsHtmlModifiers = (field) => {
    for (const modifier of field.modifiers) {
        if (MODIFIERS[modifier.name].type == 'html') {
            return true
        }
    }
    return false
}

const getRowValue = (field, data) => {
    let value = ''
    if (field.jsonstring) {
        // explorer contains object
        value = extractJsonPath(field, data)
    } else if (field.name.includes(':')) {
        if (Array.isArray(data[field.root_name])) {
            const index = Number(field.name.split(':')[1])
            value = data[field.root_name][index]
        } else {
            value = extractJsonPath(field, data)
        }
    } else {
        data = data[field.root_name]
        value = data
    }
    for (const modifier of field.modifiers) {
        if (MODIFIERS[modifier.name].type == 'value') {
            let func = MODIFIERS[modifier.name].func
            value = func(value, ...modifier.arguments)
        }
    }
    for (const modifier of field.modifiers) {
        if (MODIFIERS[modifier.name].type == 'html') {
            let func = MODIFIERS[modifier.name].func
            value = func(value, ...modifier.arguments)
        }
    }
    return value
}

const getRowValueLength = (field, data) => {
    let value = getRowValue(field, data)
    if (typeof value === 'object') {
        return JSON.stringify(value).length
    }
    return String(value).length
}

const extractJsonPath = (field, data) => {
    const path = field.name.split(':')
    let value = data
    for (const key of path) {
        if (typeof value === 'object' && key in value) {
            value = value[key]
        } else {
            return undefined
        }
    }
    return value
}

onMounted(() => {
    let now = new Date()
    let month = now.getMonth()
    let year = now.getFullYear()
    let fmt = ''
    let yearSet = new Set()
    let daySet = new Set()
    for (const row of props.rows) {
        let dt = new Date(row.time.datetime)
        yearSet.add(dt.getFullYear())
        daySet.add(dt.getDay())
        if (row.time.microseconds != 0) {
            showMicroseconds.value = true
        }
    }
    if (yearSet.size > 1) {
        fmt += 'yyyy '
    } else {
        if (yearSet.size == 1 && yearSet.values().next().value != year) {
            fmt += 'yyyy '
        }
    }
    if (daySet.size > 1 || daySet.values().next().value != month) {
        fmt += 'MMM dd, '
    } else {
        if (daySet.size == 1 && daySet.values().next().value != month) {
            fmt += 'MMM dd, '
        }
    }
    fmt += 'HH:mm:ss'
    dateFormat.value = fmt
})
</script>
