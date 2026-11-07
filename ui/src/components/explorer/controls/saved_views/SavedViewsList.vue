<template>
    <div class="flex flex-col overflow-y-auto" data-testid="saved-views-list">
        <div class="text-2xl p-4 border-b border-neutral-300 dark:border-neutral-600">
            <i class="pi pi-eye" /> <span class="font-medium">{{ source.name }}</span> source Saved Views
        </div>
        <DataView :loadings="[loading]" :errors="[error]">
            <div class="p-4 w-full flex flex-col gap-2" v-if="savedViews.length > 0">
                <IconField>
                    <InputIcon>
                        <i class="pi pi-filter" />
                    </InputIcon>
                    <InputText
                        placeholder="Filter saved views"
                        v-model="savedViewFilter"
                        :autofocus="true"
                        class="w-full"
                    />
                </IconField>
                <div class="flex items-center gap-2">
                    <ToggleButton
                        v-model="favoritesOnly"
                        onIcon="pi pi-star-fill"
                        offIcon="pi pi-star"
                        onLabel="Favorites"
                        offLabel="Favorites"
                        size="small"
                        data-testid="saved-views-favorites-only"
                    />
                    <Select
                        v-model="tagFilter"
                        :options="allTags"
                        showClear
                        placeholder="Any tag"
                        size="small"
                        class="w-48"
                        data-testid="saved-views-tag-filter"
                    />
                </div>
            </div>
            <DataTable
                rowGroupMode="subheader"
                groupRowsBy="kind"
                :value="savedViewsPrepared"
                removableSort
                paginator
                :rows="25"
                :row-hover="true"
                @rowClick="handleRowClick"
                :showHeaders="false"
                v-if="savedViewsPrepared.length > 0"
            >
                <Column column="name" class="hover:cursor-pointer">
                    <template #body="{ data }">
                        <div class="flex flex-col">
                            <div class="flex flex-row justify-between w-full">
                                <div class="text-nowrap flex items-center gap-2">
                                    <i
                                        :class="
                                            metaFor(data).favorite
                                                ? 'pi pi-star-fill text-amber-500'
                                                : 'pi pi-star text-surface-400'
                                        "
                                        class="hover:text-amber-500"
                                        role="button"
                                        :aria-label="
                                            metaFor(data).favorite ? 'Remove from favorites' : 'Add to favorites'
                                        "
                                        :data-testid="`saved-view-favorite-${data.slug}`"
                                        @click.stop="toggleFavorite(data)"
                                    />
                                    <span
                                        class="text-primary"
                                        :class="{ 'font-bold': currentView?.slug === data.slug }"
                                        v-tooltip.left="data.name.length > 64 ? data.name : ''"
                                        >{{ getShortedValue(data.name) }}</span
                                    >
                                </div>
                                <div class="flex items-center gap-2">
                                    <span
                                        v-if="metaFor(data).alerts.length"
                                        class="text-sm"
                                        :class="
                                            metaFor(data).alerts.some((a) => a.state === 'ALERT')
                                                ? 'text-red-600 dark:text-red-400'
                                                : 'text-surface-500'
                                        "
                                        v-tooltip.left="
                                            metaFor(data)
                                                .alerts.map((a) => `${a.name}: ${a.state}`)
                                                .join('\n')
                                        "
                                        :data-testid="`saved-view-alerts-${data.slug}`"
                                        @click.stop="openAlert(metaFor(data).alerts[0])"
                                        ><i class="pi pi-bell" /> {{ metaFor(data).alerts.length }}</span
                                    >
                                    <span class="text-gray-500" v-if="data.kind === 'shared'">
                                        by {{ data.user.username }}
                                    </span>
                                </div>
                            </div>
                            <div class="flex flex-wrap items-center gap-1 pt-1" @click.stop>
                                <Tag
                                    v-for="t in metaFor(data).tags"
                                    :key="t"
                                    :value="t"
                                    severity="secondary"
                                    class="text-xs"
                                />
                                <InputText
                                    v-if="tagEditing === keyOf(data)"
                                    v-model="tagText"
                                    size="small"
                                    class="w-64"
                                    placeholder="Comma separated, Enter to save"
                                    autofocus
                                    :data-testid="`saved-view-tags-input-${data.slug}`"
                                    @keydown.enter="saveTags(data)"
                                    @keydown.esc="tagEditing = null"
                                />
                                <i
                                    v-else-if="data.isEditable() && metaFor(data).id"
                                    class="pi pi-tag text-surface-400 hover:text-primary text-sm"
                                    role="button"
                                    aria-label="Edit tags"
                                    :data-testid="`saved-view-tags-edit-${data.slug}`"
                                    @click="editTags(data)"
                                />
                            </div>
                            <div class="text-gray-500 dark:text-gray-400 text-sm" v-if="data.description">
                                {{ data.description }}
                            </div>
                            <div class="flex flex-col pt-2" v-if="data.data.columns || data.data.query">
                                <div
                                    class="flex flex-row items-center text-sm text-gray-500 dark:text-gray-400"
                                    v-if="data.data.columns"
                                >
                                    <i class="pi pi-list pr-2" />
                                    <span v-tooltip.left="data.data.columns.length > 64 ? data.data.columns : ''">{{
                                        getShortedValue(data.data.columns)
                                    }}</span>
                                </div>
                                <div
                                    class="flex flex-row items-center text-sm text-gray-500 dark:text-gray-400"
                                    v-if="data.data.query"
                                >
                                    <i class="pi pi-search pr-2" />
                                    <span v-tooltip.left="data.data.query.length > 64 ? data.data.query : ''">{{
                                        getShortedValue(data.data.query)
                                    }}</span>
                                </div>
                            </div>
                        </div>
                    </template>
                </Column>
                <template #groupheader="{ data }">
                    <div class="flex items-center gap-2 text-xl font-medium">
                        <span v-if="data.kind === 'user'"><i class="pi pi-user" /> Your views</span>
                        <span v-else-if="data.kind === 'source'"><i class="pi pi-database" /> Source views</span>
                        <span v-else><i class="pi pi-users" /> Shared views</span>
                    </div>
                </template>
            </DataTable>
            <div v-else-if="savedViewFilter || favoritesOnly || tagFilter" class="pl-4 pr-4 mb-2">
                <Message severity="warn">No saved views match your filter.</Message>
            </div>
            <div v-else class="p-4 mb-2">
                <Message severity="info">You don't have any saved views yet.</Message>
            </div>
        </DataView>
    </div>
