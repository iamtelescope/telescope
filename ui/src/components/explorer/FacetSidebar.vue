<template>
    <div
        v-if="collapsed"
        class="shrink-0 self-start border rounded-lg border-neutral-300 dark:border-neutral-600"
        data-testid="facet-sidebar"
    >
        <button
            class="p-2 opacity-70 hover:opacity-100"
            title="Show filters"
            @click="setCollapsed(false)"
            data-testid="facet-toggle"
        >
            <i class="pi pi-filter"></i>
        </button>
    </div>
    <div v-else class="shrink-0 w-64 self-start" data-testid="facet-sidebar">
        <BorderCard :loading="loading">
            <div class="flex items-center gap-2 pb-1 border-b border-neutral-200 dark:border-neutral-700">
                <i class="pi pi-filter text-sm opacity-70"></i>
                <span class="flex-1 font-semibold text-sm">Filters</span>
                <button
                    class="px-1 opacity-60 hover:opacity-100"
                    title="Hide filters"
                    @click="setCollapsed(true)"
                    data-testid="facet-toggle"
                >
                    <i class="pi pi-angle-double-left"></i>
                </button>
            </div>
            <div
                v-if="data"
                class="text-xs opacity-70 py-1"
                data-testid="facet-summary"
                :title="data.sampled ? 'Counts come from the newest rows only' : ''"
            >
                <span v-if="data.sampled">Sampled {{ data.total_sampled.toLocaleString() }} newest rows</span>
                <span v-else>{{ data.total_sampled.toLocaleString() }} rows</span>
            </div>
            <div v-if="error" class="text-xs text-red-600 dark:text-red-400 py-1" data-testid="facet-error">
                {{ error }}
            </div>
            <div v-if="!data && !loading && !error" class="text-xs opacity-70 py-2">Run a search to see values.</div>
            <div class="max-h-[70vh] overflow-y-auto overflow-x-hidden">
                <FacetGroup
                    v-for="facet in groups"
                    :key="facet.id"
                    :id="facet.id"
                    :title="facet.title"
                    :kind="facet.kind"
                    :values="facet.values"
                    :total="data?.total_sampled || 0"
                    :more="facet.more"
                    :pinned="pinned.includes(facet.id)"
                    :removable="facet.key !== null && !pinned.includes(facet.id)"
                    :expandedKeys="mapKeys[facet.column] || []"
                    :class="{ 'pl-3': facet.key !== null }"
                    @include="(item) => addFilter(facet, item, '=')"
                    @exclude="(item) => addFilter(facet, item, '!=')"
                    @toggleKey="(key) => toggleKey(facet.column, key)"
                    @togglePin="togglePin(facet.id)"
                    @remove="toggleKey(facet.column, facet.key)"
                />
            </div>
            <Select
                v-if="addable.length"
                class="w-full mt-2"
                size="small"
                :options="addable"
                placeholder="Add a facet"
                filter
                :modelValue="null"
                @update:modelValue="addFacet"
                data-testid="facet-add"
            />
        </BorderCard>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Select } from 'primevue'

import BorderCard from '@/components/common/BorderCard.vue'
import FacetGroup from '@/components/explorer/facets/FacetGroup.vue'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { useAuthStore } from '@/stores/auth'
import {
    buildRequest,
    defaultFacetColumns,
    facetPath,
    fetchFacets,
    isMapType,
    loadCollapsed,
    loadPinned,
    saveCollapsed,
    savePinned,
    splitFacetId,
    typedValue,
} from '@/components/explorer/facets/facets'

// Left panel of the explorer: top values per column of the last search; click filters, Alt+click excludes.
const props = defineProps(['source', 'searchSeq'])
const emit = defineEmits(['searchRequest'])

const store = useSourceControlsStore()
const authStore = useAuthStore()
const user = computed(() => authStore.user?.username)

const collapsed = ref(loadCollapsed())
const pinned = ref([])
const expandedKeys = ref({})
const data = ref(null)
const error = ref(null)
const loading = ref(false)
let controller = null

