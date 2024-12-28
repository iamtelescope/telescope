<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280 max-w-1280">
            <div class="w-full">
                <div class="flex flex-row w-full mb-14 align-middle">
                    <div class="flex flex-col w-full">
                        <span class="font-bold text-3xl"><i class="pi pi-database text-3xl"></i> Sources</span>
                        <span class="text-gray-400">Sources define where logs are accessed for reading
                            and searching within your system</span>
                    </div>
                    <div v-if="user.canCreateSource()" class="flex items-center w-full justify-end">
                        <Button size="small" severity="primary" icon="pi pi-plus" label="Create" @click="handleSourceCreate" />
                    </div>
                </div>
                <div class="mb-9">
                    <InputText placeholder="Filter by slug or name" v-model="filterValue" fluid class="placeholder-gray-300" />
                </div>
                <DataView :loading="loading" :error="error">
                    <div class="flex flex-wrap w-full gap-2">
                        <Card v-for="(source, index) in filteredSources" :key="index" @click="handleSourceClick(source)"
                            class="max-w-400 min-w-400 cursor-pointer hover:drop-shadow-md"
                            style="max-width:420px;min-width:420px;">
                            <template #title>
                                <div class="flex flex-row items-start">
                                    <img src="@/assets/clickhouse.png" class="mr-3" height="24px" width="24px">
                                    <div class="flex flex-col w-full">
                                        <span>{{ source.name }}</span>
                                        <span class="text-gray-500 text-sm">{{ source.slug }}</span>
                                    </div>
                                    <div class="flex justify-end">
                                        <Button v-if="source.isEditable()" type="button" severity="secondary" icon="pi pi-cog" label="Manage" size="small"
                                            @click.stop="handleSourceViewClick(source)" />
                                    </div>
                                </div>
                            </template>
                            <template #content>
                                <div class="flex flex-row items-center">
                                    <div style="width: 24px; height:24px;" class="mr-3"></div>
                                    <span>{{ source.description }}</span>
                                </div>
                            </template>
                        </Card>
                    </div>
                </DataView>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'

import { useRouter } from 'vue-router'

import { storeToRefs } from 'pinia'

import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'

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

const handleSourceClick = (source) => {
    router.push({ name: 'logs', params: { sourceSlug: source.slug, source: source } })
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