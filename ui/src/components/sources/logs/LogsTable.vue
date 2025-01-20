<template>
    <Drawer v-model:visible="visible" :modal="false" position="right" pt:root:style="width:70%;">
        <template #container>
            <Row :source="source" :row="selectedRow"></Row>
        </template>
    </Drawer>
    <table class="w-full min-w-full text-sm logs-table" v-if="rows && dateFormat">
        <thead>
            <tr>
                <th class="border-b border-neutral-200 dark:border-neutral-700"></th>
                <th class="pl-2 pr-2 text-left border-l border-b border-neutral-200 dark:border-neutral-700">Time</th>
                <th class="pl-2 pr-2 text-left border-l border-b border-neutral-200 dark:border-neutral-700" v-for="field in metadata.fields" :key="field.name">{{ field.display_name
                    }}
                </th>
            </tr>
        </thead>
        <tbody>
            <tr class="hover:bg-slate-100 dark:hover:bg-neutral-800 hover:cursor-pointer" v-for="row in rows"
                :key="row.record_id" @click="handleRowClick(row)">
                <td class="pl-1 pr-2 w-1 m-w-1 border-b border-neutral-200 dark:border-neutral-700">
                    <div class="rounded w-2 h-6" :style="{ 'background-color': getRowColor(row) }"></div>
                </td>
                <td
                    class="nowrap pt-1 pb-1 pl-2 pr-2 font-mono border-l border-b border-neutral-200 dark:border-neutral-700 dark:text-neutral-300 hover:cursor-pointer hover:bg-slate-300 dark:hover:bg-neutral-900">
                    <pre class="logs-value-field">{{ getTime(row.time) }}.<span class="text-xs text-neutral-300">{{
                        row.time.microseconds }}</span></pre>
                </td>
                <td class="nowrap pt-1 pb-1 pl-2 pr-2 font-mono border-l border-b border-neutral-200 dark:border-neutral-700 dark:text-neutral-300 hover:cursor-pointer hover:bg-slate-300 dark:hover:bg-neutral-900"
                    v-for="field in metadata.fields" :key="field.name">
                    <pre v-if="field.type != 'jsonstring'" class="border-0 p-0 m-0"
                        :class="{ 'whitespace-pre-wrap break-all': String(row.data[field.root_name]).length > 50 }">{{
                            getRowValue(field, row.data[field.root_name]) || '&dash;' }}</pre>
                    <pre v-else class="border-0 p-0 m-0 break-all whitespace-pre-wrap"
                        :class="{ 'whitespace-pre-wrap break-all': extractJsonPathLength(field, row.data) > 50 }">
                    {{ extractJsonPath(field, row.data) }}</pre>
                </td>
            </tr>
        </tbody>
    </table>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { format } from "date-fns"

import Drawer from "primevue/drawer"

import Row from "@/components/sources/logs/Row.vue"

import { getColor } from '@/utils/colors.js'
import { MODIFIERS } from '@/utils/modifiers.js'

const props = defineProps(['source', 'rows', 'metadata', 'timezone'])
const selectedRow = ref(null)
const visible = ref(false)
const dateFormat = ref(null)

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

const getRowValue = (field, data) => {
    let value = data
    for (const modifier of field.modifiers) {
        let func = MODIFIERS[modifier.name]
        value = func(value, ...modifier.arguments)
    }
    return value
}

const extractJsonPathLength = (field, data) => {
    let value = extractJsonPath(field, data)
    if (value === undefined || value === null) {
        return 0
    } else {
        return String(value).length
    }
}

const extractJsonPath = (field, data) => {
    const path = field.name.split(':')
    let value = data
    for (const key of path) {
        if (typeof (value) === 'object' && key in value) {
            value = value[key]
        } else {
            return undefined
        }
    }
    if (typeof (value) === 'object') {
        value = JSON.stringify(value)
    }
    for (const modifier of field.modifiers) {
        let func = MODIFIERS[modifier.name]
        value = func(value, ...modifier.arguments)
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