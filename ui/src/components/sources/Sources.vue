<template>
    <Content>
        <template #header>
            <ListHeader>
                <template #title>
                    <div class="flex items-center">
                        <Database class="mr-3 w-8 h-8" />
                        Sources
                    </div>
                </template>
                <template #actions>
                    <Button
                        v-if="user.canCreateSource()"
                        size="small"
                        severity="primary"
                        icon="pi pi-plus"
                        label="Create"
                        @click="handleSourceCreate"
                    />
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading, connectionNamesLoading]" :errors="[error, connectionNamesError]">
                <template #loader>
                    <ContentBlock header="Sources" :collapsible="false">
                        <SkeletonList :columns="6" :rows="10" />
                    </ContentBlock>
                </template>
                <ContentBlock :header="`Sources: ${sources.length}`" :collapsible="false">
                    <DataTable
                        :value="sourcesWithConnectionNames"
                        filterDisplay="row"
                        v-model:filters="sourceFilters"
                        sortField="slug"
                        removableSort
                        size="small"
                        :sortOrder="1"
                        :paginator="sources.length > 50"
                        :rows="50"
                        :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                        :row-hover="true"
                    >
                        <Column
                            field="slug"
                            header="Slug"
                            class="w-1 text-nowrap font-medium pl-4"
                            :sortable="true"
                            :showFilterMenu="false"
                        >
                            <template #body="slotProps">
                                <router-link
                                    :to="{ name: 'source', params: { sourceSlug: slotProps.data.slug } }"
                                    class="table-link"
                                >
                                    {{ slotProps.data.slug }}
                                </router-link>
                            </template>
                            <template #filter="{ filterModel, filterCallback }">
                                <InputText
                                    v-model="filterModel.value"
                                    @input="filterCallback()"
                                    placeholder="Filter by slug"
                                    size="small"
                                    fluid
                                    class="min-w-32"
                                />
                            </template>
                        </Column>
                        <Column header="Kind" field="kind" :showFilterMenu="false" :sortable="true" class="w-1">
                            <template #body="slotProps">
                                <div class="flex items-center">
                                    <img
                                        :src="require(`@/assets/${slotProps.data.kind}.png`)"
                                        height="20px"
                                        width="20px"
                                        class="mr-2"
                                        :title="slotProps.data.kind"
                                    />
                                    {{ slotProps.data.kind.charAt(0).toUpperCase() + slotProps.data.kind.slice(1) }}
                                </div>
                            </template>
                            <template #filter="{ filterModel, filterCallback }">
                                <MultiSelect
                                    v-model="filterModel.value"
                                    @change="filterCallback()"
                                    :options="availableKinds"
                                    optionLabel="label"
                                    optionValue="value"
                                    placeholder="Filter by kind..."
                                    :maxSelectedLabels="1"
                                    fluid
                                    size="small"
                                    :showClear="true"
                                    class="min-w-32"
                                >
                                    <template #value="{ value }">
                                        <div v-if="value && value.length > 0" class="flex items-center">
                                            <img
                                                :src="require(`@/assets/${value[0]}.png`)"
                                                height="16px"
                                                width="16px"
                                                class="mr-2"
                                                :title="value[0]"
                                            />
                                            <span v-if="value.length === 1">{{
                                                value[0].charAt(0).toUpperCase() + value[0].slice(1)
                                            }}</span>
                                            <span v-else>{{ value.length }} selected</span>
                                        </div>
                                    </template>
                                    <template #option="{ option }">
                                        <div class="flex items-center">
                                            <img
                                                :src="require(`@/assets/${option.value}.png`)"
                                                height="16px"
                                                width="16px"
                                                class="mr-2"
                                                :title="option.value"
                                            />
                                            {{ option.label }}
                                        </div>
                                    </template>
                                </MultiSelect>
                            </template>
                        </Column>

                        <Column
                            field="name"
                            header="Name"
                            class="w-1 text-nowrap"
                            :sortable="true"
                            :showFilterMenu="false"
                        >
                            <template #filter="{ filterModel, filterCallback }">
                                <InputText
                                    v-model="filterModel.value"
                                    @input="filterCallback()"
                                    placeholder="Filter by name"
                                    size="small"
                                    fluid
                                    class="min-w-32"
                                />
                            </template>
                        </Column>
                        <Column
                            field="connectionName"
                            header="Connection"
                            class="w-1 text-nowrap"
                            :showFilterMenu="false"
                            :sortable="true"
                        >
                            <template #body="slotProps">
                                <router-link
                                    v-if="
                                        slotProps.data.connectionId &&
                                        connectionNames &&
                                        connectionNames[slotProps.data.connectionId]
                                    "
                                    :to="{ name: 'connection', params: { connectionId: slotProps.data.connectionId } }"
                                    class="table-link"
                                >
                                    {{ connectionNames[slotProps.data.connectionId] }}
                                </router-link>
                                <span v-else-if="slotProps.data.connectionId" class="text-gray-400 text-xs italic">
                                    No access
                                </span>
                                <EmptyValue v-else :value="null" :isDark="isDark" />
                            </template>
                            <template #filter="{ filterModel, filterCallback }">
                                <InputText
                                    v-model="filterModel.value"
                                    @input="filterCallback()"
                                    placeholder="Filter by connection"
                                    size="small"
                                    fluid
                                    class="min-w-32"
                                />
                            </template>
                        </Column>
                        <Column field="description" header="Description" :showFilterMenu="false" :sortable="true">
                            <template #body="slotProps">
                                <EmptyValue :value="slotProps.data.description" :isDark="isDark" />
                            </template>
                            <template #filter="{ filterModel, filterCallback }">
                                <InputText
                                    v-model="filterModel.value"
                                    @input="filterCallback()"
                                    placeholder="Filter by description"
                                    size="small"
                                    fluid
                                    class="min-w-40"
                                />
                            </template>
                        </Column>
                        <template #empty>
                            <div
                                class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400"
                            >
                                <i class="pi pi-database text-4xl mb-4 opacity-50"></i>
                                <p class="text-lg font-medium mb-2">No sources found</p>
                            </div>
                        </template>
                    </DataTable>
                </ContentBlock>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDark } from '@vueuse/core'

