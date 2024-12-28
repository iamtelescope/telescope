<template>
    <Drawer v-model:visible="visible" :modal="false" position="right" pt:root:style="width:70%;">
        <template #container>
            <Row :source="source" :row="selectedRow"></Row>
        </template>
    </Drawer>
    <table class="logs-table" v-if="rows && dateFormat">
        <thead>
            <tr>
                <th></th>
                <th scope="col">Time</th>
                <th scope="col" v-for="field in metadata.fields" :key="field.name">{{ field.display_name }}
                </th>
            </tr>
        </thead>
        <tbody>
            <tr v-for="row in rows" :key="row.record_id" @click="handleRowClick(row)">
                <td>
                    <div class="logs-severity-box" :style="{ 'background-color': getRowColor(row) }"></div>
                </td>
                <td class="nowrap">
                    <pre class="logs-value-field">{{ getTime(row.time) }}.<span class="text-xs text-gray-400">{{
                        row.time.microseconds }}</span></pre>
                </td>
                <td class="nowrap" v-for="field in metadata.fields" :key="field.name">
                    <pre v-if="field.type != 'jsonstring'" class="logs-value-field"
                        :class="{ prewrap: row.data[field.root_name].length > 50 }">{{
                            row.data[field.name] || '&dash;' }}</pre>
                    <pre v-else></pre>
                    <pre v-else="field.type != 'jsonstring'" class="logs-value-field"
                        :class="{ prewrap: extractJsonPathLength(field, row.data) > 50 }">{{ extractJsonPath(field, row.data) }}</pre>
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

const extractJsonPathLength = (field, data) => {
    let value = extractJsonPath(field, data)
    if (value === undefined ) {
        return 0
    } else {
        return String(value).lentgh
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
    if (typeof(value) === 'object') {
        return JSON.stringify(value)
    } else {
        return value
    }
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

<style scoped>
.logs-severity-box {
    border-radius: 3px;
    width: 5px;
    height: 16px;
}

.logs-value-field {
    background-color: transparent;
    border: none;
    padding-top: 0px;
    padding-left: 0px;
    padding-right: 0px;
    padding-bottom: 0px;
    margin: 0px;
    word-break: break-all;
    word-wrap: break-word;
}

.logs-table {
    width: 100%;
    min-width: 100%;
}

.logs-table>tbody>tr:hover {
    background-color: #f3f3f3
}

.logs-table>thead>tr>th {
    text-align: left;
}

.logs-table>tbody>tr>td {
    padding: 3px 5px;
    border-left: 1px solid #f2f2f2;
    border-bottom: 1px solid #f2f2f2;
    font-family: monospace;
}

.logs-table>tbody>tr>td>pre {
    font-size: 13px;
}

.logs-table>tbody>tr>td:hover {
    background-color: #f6f6f6;
    cursor: pointer;
}

.logs-table>tbody>tr>td:first-child {
    max-width: 5px;
    width: 5px;
    padding-right: 10px;
    padding-left: 0px;
}

.logs-table>tbody>tr>td:first-child:hover {
    background-color: transparent;
}

.logs-table>thead>tr>th:first-child {
    padding-left: 0px;
    padding-right: 0px;
}

.logs-table>tbody>tr>td:first-child:hover {
    color: #333333;
}

.logs-table>tbody>tr.detailed-row>td {
    display: none;
}

.logs-table>tbody>tr.detailed-row>td:hover {
    background-color: white;
}

.logs-table>tbody>tr.detailed-row>td:first-child {
    padding-left: 0px;
    cursor: auto;
}

.logs-table>tbody>tr>td:hover {
    background-color: #dbdbdb;
}

.logs-table>thead>tr>th {
    font-size: 13px;
    border-left: 1px solid #f2f2f2;
    border-bottom: none;
}

.dl-info-table {
    width: 100%;
    border-collapse: collapse;
}

.dl-info-table>tbody>tr>th {
    width: 200px;
    min-width: 200px;
}

.dl-info-table>tbody>tr>th,
.dl-info-table>tbody>tr>td {
    text-align: left;
    padding: 10px;
    border-bottom: 1px solid #cad9d5;
    vertical-align: top;
}
</style>
