<template>
    <div class="flex flex-col gap-3 text-sm" data-testid="span-detail">
        <div class="flex items-start gap-2">
            <span class="w-1.5 self-stretch rounded-sm" :style="{ backgroundColor: color }"></span>
            <div class="min-w-0 flex-1">
                <div class="font-semibold text-base break-words" data-testid="span-detail-name">
                    {{ span.synthetic ? `missing span ${span.id}` : span.name }}
                </div>
                <div class="text-neutral-600 dark:text-neutral-400">{{ span.service }}</div>
            </div>
            <Button
                icon="pi pi-times"
                text
                rounded
                size="small"
                severity="secondary"
                aria-label="Close"
                @click="emit('close')"
            />
        </div>
        <p v-if="span.synthetic" class="text-neutral-600 dark:text-neutral-400">
            The parent span {{ span.id }} is not in this trace (not exported, sampled out, or outside the time window).
            Its children are grouped here.
        </p>
        <dl v-else class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
            <dt class="text-neutral-500">Duration</dt>
            <dd class="font-mono" data-testid="span-detail-duration">{{ formatDuration(span.duration_ns) }}</dd>
            <dt class="text-neutral-500">Start</dt>
            <dd class="font-mono">+{{ formatDuration(span.offset_ns) }}</dd>
            <dt class="text-neutral-500">Status</dt>
            <dd
                :class="span.error ? 'text-red-600 dark:text-red-400 font-medium' : ''"
                data-testid="span-detail-status"
            >
                {{ span.status_code || '–' }}<span v-if="span.status_message">: {{ span.status_message }}</span>
            </dd>
            <dt class="text-neutral-500">Kind</dt>
            <dd>{{ span.kind || '–' }}</dd>
            <dt class="text-neutral-500">Span ID</dt>
            <dd class="font-mono">{{ span.id }} <Copy :value="span.id" /></dd>
            <dt class="text-neutral-500">Parent ID</dt>
            <dd class="font-mono">{{ span.parent_id || '–' }}</dd>
        </dl>

        <section
            v-for="ex in exceptions"
            :key="ex.offset_ns"
            class="rounded border border-red-300 dark:border-red-500/40 bg-red-50 dark:bg-red-500/10 p-2"
            data-testid="span-exception"
        >
            <div class="font-medium text-red-700 dark:text-red-300">
                {{ ex.attributes['exception.type'] || 'exception' }}
                <span class="font-normal">{{ ex.attributes['exception.message'] }}</span>
            </div>
            <pre
                v-if="ex.attributes['exception.stacktrace']"
                class="mt-1 text-xs whitespace-pre-wrap break-words max-h-48 overflow-auto"
                >{{ ex.attributes['exception.stacktrace'] }}</pre
            >
        </section>

        <section v-for="group in groups" :key="group.title" :data-testid="`span-${group.id}`">
            <h4 class="font-medium mb-1">
                {{ group.title }} <span class="text-neutral-500 font-normal">({{ group.rows.length }})</span>
            </h4>
            <table v-if="group.rows.length" class="w-full text-xs">
                <tr
                    v-for="[key, value] in group.rows"
                    :key="key"
                    class="border-t border-neutral-100 dark:border-neutral-800 align-top"
                >
                    <td class="py-0.5 pr-3 font-mono text-neutral-600 dark:text-neutral-400 break-all w-2/5">
                        {{ key }}
                    </td>
                    <td class="py-0.5 font-mono break-all">{{ value }}</td>
                </tr>
            </table>
        </section>

        <section data-testid="span-events">
            <h4 class="font-medium mb-1">
                Events <span class="text-neutral-500 font-normal">({{ span.events.length }})</span>
            </h4>
            <div
                v-for="(event, i) in span.events"
                :key="i"
                class="border-t border-neutral-100 dark:border-neutral-800 py-1"
            >
                <div class="flex gap-2">
                    <span class="font-mono text-xs text-neutral-500"
                        >+{{ formatDuration(event.offset_ns - span.offset_ns) }}</span
                    >
                    <span :class="isException(event) ? 'text-red-600 dark:text-red-400 font-medium' : 'font-medium'">{{
                        event.name
                    }}</span>
                </div>
                <div v-for="(value, key) in event.attributes" :key="key" class="pl-4 text-xs font-mono break-all">
                    <span class="text-neutral-500">{{ key }}</span> = {{ value }}
                </div>
            </div>
        </section>

        <section data-testid="span-links">
            <h4 class="font-medium mb-1">
                Links <span class="text-neutral-500 font-normal">({{ span.links.length }})</span>
            </h4>
            <div
                v-for="(link, i) in span.links"
                :key="i"
                class="border-t border-neutral-100 dark:border-neutral-800 py-1 text-xs font-mono"
            >
                <router-link
                    :to="traceRoute(slug, link.trace_id, aroundMs, link.span_id)"
                    class="text-primary hover:underline"
                >
                    {{ link.trace_id }}
                </router-link>
                <span class="text-neutral-500"> span {{ link.span_id }}</span>
                <div v-for="(value, key) in link.attributes" :key="key" class="pl-4 break-all">
                    <span class="text-neutral-500">{{ key }}</span> = {{ value }}
                </div>
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button } from 'primevue'

import Copy from '@/components/common/Copy.vue'
import { formatDuration, isException, traceRoute } from '@/features/traces/trace.js'

const props = defineProps({
    span: { type: Object, required: true },
    color: { type: String, default: '#6b7280' },
    slug: { type: String, required: true },
    aroundMs: { type: Number, default: null },
})
const emit = defineEmits(['close'])

const sorted = (obj) => Object.entries(obj || {}).sort(([a], [b]) => a.localeCompare(b))
const exceptions = computed(() => props.span.events.filter(isException))
const groups = computed(() => [
    { id: 'attributes', title: 'Attributes', rows: sorted(props.span.attributes) },
    { id: 'resource', title: 'Resource', rows: sorted(props.span.resource) },
])
</script>
