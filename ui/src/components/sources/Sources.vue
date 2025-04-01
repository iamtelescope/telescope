<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280 max-w-1280">
            <div class="w-full">
                <div class="flex flex-row w-full mb-14 align-middle">
                    <div class="flex flex-col w-full">
                        <span class="font-bold text-3xl"><i class="pi pi-database text-3xl"></i> Sources</span>
                        <span class="text-gray-400">Sources define how to connect to your data and the access policy for
                            that data.
                        </span>
                    </div>
                    <div v-if="user.canCreateSource()" class="flex items-center w-full justify-end">
                        <Button size="small" severity="primary" icon="pi pi-plus" label="Create"
                            @click="handleSourceCreate" />
                    </div>
                </div>
                <div class="mb-9">
                    <InputText placeholder="Filter by slug or name" v-model="sourceFilters.global.value" fluid
                        class="placeholder-gray-300" />
                </div>
                <DataView :loading="loading" :error="error">
                    <DataTable :value="filteredSources" removableSort class="hover:cursor-pointer" :row-hover="true"
                        v-model:filters="sourceFilters" @row-click="handleRowClick">
                        <Column header="Kind" sortable field="kind" bodyClass="w-40">
                            <template #body="slotProps">
                                <div class="flex flex-row items-center">
                                    <div class="pr-2">
                                        <img :src="require(`@/assets/${slotProps.data.kind}.png`)" height="24px"
                                            width="24px">
                                    </div>
                                    <div>
                                        {{ slotProps.data.kind }}
                                    </div>
                                </div>
                            </template>
                        </Column>
                        <Column field="name" header="Name" class="w-1 text-nowrap font-bold" sortable></Column>
                        <Column field="slug" header="Slug" class="w-1 text-nowrap text-gray-500" sortable></Column>
                        <Column field="description" header="Description" sortable></Column>
                        <Column>
                            <template #body="slotProps">
                                <div class="flex flex-row justify-end">
                                    <Button v-if="slotProps.data.isEditable()" type="button" severity="secondary"
                                        icon="pi pi-cog" label="Manage" size="small"
                                        @click.stop="handleSourceViewClick(slotProps.data)" />
                                    <Button v-else-if="slotProps.data.isReadable()" type="button" severity="secondary"
                                        icon="pi pi-eye" label="View" size="small"
                                        @click.stop="handleSourceViewClick(slotProps.data)" />
                                </div>
                            </template>
                        </Column>
                    </DataTable>
                </DataView>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'

import { useRouter } from 'vue-router'

import { storeToRefs } from 'pinia'

import { Button, InputText, DataTable, Column } from 'primevue'
import { FilterMatchMode } from '@primevue/core/api'

import { useNavStore } from '@/stores/nav'
import { useAuthStore } from '@/stores/auth'
import { useGetSources } from '@/composables/sources/useSourceService'

import DataView from '@/components/common/DataView'

const router = useRouter()
const navStore = useNavStore()
const filterValue = ref('')

const { user } = storeToRefs(useAuthStore())
const { sources, error, loading } = useGetSources()

const filteredSources = computed(() => {
    return sources.value.filter((source) => source.name.includes(filterValue.value) || source.slug.includes(filterValue.value))
})

const sourceFilters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
})

const handleRowClick = (event) => {
    let source = event.data
    router.push({ name: 'explore', params: { sourceSlug: source.slug, source: source } })
}

const handleSourceCreate = () => {
    router.push({ name: 'sourceNew' })
}

const handleSourceViewClick = (source) => {
    router.push({ name: 'source', params: { sourceSlug: source.slug } })
}

navStore.update([
    {
        icon: 'pi pi-database',
        label: 'Sources',
        url: '/',
    },
])
</script>