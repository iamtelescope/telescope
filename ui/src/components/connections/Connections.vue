<template>
    <Content>
        <template #header>
            <Header>
                <template #title> <Cable class="mr-3 w-8 h-8" />Connections </template>
                <template #actions>
                    <Button
                        v-if="user.canCreateConnection()"
                        size="small"
                        severity="primary"
                        icon="pi pi-plus"
                        label="Create"
                        @click="handleConnectionCreate"
                    />
                </template>
            </Header>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <template #loader>
                    <ContentBlock header="Connections" :collapsible="false">
                        <SkeletonList :columns="6" :rows="10" />
                    </ContentBlock>
                </template>
                <ContentBlock :header="`Connections: ${connections.length}`" :collapsible="false">
                    <DataTable
                        :value="connections"
                        filterDisplay="row"
                        v-model:filters="connectionFilters"
                        sortField="name"
                        removableSort
                        size="small"
                        :sortOrder="1"
                        :paginator="connections.length > 50"
                        :rows="50"
                        :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                        :row-hover="true"
                    >
                        <Column
                            header="ID"
                            field="id"
                            :sortable="true"
                            class="w-1 text-nowrap pl-4"
                            :showFilterMenu="false"
                        >
                            <template #body="slotProps">
                                <span class="font-mono text-sm text-gray-600 dark:text-gray-400">
                                    {{ slotProps.data.id }}
                                </span>
                            </template>
                        </Column>
                        <Column
                            field="name"
                            header="Name"
                            class="w-1 text-nowrap font-medium"
                            :sortable="true"
                            :showFilterMenu="false"
                        >
                            <template #body="slotProps">
                                <router-link
                                    :to="{ name: 'connection', params: { connectionId: slotProps.data.id } }"
                                    class="table-link"
                                >
                                    {{ slotProps.data.name }}
                                </router-link>
                            </template>
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
                        <Column header="Kind" field="kind" :sortable="true" :showFilterMenu="false" class="w-1">
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
                        <Column field="description" header="Description" :sortable="true" :showFilterMenu="false">
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
                        <Column field="createdAt" header="Created" sortable class="w-1 text-nowrap">
                            <template #body="slotProps">
                                <DateTimeFormatted :value="slotProps.data.createdAt" />
                            </template>
                        </Column>
                        <Column field="updatedAt" header="Updated" sortable class="w-1 text-nowrap">
                            <template #body="slotProps">
                                <DateTimeFormatted :value="slotProps.data.updatedAt" />
                            </template>
                        </Column>
                        <template #empty>
                            <div
                                class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400"
                            >
                                <i class="pi pi-link text-4xl mb-4 opacity-50"></i>
                                <p class="text-lg font-medium mb-2">No connections found</p>
                            </div>
                        </template>
                    </DataTable>
                </ContentBlock>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
import { ref } from 'vue'
import { Cable } from 'lucide-vue-next'
import { useDark } from '@vueuse/core'

import { useRouter } from 'vue-router'

import { storeToRefs } from 'pinia'

import { Button, InputText, DataTable, Column, MultiSelect } from 'primevue'
import { FilterMatchMode } from '@primevue/core/api'

import { useAuthStore } from '@/stores/auth'
import { useGetConnections } from '@/composables/connections/useConnectionService'

import Content from '@/components/common/Content.vue'
import Header from '@/components/common/Header.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import DataView from '@/components/common/DataView.vue'
import DateTimeFormatted from '@/components/common/DateTimeFormatted.vue'
import EmptyValue from '@/components/common/EmptyValue.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'

const router = useRouter()
const isDark = useDark()

const { user } = storeToRefs(useAuthStore())
const { connections, error, loading } = useGetConnections()

const connectionFilters = ref({
    kind: { value: null, matchMode: FilterMatchMode.IN },
    name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    description: { value: null, matchMode: FilterMatchMode.CONTAINS },
})

const availableKinds = [
    { label: 'Docker', value: 'docker' },
    { label: 'ClickHouse', value: 'clickhouse' },
    { label: 'Kubernetes', value: 'kubernetes' },
]

const handleConnectionCreate = () => {
    router.push({ name: 'connectionNew' })
}
</script>