import { useRouter } from 'vue-router'

import { storeToRefs } from 'pinia'

import { Button, InputText, DataTable, Column, MultiSelect } from 'primevue'
import { FilterMatchMode } from '@primevue/core/api'

import { useAuthStore } from '@/stores/auth'
import { useGetSources } from '@/composables/sources/useSourceService'
import { useGetConnectionNames } from '@/composables/connections/useConnectionService'

import Content from '@/components/common/Content.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import DataView from '@/components/common/DataView.vue'
import EmptyValue from '@/components/common/EmptyValue.vue'
import { Database } from 'lucide-vue-next'
import SkeletonList from '@/components/common/SkeletonList.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'

const router = useRouter()
const isDark = useDark()

const { user } = storeToRefs(useAuthStore())
const { sources, error, loading } = useGetSources()
const { connectionNames, error: connectionNamesError, loading: connectionNamesLoading } = useGetConnectionNames()

const sourceFilters = ref({
    kind: { value: null, matchMode: FilterMatchMode.IN },
    slug: { value: null, matchMode: FilterMatchMode.CONTAINS },
    name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    connectionName: { value: null, matchMode: FilterMatchMode.CONTAINS },
    description: { value: null, matchMode: FilterMatchMode.CONTAINS },
})

const availableKinds = [
    { label: 'Docker', value: 'docker' },
    { label: 'ClickHouse', value: 'clickhouse' },
    { label: 'StarRocks', value: 'starrocks' },
    { label: 'Kubernetes', value: 'kubernetes' },
]

const handleSourceCreate = () => {
    router.push({ name: 'sourceNew' })
}

const getConnectionName = (source) => {
    if (!source.connectionId || !connectionNames.value) return ''
    return connectionNames.value[source.connectionId] || ''
}

const sourcesWithConnectionNames = computed(() => {
    if (!sources.value || !connectionNames.value) return sources.value || []
    return sources.value.map((source) => ({
        ...source,
        connectionName: getConnectionName(source),
    }))
})
</script>
