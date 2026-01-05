<template>
    <div class="flex flex-col overflow-y-auto">
        <div class="text-2xl p-4 border-b border-neutral-300 dark:border-neutral-600">
            <i class="pi pi-eye" /> <span class="font-medium">{{ source.name }}</span> source Saved Views
        </div>
        <DataView :loadings="[loading]" :errors="[error]">
            <div class="p-4 w-full" v-if="savedViews.length > 0">
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
                                <div class="text-nowrap">
                                    <span
                                        class="text-primary"
                                        :class="{ 'font-bold': currentView?.slug === data.slug }"
                                        v-tooltip.left="data.name.length > 64 ? data.name : ''"
                                        >{{ getShortedValue(data.name) }}</span
                                    >
                                </div>
                                <div class="text-gray-500" v-if="data.kind === 'shared'">
                                    by {{ data.user.username }}
                                </div>
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
            <div v-else-if="savedViewFilter" class="pl-4 pr-4 mb-2">
                <Message severity="warn">No saved views match your filter.</Message>
            </div>
            <div v-else class="p-4 mb-2">
                <Message severity="info">You don't have any saved views yet.</Message>
            </div>
        </DataView>
    </div>
</template>
<script setup>
import { DataTable, Column, IconField, InputIcon, InputText, Message } from 'primevue'

import { useGetSavedViews } from '@/composables/sources/useSourceService'

import DataView from '@/components/common/DataView.vue'
import { onMounted, ref, computed } from 'vue'

import Fuse from 'fuse.js'

const props = defineProps(['source', 'currentView'])
const emit = defineEmits(['change'])
const savedViewFilter = ref('')

const { savedViews, error, loading } = useGetSavedViews(props.source.slug)

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
        views = views.slice().sort((a, b) => {
            const prioA = getViewPriority(a)
            const prioB = getViewPriority(b)

            if (prioA !== prioB) {
                return prioA - prioB
            }
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
