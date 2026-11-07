<template>
    <div class="flex flex-col h-full min-h-0" :data-testid="`log-tile-${chart.display}`">
        <div
            v-if="code === 'no_access'"
            class="flex flex-col items-center justify-center gap-1.5 h-full p-2 text-center text-sm text-surface-500 dark:text-surface-400"
        >
            <i class="pi pi-lock text-xl"></i>
            <span>You don't have access to source {{ chart.source }}</span>
        </div>
        <div v-else-if="validation && validation.result === false" class="h-full overflow-auto">
            <ValidationError :validation="validation" message="Invalid tile settings" />
        </div>
        <div
            v-else-if="error"
            class="flex flex-col items-center justify-center gap-1.5 h-full p-2 text-center text-sm text-surface-500 dark:text-surface-400"
        >
            <i class="pi pi-exclamation-triangle text-xl text-red-500 dark:text-red-400"></i>
            <span class="font-medium text-surface-700 dark:text-surface-200">Query failed</span>
            <pre
                class="max-w-full max-h-[50%] overflow-auto whitespace-pre-wrap break-words text-left text-xs font-mono px-2"
                >{{ error }}</pre
            >
        </div>
        <div v-else-if="!data || !source" class="flex flex-col gap-2 p-1" data-testid="chart-skeleton">
            <Skeleton v-for="idx in 6" :key="idx" height="1.25rem" :width="`${100 - idx * 8}%`" />
        </div>
        <div
            v-else-if="isEmpty"
            class="flex flex-col items-center justify-center gap-1.5 h-full p-2 text-center text-sm text-surface-500 dark:text-surface-400"
        >
            <i class="pi pi-list text-xl"></i>
            <span>{{ chart.display === 'search' ? 'No rows in this time range' : 'No rows match the search' }}</span>
        </div>
        <template v-else-if="chart.display === 'search'">
            <div class="flex-1 min-h-0 overflow-auto">
                <ExplorerTable :source="source" :rows="data.rows" :columns="data.columns" :timeZone="timeZone" />
            </div>
            <div
                class="flex items-center justify-between gap-2 shrink-0 pt-1 text-xs text-surface-500 dark:text-surface-400"
            >
                <span data-testid="log-tile-count">{{ data.rows.length.toLocaleString() }} rows</span>
                <Button
                    v-if="cursor && supportsPaging(source)"
                    label="Load more"
                    icon="pi pi-angle-down"
                    text
                    size="small"
                    :loading="loadingMore"
                    :disabled="loading"
                    data-testid="log-tile-load-more"
                    @click="loadMore"
                />
            </div>
        </template>
        <template v-else>
            <div class="shrink-0 pb-1 text-xs text-surface-500 dark:text-surface-400" data-testid="patterns-summary">
                {{ data.patterns.length }} patterns in {{ data.sample_size.toLocaleString() }}
                <template v-if="sampled">sampled of {{ data.total.toLocaleString() }}</template>
                rows of {{ data.column }}
            </div>
            <div class="flex-1 min-h-0 overflow-auto">
                <PatternTable
                    :patterns="data.patterns"
                    :sampled="sampled"
                    :selectedId="selected?.id"
                    @select="(p) => (selected = p)"
                />
            </div>
            <PatternDrawer
                :pattern="selected"
                :sampled="sampled"
                :timeZone="timeZone"
                @close="selected = null"
                @filter="onFilter"
            />
        </template>
    </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Skeleton, useToast } from 'primevue'

import ValidationError from '@/components/common/ValidationError.vue'
import ExplorerTable from '@/components/explorer/results/ExplorerTable.vue'
import PatternTable from '@/components/explorer/patterns/PatternTable.vue'
import PatternDrawer from '@/components/explorer/patterns/PatternDrawer.vue'
import { fetchLogTile, loadSource, logTileBody, logTileExplorerRoute } from './logTiles'
import { supportsPaging } from '@/utils/explorerPaging'

// `range` is the dashboard's {from, to, query, params}; `queue` limits requests per dashboard.
const props = defineProps(['chart', 'range', 'timeZone', 'queue', 'refreshTick', 'attribution'])
const emit = defineEmits(['loading'])

const router = useRouter()
const toast = useToast()
const source = ref(null)
const data = ref(null)
const error = ref(null)
const code = ref(null)
const validation = ref(null)
const loading = ref(false)
const loadingMore = ref(false)
const cursor = ref(null)
const selected = ref(null)
// The first page's range as the server resolved it, so later pages keep its 'now'.
let resolved = null
let controller = null

const sampled = computed(() => !!data.value && data.value.sample_size < data.value.total)
const isEmpty = computed(() => !(data.value.rows || data.value.patterns).length)

const request = async (body, signal) => {
    const call = () => fetchLogTile(props.chart, body, signal, props.attribution)
    return props.queue ? await props.queue(call, signal) : await call()
}

const apply = (response) => {
    error.value = response.result ? null : response.errors.join(', ')
    code.value = response.result ? null : response.data?.code || null
    validation.value = response.validation
}

const load = async () => {
    // A reload drops an in-flight Load more, whose rows would follow the old first page.
    controller?.abort()
    loadingMore.value = false
    const current = new AbortController()
    controller = current
    loading.value = true
    emit('loading', true)
    selected.value = null
    const [s, response] = await Promise.all([
        loadSource(props.chart.source),
        request(logTileBody(props.chart, props.range), current.signal),
    ])
    if (current.signal.aborted || !response) return
    source.value = s
    apply(response)
    if (response.result && !s) error.value = `Source ${props.chart.source} not found`
    const ok = response.result && response.validation?.result !== false
    data.value = ok ? response.data : null
    cursor.value = ok ? response.data.cursor || null : null
    resolved = ok && response.data.time_from ? { from: response.data.time_from, to: response.data.time_to } : null
    loading.value = false
    emit('loading', false)
    controller = null
}

const loadMore = async () => {
    if (loading.value) return
    const current = new AbortController()
    controller = current
    loadingMore.value = true
    const body = logTileBody(props.chart, { ...props.range, ...(resolved || {}) }, cursor.value)
    const response = await request(body, current.signal)
    if (current.signal.aborted || !response) return
    loadingMore.value = false
    controller = null
    if (response.result && response.validation?.result !== false) {
        data.value = { ...data.value, rows: data.value.rows.concat(response.data.rows) }
        cursor.value = response.data.cursor || null
    } else {
        const detail = response.errors.join(', ') || JSON.stringify(response.validation?.fields ?? {})
        toast.add({ severity: 'error', summary: 'Failed to load more rows', detail, life: 6000 })
    }
}

const onFilter = (pattern) => {
    router.push(logTileExplorerRoute(props.chart, props.range, props.timeZone, pattern.filter))
}

watch(
    () => [
        JSON.stringify(props.chart),
        props.range.from,
        props.range.to,
        props.range.query,
        JSON.stringify(props.range.params),
    ],
    load,
    { immediate: true },
)

watch(
    () => props.refreshTick,
    () => {
        if (!loading.value && !loadingMore.value) load()
    },
)

onBeforeUnmount(() => controller?.abort())
</script>
