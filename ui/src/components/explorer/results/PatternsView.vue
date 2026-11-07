<template>
    <div data-testid="patterns-view">
        <div class="flex flex-wrap items-center gap-3 pb-2 text-sm">
            <label class="flex items-center gap-2">
                <span class="text-neutral-500 dark:text-neutral-400">Column</span>
                <Select
                    v-model="column"
                    :options="columnOptions"
                    size="small"
                    placeholder="Body"
                    @change="load"
                    data-testid="patterns-column"
                />
            </label>
            <label class="flex items-center gap-2">
                <span class="text-neutral-500 dark:text-neutral-400">Sample</span>
                <Select
                    v-model="sample"
                    :options="sampleOptions"
                    optionLabel="label"
                    optionValue="value"
                    size="small"
                    @change="load"
                    data-testid="patterns-sample"
                />
            </label>
            <span v-if="data" class="text-xs text-neutral-500 dark:text-neutral-400" data-testid="patterns-summary">
                {{ data.patterns.length }} patterns in {{ data.sample_size.toLocaleString() }}
                <template v-if="sampled">sampled of {{ data.total.toLocaleString() }}</template>
                rows of {{ data.column }}
            </span>
        </div>
        <Skeleton v-if="loading && !data" width="100%" height="300px" />
        <div v-if="error" class="text-sm text-red-600 dark:text-red-400 py-2" data-testid="patterns-error">
            {{ error }}
        </div>
        <div
            v-if="data && !data.patterns.length && !error"
            class="py-10 text-center text-sm text-neutral-500 dark:text-neutral-400"
        >
            No rows match the search.
        </div>
        <PatternTable
            v-if="data && data.patterns.length"
            :patterns="data.patterns"
            :sampled="sampled"
            :selectedId="selected?.id"
            @select="(p) => (selected = p)"
        />
        <PatternDrawer
            :pattern="selected"
            :sampled="sampled"
            :timeZone="timeZone"
            @close="selected = null"
            @filter="onFilter"
        />
    </div>
</template>

<script>
import { PATTERN_KINDS } from '@/components/explorer/patterns/patterns'

// Explorer shows the results-mode toggle only when available(source) is true.
export function available(source) {
    return PATTERN_KINDS.includes(source?.kind)
}
</script>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Select, Skeleton, useToast } from 'primevue'

import PatternTable from '@/components/explorer/patterns/PatternTable.vue'
import PatternDrawer from '@/components/explorer/patterns/PatternDrawer.vue'
import { buildRequest, fetchPatterns, patternColumns, withPatternFilter } from '@/components/explorer/patterns/patterns'
import { useSourceControlsStore } from '@/stores/sourceControls'

const props = defineProps(['source', 'searchSeq', 'timeZone'])
const emit = defineEmits(['searchRequest'])

const store = useSourceControlsStore()
const toast = useToast()

const column = ref(null)
const sample = ref(10000)
const sampleOptions = [1000, 10000, 50000, 100000].map((value) => ({ label: value.toLocaleString(), value }))
const columnOptions = computed(() => patternColumns(props.source))
const data = ref(null)
const error = ref(null)
const loading = ref(false)
const selected = ref(null)
const sampled = computed(() => !!data.value && data.value.sample_size < data.value.total)
let controller = null

const load = async () => {
    if (controller) controller.abort()
    controller = new AbortController()
    const signal = controller.signal
    loading.value = true
    const response = await fetchPatterns(props.source.slug, buildRequest(store, column.value, sample.value), signal)
    if (signal.aborted) return
    loading.value = false
    selected.value = null
    if (response.result) {
        data.value = response.data
        column.value = response.data.column
        error.value = null
    } else {
        data.value = null
        error.value =
            response.validation && response.validation.result === false
                ? Object.values(response.validation.columns || {})
                      .flat()
                      .join(', ')
                : response.errors.join(', ')
    }
}

// The search runs again with the pattern's LIKE added; the explorer then shows its rows.
const onFilter = (pattern) => {
    store.setQuery(withPatternFilter(store.query, pattern.filter))
    toast.add({ severity: 'success', summary: 'Success', detail: 'Query was updated', life: 3000 })
    selected.value = null
    emit('searchRequest')
}

watch(
    () => props.searchSeq,
    () => load(),
)

onMounted(() => load())
</script>
