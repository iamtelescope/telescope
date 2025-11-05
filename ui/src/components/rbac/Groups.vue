<template>
    <AccessDenied v-if="!hasPermission" message="You don't have permission to access RBAC settings." />
    <Content v-else>
        <template #header>
            <Header>
                <template #title> <Users class="mr-3 w-8 h-8" /> Groups </template>
                <template #actions>
                    <Button
                        size="small"
                        severity="primary"
                        icon="pi pi-plus"
                        label="New Group"
                        @click="handleGroupCreate"
                    />
                </template>
            </Header>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <template #loader>
                    <ContentBlock header="Groups" :collapsible="false">
                        <SkeletonList :columns="3" :rows="10" />
                    </ContentBlock>
                </template>
                <ContentBlock :header="`Groups: ${groups.length}`" :collapsible="false">
                    <DataTable
                        :value="groups"
                        filterDisplay="row"
                        v-model:filters="filters"
                        sortField="name"
                        removableSort
                        size="small"
                        :sortOrder="1"
                        :paginator="groups.length > 50"
                        :rows="50"
                        :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                        :row-hover="true"
                        class="w-full"
                    >
                        <Column
                            field="id"
                            :sortable="true"
                            header="ID"
                            :showFilterMenu="false"
                            class="w-20 pl-4"
                        ></Column>
                        <Column field="name" :sortable="true" header="Name" :showFilterMenu="false">
                            <template #body="{ data }">
                                <router-link
                                    :to="{ name: 'rbacGroup', params: { groupId: data.id } }"
                                    class="table-link"
                                >
                                    {{ data.name }}
                                </router-link>
                            </template>
                            <template #filter="{ filterModel, filterCallback }">
                                <InputText
                                    v-model="filterModel.value"
                                    @input="filterCallback()"
                                    placeholder="Filter by name..."
                                    size="small"
                                    fluid
                                />
                            </template>
                        </Column>
                        <Column field="userCount" :sortable="true" header="Members"></Column>
                        <template #empty>
                            <div
                                class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400"
                            >
                                <Users class="w-10 h-10 mb-4 opacity-50" />
                                <p class="text-lg font-medium mb-2">No groups found</p>
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
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { Users } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

import { FilterMatchMode } from '@primevue/core/api'
import { DataTable, Column, InputText, Button } from 'primevue'

import { useGetGroups } from '@/composables/rbac/useGroupService'

import Content from '@/components/common/Content.vue'
import Header from '@/components/common/Header.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import DataView from '@/components/common/DataView.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import AccessDenied from '@/components/common/AccessDenied.vue'

const { user } = storeToRefs(useAuthStore())

const hasPermission = computed(() => {
    return user.value?.hasAccessToSettings() || false
})

const router = useRouter()

const filters = ref({
    name: { value: null, matchMode: FilterMatchMode.CONTAINS },
})
const { groups, error, loading } = useGetGroups()

const handleGroupCreate = () => {
    router.push({ name: 'rbacGroupNew' })
}
</script>
