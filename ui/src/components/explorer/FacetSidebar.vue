<template>
    <div
        v-if="collapsed"
        class="shrink-0 self-start border rounded-lg border-neutral-300 dark:border-neutral-600"
        data-testid="facet-sidebar"
    >
        <button
            class="p-2 opacity-70 hover:opacity-100"
            title="Show filters"
            aria-label="Show filters"
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
                    aria-label="Hide filters"
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
            <SearchError
                v-if="error"
                :error="error"
                title="Facets unavailable"
                compact
                class="my-1 text-xs"
                data-testid="facet-error"
            />
            <IconField v-if="groups.length > 1" class="my-1">
                <InputIcon class="pi pi-search" />
                <InputText
                    v-model="search"
                    size="small"
                    fluid
                    placeholder="Search facets and values"
                    aria-label="Search facets and values"
                    data-testid="facet-search"
                />
            </IconField>
            <div v-if="search && !shownGroups.length" class="text-xs opacity-70 py-1" data-testid="facet-search-empty">
                No facet or value matches "{{ search }}".
            </div>
            <div v-if="queryInvalid" class="text-xs opacity-70 py-2" data-testid="facet-query-invalid">
                Fix the query to see values.
            </div>
            <div v-else-if="!data && !loading && !error" class="text-xs opacity-70 py-2">
                Run a search to see values.
            </div>
            <div class="max-h-[70vh] overflow-y-auto overflow-x-hidden">
                <FacetGroup
                    v-for="facet in shownGroups"
                    :key="facet.id"
                    :id="facet.id"
                    :title="facet.title"
                    :kind="facet.kind"
                    :values="facet.values"
                    :filter="titleMatches(facet) ? '' : term"
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
                :disabled="!pinsLoaded"
                :modelValue="null"
                @update:modelValue="addFacet"
                data-testid="facet-add"
            />
        </BorderCard>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Select, IconField, InputIcon, InputText } from 'primevue'

import BorderCard from '@/components/common/BorderCard.vue'
import FacetGroup from '@/components/explorer/facets/FacetGroup.vue'
import SearchError from '@/components/explorer/results/SearchError.vue'
import { useSourceControlsStore } from '@/stores/sourceControls'
import { useAuthStore } from '@/stores/auth'
import {
    buildRequest,
    defaultFacetColumns,
    facetPath,
    fetchFacets,
    formatValue,
    isMapType,
    loadCollapsed,
    loadPinned,
    saveCollapsed,
    savePinned,
    splitFacetId,
    typedValue,
} from '@/components/explorer/facets/facets'

// Left panel of the explorer: top values per column of the last search; click filters, Alt+click excludes.
const props = defineProps(['source', 'searchSeq', 'queryInvalid'])
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

// Facet loads wait for the pins, which come from the server; pin changes wait for them too.
const pinsLoaded = ref(false)
let pinsReady = null
const fetchPins = () => {
    pinsLoaded.value = false
    return (pinsReady = loadPinned(user.value, props.source).then((value) => {
        pinned.value = value
        pinsLoaded.value = true
    }))
}
fetchPins()
// Saves go one at a time, so the server keeps the newest list.
let saving = Promise.resolve()

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
        // A map key reads as the key alone, as on dashboards; the header tooltip keeps the full path.
        const title = key === null ? column : key
        return { id, column, key, kind, title, values: values || [], more: more.has(id) }
    }
    const column = (name) =>
        isMapType(props.source.columns[name]?.type)
            ? group(name, null, 'keys', data.value.map_keys[name])
            : group(name, null, 'value', data.value.facets[name])
    const withKeys = (name) => [
        column(name),
        ...(expandedKeys.value[name] || []).map((key) =>
            group(name, key, 'value', data.value.facets[`${name}.${key}`]),
        ),
    ]
    // Pinned facets first, in pin order (a pinned Map key too), then the other default columns.
    const result = []
    for (const id of pinned.value) {
        const { column: name, key } = splitFacetId(id, props.source.columns)
        if (!(name in props.source.columns)) continue
        if (key === null) result.push(...withKeys(name))
        else result.push(group(name, key, 'value', data.value.facets[id]))
    }
    for (const name of columnIds.value) if (!pinned.value.includes(name)) result.push(...withKeys(name))
    return result.filter((g, i) => result.findIndex((other) => other.id === g.id) === i)
})

// The search keeps groups whose name matches (all values) or that have a matching value (only those).
const search = ref('')
const term = computed(() => search.value.trim().toLowerCase())
const titleMatches = (facet) => `${facet.title} ${facet.id}`.toLowerCase().includes(term.value)
const shownGroups = computed(() =>
    term.value
        ? groups.value.filter(
              (g) =>
                  titleMatches(g) ||
                  g.values.some((v) => String(formatValue(v.value)).toLowerCase().includes(term.value)),
          )
        : groups.value,
)

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
    if (!pinsLoaded.value) return
    const next = pinned.value.includes(id) ? pinned.value.filter((p) => p !== id) : [...pinned.value, id]
    pinned.value = next
    saving = saving.then(async () => {
        const response = await savePinned(props.source, next)
        if (response.result && response.validation?.result !== false) return
        error.value = `Pinned facets not saved: ${response.errors.join(', ') || 'invalid list'}`
        await fetchPins()
    })
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