// Facet loads wait for the pins, which come from the server.
let pinsReady = null
const fetchPins = () =>
    (pinsReady = loadPinned(user.value, props.source).then((value) => {
        pinned.value = value
    }))
fetchPins()

const defaults = computed(() => defaultFacetColumns(props.source))

// Pinned columns first, then the defaults; pinned Map keys go to map_keys.
const columnIds = computed(() => {
    const ids = pinned.value.filter((id) => id in props.source.columns)
    for (const name of defaults.value) if (!ids.includes(name)) ids.push(name)
    return ids
})

const mapKeys = computed(() => {
    const result = {}
    const add = (column, key) => {
        if (!(column in props.source.columns)) return
        result[column] = result[column] || []
        if (!result[column].includes(key)) result[column].push(key)
    }
    for (const id of pinned.value) {
        const { column, key } = splitFacetId(id, props.source.columns)
        if (key !== null) add(column, key)
    }
    for (const [column, keys] of Object.entries(expandedKeys.value)) for (const key of keys) add(column, key)
    return result
})

const groups = computed(() => {
    if (!data.value) return []
    const more = new Set(data.value.more)
    const group = (column, key, kind, values) => {
        const id = key === null ? column : `${column}.${key}`
        return { id, column, key, kind, title: facetPath(column, key), values: values || [], more: more.has(id) }
    }
    const result = []
    const placed = new Set()
    for (const column of columnIds.value) {
        if (isMapType(props.source.columns[column]?.type)) {
            result.push(group(column, null, 'keys', data.value.map_keys[column]))
        } else {
            result.push(group(column, null, 'value', data.value.facets[column]))
        }
        for (const key of mapKeys.value[column] || []) {
            result.push(group(column, key, 'value', data.value.facets[`${column}.${key}`]))
            placed.add(column)
        }
    }
    for (const [column, keys] of Object.entries(mapKeys.value)) {
        if (placed.has(column)) continue
        for (const key of keys) result.push(group(column, key, 'value', data.value.facets[`${column}.${key}`]))
    }
    return result
})

const addable = computed(() =>
    Object.keys(props.source.columns).filter(
        (name) => name !== props.source.timeColumn && !columnIds.value.includes(name),
    ),
)

const load = async () => {
    if (collapsed.value) return
    await pinsReady
    if (controller) controller.abort()
    controller = new AbortController()
    const signal = controller.signal
    loading.value = true
    const response = await fetchFacets(props.source.slug, buildRequest(store, columnIds.value, mapKeys.value), signal)
    if (signal.aborted) return
    loading.value = false
    if (response.result) {
        data.value = response.data
        error.value = null
    } else if (response.validation && response.validation.result === false) {
        error.value = Object.values(response.validation.columns || {})
            .flat()
            .join(', ')
    } else {
        error.value = response.errors.join(', ')
    }
}

const addFilter = (facet, item, operator) => {
    store.addQueryExpression(
        facetPath(facet.column, facet.key),
        operator,
        typedValue(props.source, facet.column, facet.key, item.value),
    )
    emit('searchRequest')
}

const togglePin = (id) => {
    pinned.value = pinned.value.includes(id) ? pinned.value.filter((p) => p !== id) : [...pinned.value, id]
    savePinned(props.source, pinned.value)
}

const toggleKey = (column, key) => {
    const keys = expandedKeys.value[column] || []
    const id = `${column}.${key}`
    if (keys.includes(key) || pinned.value.includes(id)) {
        expandedKeys.value = { ...expandedKeys.value, [column]: keys.filter((k) => k !== key) }
        if (pinned.value.includes(id)) togglePin(id)
        return
    }
    expandedKeys.value = { ...expandedKeys.value, [column]: [...keys, key] }
    load()
}

const addFacet = (name) => {
    if (!name) return
    togglePin(name)
    load()
}

const setCollapsed = (value) => {
    collapsed.value = value
    saveCollapsed(value)
    if (!value && props.searchSeq > 0) load()
}

watch(
    () => props.searchSeq,
    () => load(),
)

watch(user, async () => {
    await fetchPins()
    if (props.searchSeq > 0) load()
})

onMounted(() => {
    if (props.searchSeq > 0) load()
})
</script>
