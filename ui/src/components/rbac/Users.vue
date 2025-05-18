<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280 max-w-1280">
            <div class="w-full">
                <div class="flex flex-row w-full mb-14 align-middle">
                    <div class="flex flex-col w-full">
                        <span class="font-medium text-3xl"><i class="pi pi-user text-3xl"></i> Users</span>
                        <span class="text-gray-400"
                            >Users are members of your organization with specific permissions that control their access
                            and actions</span
                        >
                    </div>
                </div>
                <div class="mb-6">
                    <InputText
                        placeholder="Filter by username"
                        v-model="filters.global.value"
                        fluid
                        class="placeholder-gray-300"
                    />
                </div>
                <DataView :loadings="[loading]" :errors="[error]">
                    <DataTable
                        :value="users"
                        v-model:filters="filters"
                        sortField="username"
                        :sortOrder="1"
                        paginator
                        :rows="20"
                        removableSort
                    >
                        <Column field="isActive" sortable header="Is active" class="font-medium"></Column>
                        <Column field="username" sortable header="Username" class="font-medium"></Column>
                        <Column field="displayFirstName" sortable header="First name" class="text-nowrap"></Column>
                        <Column field="displayLastName" sortable header="Last name" class="text-nowrap"></Column>
                        <Column field="displayLastLogin" sortable header="Last login" class="text-nowrap"></Column>
                        <Column field="displayGroups" sortable header="Groups" class="w-1/2">
                            <template #body="slotProps">
                                <div class="flex flex-wrap gap-2">
                                    <Badge
                                        v-for="group in slotProps.data.sortedGroups"
                                        :key="group.name"
                                        :value="group.name"
                                        severity="secondary"
                                        size="large"
                                    ></Badge>
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
import { ref } from 'vue'
import { FilterMatchMode } from '@primevue/core/api'
import InputText from 'primevue/inputtext'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { Badge } from 'primevue'

import { useNavStore } from '@/stores/nav'
import DataView from '@/components/common/DataView.vue'

import { useGetUsers } from '@/composables/rbac/useUserService'

const navStore = useNavStore()
const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
})
navStore.update([
    { label: 'Role-Based Access Control', url: '/rbac' },
    { label: 'Users', url: '/rbac/users' },
])

const { users, error, loading } = useGetUsers()
</script>
