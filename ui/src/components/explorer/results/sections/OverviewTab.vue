<template>
    <div class="flex flex-col text-sm pb-4" data-testid="row-overview">
        <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 px-4 py-3" data-testid="row-top-level">
            <template v-for="item in top" :key="item.role">
                <dt class="text-neutral-500">{{ item.label }}</dt>
                <dd class="font-mono [overflow-wrap:anywhere]" :data-testid="`row-top-${item.role}`">
                    {{ item.role === 'duration' ? formatDuration(durationNs(source, item.value)) : item.value }}
                </dd>
            </template>
        </dl>

        <div v-if="highlights.length" class="flex flex-wrap gap-2 px-4 pb-3" data-testid="row-highlighted">
            <span
                v-for="h in highlights"
                :key="h.key"
                class="inline-flex items-center gap-1 rounded border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 pl-2 text-xs"
                data-testid="row-highlight"
            >
                <span class="text-neutral-500">{{ h.key }}</span>
                <span class="font-mono font-medium">{{ h.value }}</span>
                <FilterButtons :path="h.path" :value="h.value" :label="h.key" />
            </span>
        </div>

        <Section v-if="excs.length" title="Exception" :count="excs.length" testid="row-exceptions">
            <div
                v-for="(ex, i) in excs"
                :key="i"
                class="rounded border border-red-300 dark:border-red-500/40 bg-red-50 dark:bg-red-500/10 p-2 mb-2"
                data-testid="row-exception"
            >
                <div class="font-medium text-red-700 dark:text-red-300 break-words">
                    <span data-testid="row-exception-type">{{ ex.type || 'Exception' }}</span>
                    <span v-if="ex.message" class="font-normal">: {{ ex.message }}</span>
                </div>
                <pre
                    v-if="ex.stacktrace"
                    class="mt-1 text-xs whitespace-pre-wrap break-words max-h-72 overflow-auto"
                    data-testid="row-exception-stack"
                    >{{ ex.stacktrace }}</pre
                >
            </div>
        </Section>

        <Section v-if="http" title="HTTP" testid="row-http">
            <div class="font-mono mb-2 break-all" data-testid="row-http-summary">
                <span class="font-semibold">{{ http.method }}</span> {{ http.url || http.route }}
                <span v-if="http.status" :class="statusClass">→ {{ http.status }}</span>
            </div>
            <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                <template v-for="[label, value] in httpFields" :key="label">
                    <dt class="text-neutral-500">{{ label }}</dt>
                    <dd class="font-mono [overflow-wrap:anywhere]">{{ value }}</dd>
                </template>
            </dl>
            <template v-for="part in httpParts" :key="part.title">
                <h4 class="font-medium mt-3 mb-1 text-xs">
                    {{ part.title }} <span class="text-neutral-500 font-normal">({{ part.rows.length }})</span>
                </h4>
                <AttributeTable :rows="part.rows" :filterable="false" />
            </template>
            <template v-for="body in httpBodies" :key="body.title">
                <h4 class="font-medium mt-3 mb-1 text-xs">{{ body.title }}</h4>
                <pre class="text-xs whitespace-pre-wrap break-words max-h-60 overflow-auto">{{ body.text }}</pre>
            </template>
        </Section>

        <Section v-if="events.length" title="Span events" :count="events.length" testid="row-span-events">
            <div
                v-for="(e, i) in events"
                :key="i"
                class="border-t border-neutral-100 dark:border-neutral-800 first:border-t-0 py-1"
                data-testid="row-span-event"
            >
                <div class="text-xs">
                    <span class="font-mono text-neutral-500">{{ e.time }}</span>
                    <span class="font-medium ml-2">{{ e.name }}</span>
                </div>
                <AttributeTable :rows="eventRows(e)" :filterable="false" />
            </div>
        </Section>

        <Section v-if="body" title="Parsed body" :count="body.length" testid="row-parsed-body">
            <AttributeTable :rows="body" :filterable="bodyFilterable" />
        </Section>

        <Section
            v-if="maps.attrs"
            :title="maps.attrs.column"
            :count="attrRows.length"
            testid="row-attributes"
            :collapsed="!attrRows.length"
        >
            <AttributeTable :rows="attrRows" />
        </Section>

        <Section
            v-if="maps.resource"
            :title="maps.resource.column"
            :count="resourceRows.length"
            testid="row-resource"
            :collapsed="!resourceRows.length"
        >
            <AttributeTable :rows="resourceRows" />
        </Section>
    </div>
</template>

<script>
import { isEnriched } from '@/components/explorer/results/sections/rowpanel.js'

// Row.vue renders this only when available(source, row) is true.
export function available(source) {
    return isEnriched(source)
}
</script>

<script setup>
import { computed } from 'vue'

import AttributeTable from '@/components/explorer/results/sections/AttributeTable.vue'
import FilterButtons from '@/components/explorer/results/sections/FilterButtons.vue'
import Section from '@/components/explorer/results/sections/Section.vue'
import {
    attributeMaps,
    durationNs,
    exceptions,
    highlighted,
    httpMessage,
    parseJson,
    parsedBody,
    spanEvents,
    topLevel,
} from '@/components/explorer/results/sections/rowpanel.js'
import { formatDuration } from '@/features/traces/trace.js'

const props = defineProps(['source', 'row', 'timeZone'])

const top = computed(() => topLevel(props.source, props.row))
const highlights = computed(() => highlighted(props.source, props.row))
const excs = computed(() => exceptions(props.source, props.row))
const events = computed(() => spanEvents(props.source, props.row))
const http = computed(() => httpMessage(props.source, props.row))
const body = computed(() => parsedBody(props.source, props.row))
const maps = computed(() => attributeMaps(props.source, props.row))

const bodyFilterable = computed(() => !!props.source.columns?.[props.source.otelRole('body')]?.jsonstring)

const mapRows = (map) =>
    Object.keys(map.values)
        .sort()
        .map((key) => ({ key, path: [map.column, key], value: map.values[key] }))
const attrRows = computed(() => (maps.value.attrs ? mapRows(maps.value.attrs) : []))
const resourceRows = computed(() => (maps.value.resource ? mapRows(maps.value.resource) : []))

const eventRows = (e) => Object.keys(e.attributes).map((key) => ({ key, path: [key], value: e.attributes[key] }))

const statusClass = computed(() =>
    Number(http.value?.status) >= 400
        ? 'text-red-600 dark:text-red-400 font-medium'
        : 'text-green-700 dark:text-green-400',
)

const httpFields = computed(() => {
    const h = http.value
    const fields = [
        ['Route', h.route],
        ['Server', h.server],
        ['Client', h.client],
        ['Protocol', h.protocol],
        ['User agent', h.userAgent],
    ]
    return fields.filter(([, v]) => v !== undefined && v !== null && v !== '')
})

const headerRows = (list) => list.map((h) => ({ key: h.name, path: [h.name], value: h.value }))
const httpParts = computed(() =>
    [
        { title: 'Request headers', rows: headerRows(http.value.requestHeaders) },
        { title: 'Response headers', rows: headerRows(http.value.responseHeaders) },
    ].filter((p) => p.rows.length),
)

const pretty = (text) => {
    const parsed = parseJson(text)
    return parsed === null ? String(text) : JSON.stringify(parsed, null, 2)
}
const httpBodies = computed(() =>
    [
        { title: 'Request body', value: http.value.requestBody },
        { title: 'Response body', value: http.value.responseBody },
    ]
        .filter((b) => b.value !== undefined && b.value !== null && b.value !== '')
        .map((b) => ({ title: b.title, text: pretty(b.value) })),
)
</script>