</template>
<script setup>
import { useRouter } from 'vue-router'
import { DataTable, Column, IconField, InputIcon, InputText, Message, Select, Tag, ToggleButton } from 'primevue'

import { useGetSavedViews } from '@/composables/sources/useSourceService'

import DataView from '@/components/common/DataView.vue'
import { onMounted, ref, computed } from 'vue'

import Fuse from 'fuse.js'

import { AlertService } from '@/features/alerts/service.js'

const props = defineProps(['source', 'currentView'])
const emit = defineEmits(['change'])
const savedViewFilter = ref('')

const { savedViews, error, loading } = useGetSavedViews(props.source.slug)

// Tags, favorites and alert badges live in the telescope_alerts side table, matched on slug and user.
const router = useRouter()
const alertSrv = new AlertService()
const meta = ref({})
const favoritesOnly = ref(false)
const tagFilter = ref(null)
const tagEditing = ref(null)
const tagText = ref('')
const EMPTY = { id: null, tags: [], favorite: false, alerts: [] }
const keyOf = (view) => `${view.slug}:${view.user?.id ?? ''}`
const metaFor = (view) => meta.value[keyOf(view)] || EMPTY
const allTags = computed(() => [...new Set(Object.values(meta.value).flatMap((m) => m.tags))].sort())
alertSrv.savedViews(props.source.slug).then((r) => {
    if (!r.result) return
    meta.value = Object.fromEntries(Object.values(r.data).map((m) => [`${m.slug}:${m.user_id ?? ''}`, m]))
})
const patch = async (view, data) => {
    const m = metaFor(view)
    if (!m.id) return
    const r = await alertSrv.updateSavedView(props.source.slug, m.id, data)
    if (r.result) meta.value = { ...meta.value, [keyOf(view)]: r.data }
}
const toggleFavorite = (view) => patch(view, { favorite: !metaFor(view).favorite })
const editTags = (view) => {
    tagText.value = metaFor(view).tags.join(', ')
    tagEditing.value = keyOf(view)
}
const saveTags = async (view) => {
    await patch(view, { tags: tagText.value.split(',').map((t) => t.trim()) })
    tagEditing.value = null
}
const openAlert = (alert) => router.push({ name: 'alertDetail', params: { alertId: alert.id } })

const getViewPriority = (view) => {
    if (view.kind === 'user') return 0
    if (view.kind === 'source') return 1
    if (view.kind === 'shared') return 2
    return 3
}

const savedViewsPrepared = computed(() => {
    if (savedViews.value && savedViews.value.length > 0) {
        let views = savedViews.value
        if (savedViewFilter.value) {
            let fuse = new Fuse(views, {
                keys: ['name', 'description', 'data.columns', 'data.query', 'data.limit', 'data.from', 'data.to'],
                threshold: 0.4,
            })
            views = fuse.search(savedViewFilter.value).map((r) => r.item)
        }
        if (favoritesOnly.value) views = views.filter((v) => metaFor(v).favorite)
        if (tagFilter.value) views = views.filter((v) => metaFor(v).tags.includes(tagFilter.value))
        views = views.slice().sort((a, b) => {
            const prioA = getViewPriority(a)
            const prioB = getViewPriority(b)

            if (prioA !== prioB) {
                return prioA - prioB
            }
            const fav = Number(metaFor(b).favorite) - Number(metaFor(a).favorite)
            if (fav) return fav
            return a.name.localeCompare(b.name)
        })
        return views
    } else {
        return savedViews.value
    }
})

const getShortedValue = (value) => {
    return value.length > 64 ? value.slice(0, 61) + '…' : value
}

const handleRowClick = ({ data }) => {
    emit('change', data)
}
</script>
