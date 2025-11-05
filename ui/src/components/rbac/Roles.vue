<template>
    <AccessDenied v-if="!hasPermission" message="You don't have permission to access RBAC settings." />
    <Content v-else>
        <template #header>
            <ListHeader>
                <template #title>
                    <div class="flex items-center">
                        <Key class="mr-3 w-8 h-8" />
                        Roles
                    </div>
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <template #loader>
                    <ContentBlock header="Roles" :collapsible="false">
                        <SkeletonList :columns="3" :rows="10" />
                    </ContentBlock>
                </template>
                <ContentBlock :header="`Roles: ${roles.length}`" :collapsible="false">
                    <DataTable
                        :value="roles"
                        sortField="name"
                        removableSort
                        size="small"
                        :sortOrder="1"
                        :paginator="roles.length > 50"
                        :rows="50"
                        :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                        :row-hover="true"
                        class="w-full"
                    >
                        <Column field="name" :sortable="true" header="Name" class="pl-4">
                            <template #body="{ data }">
                                {{ data.name }}
                            </template>
                        </Column>
                        <Column field="type" :sortable="true" header="Type"></Column>
                        <Column field="permissions" header="Permissions">
                            <template #body="{ data }">
                                <div class="flex flex-wrap gap-2">
                                    <Tag
                                        v-for="perm in data.permissions"
                                        :key="perm"
                                        :value="perm"
                                        severity="secondary"
                                    ></Tag>
                                </div>
                            </template>
                        </Column>
                        <template #empty>
                            <div
                                class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400"
                            >
                                <Key class="w-10 h-10 mb-4 opacity-50" />
                                <p class="text-lg font-medium mb-2">No roles found</p>
                            </div>
                        </template>
                    </DataTable>
                </ContentBlock>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { Key } from 'lucide-vue-next'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import Content from '@/components/common/Content.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import DataView from '@/components/common/DataView.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import Tag from '@/components/common/Tag.vue'
import AccessDenied from '@/components/common/AccessDenied.vue'
import { useGetRoles } from '@/composables/rbac/useRoleService'

const { user } = storeToRefs(useAuthStore())

const hasPermission = computed(() => {
    return user.value?.hasAccessToSettings() || false
})

const { roles, error, loading } = useGetRoles()
</script>
