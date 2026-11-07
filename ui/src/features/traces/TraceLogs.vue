<template>
    <div class="flex flex-col gap-2 text-sm" data-testid="trace-logs">
        <div class="flex flex-wrap items-center gap-3">
            <h3 class="font-semibold">Correlated logs</h3>
            <span v-if="data" class="text-neutral-600 dark:text-neutral-400" data-testid="trace-logs-summary">
                <span class="font-medium text-neutral-900 dark:text-neutral-100" data-testid="trace-logs-count">{{
                    shown.length
                }}</span>
                {{ shown.length === 1 ? 'log' : 'logs' }}
                <span v-if="onlySpan">for the selected span (of {{ data.logs.length }})</span>
                <span v-if="data.truncated">(first {{ data.logs.length }} shown)</span>
            </span>
            <label v-if="selectedSpanId && data" class="inline-flex items-center gap-1.5 cursor-pointer">
                <Checkbox v-model="onlySpan" binary inputId="trace-logs-only-span" data-testid="trace-logs-only-span" />
                <span>Selected span only</span>
            </label>
            <a
                v-if="data && data.logs.length"
                :href="explorerHref()"
                class="ml-auto text-primary hover:underline"
                data-testid="trace-logs-open-explorer"
                >Open in explorer <i class="pi pi-external-link text-xs"></i
            ></a>
        </div>
        <Message v-if="error" severity="warn" :closable="false" data-testid="trace-logs-error">{{ error }}</Message>
        <Skeleton v-else-if="loading && !data" height="120px" />
        <div
            v-else-if="shown.length"
            class="overflow-auto max-h-[40vh] border border-neutral-200 dark:border-neutral-700 rounded"
        >
            <table class="w-full text-xs">
                <thead class="sticky top-0 bg-white dark:bg-neutral-900">
                    <tr class="text-left">
                        <th class="w-1"></th>
                        <th class="px-2 py-1 font-medium">Time</th>
                        <th class="px-2 py-1 font-medium text-right">Offset</th>
                        <th class="px-2 py-1 font-medium">Service</th>
                        <th class="px-2 py-1 font-medium">Body</th>
                        <th class="w-1"></th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="(log, i) in shown"
                        :key="i"
                        class="border-t border-neutral-100 dark:border-neutral-800 cursor-pointer"
                        :class="
                            log.span_id && log.span_id === selectedSpanId
                                ? 'bg-amber-50 dark:bg-amber-500/15'
                                : 'hover:bg-neutral-50 dark:hover:bg-neutral-800/60'
                        "
                        :data-testid="`trace-log-${i}`"
                        :data-span-id="log.span_id"
                        @click="emit('selectSpan', log.span_id)"
                    >
                        <td class="pl-1">
                            <div
                                class="rounded w-1.5 h-4"
                                :style="{ backgroundColor: getColor(log.severity) }"
                                :title="log.severity"
                            ></div>
                        </td>
                        <td class="px-2 py-1 font-mono whitespace-nowrap">{{ formatTime(log.time_ms) }}</td>
                        <td class="px-2 py-1 font-mono whitespace-nowrap text-right text-neutral-500">
                            {{ startNs ? `+${formatDuration(offsetNs(log.ts_ns, startNs))}` : '' }}
                        </td>
                        <td class="px-2 py-1 whitespace-nowrap">{{ log.service }}</td>
                        <td class="px-2 py-1 font-mono break-all">{{ log.body }}</td>
                        <td class="px-2">
                            <a
                                :href="explorerHref(log)"
                                class="text-primary"
                                title="Show this log in the explorer"
                                :data-testid="`trace-log-explore-${i}`"
                                @click.stop
                                ><i class="pi pi-external-link text-xs"></i
                            ></a>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <p v-else-if="data" class="text-neutral-600 dark:text-neutral-400">No logs carry this trace ID.</p>
    </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Checkbox, Message, Skeleton } from 'primevue'
import { DateTime } from 'luxon'

import { getColor } from '@/utils/colors.js'
import { useTraceLogs } from '@/features/traces/service.js'
import { formatDuration, offsetNs } from '@/features/traces/trace.js'

const props = defineProps({
    slug: { type: String, required: true },
    traceId: { type: String, required: true },
    aroundMs: { type: Number, default: null },
    startNs: { type: String, default: null },
    selectedSpanId: { type: String, default: null },
    timeZone: { type: String, default: 'UTC' },
})
const emit = defineEmits(['selectSpan'])

const router = useRouter()
const { data, error, loading, load } = useTraceLogs()
const onlySpan = ref(false)

watch(
    () => [props.slug, props.traceId, props.aroundMs],
    () => load(props.slug, props.traceId, props.aroundMs),
    { immediate: true },
)
watch(
    () => props.selectedSpanId,
    (id) => {
        if (!id) onlySpan.value = false
    },
)

const shown = computed(() => {
    if (!data.value) return []
    return onlySpan.value ? data.value.logs.filter((l) => l.span_id === props.selectedSpanId) : data.value.logs
})

const formatTime = (ms) => DateTime.fromMillis(ms, { zone: props.timeZone }).toFormat('yyyy-MM-dd HH:mm:ss.SSS')

// The explorer around one log (that span's logs), or around all of them (the whole trace).
const explorerHref = (log) => {
    const d = data.value
    const logs = d.logs
    let query = `${d.trace_id_column} = '${props.traceId}'`
    let from = logs[0].time_ms - 1000
    let to = logs[logs.length - 1].time_ms + 1000
    if (log) {
        if (log.span_id && d.span_id_column) query += ` and ${d.span_id_column} = '${log.span_id}'`
        from = log.time_ms - 1000
        to = log.time_ms + 1000
    }
    return router.resolve({
        name: 'explore',
        params: { sourceSlug: d.source },
        query: { from, to, query, timeZone: props.timeZone },
    }).href
}
</script>
