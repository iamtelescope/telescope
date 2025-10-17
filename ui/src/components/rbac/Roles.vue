<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280 max-w-1280">
            <div class="w-full">
                <div class="flex flex-row w-full mb-14 align-middle">
                    <div class="flex flex-col w-full">
                        <span class="font-medium text-3xl"><i class="pi pi-key text-3xl"></i> Roles</span>
                        <span class="text-gray-400"
                            >Roles determine the access levels and permissions assigned to users, enabling control over
                            actions within your organization</span
                        >
                    </div>
                </div>
                <DataView :loadings="[loading]" :errors="[error]">
                    <DataTable :value="roles" :row-hover="true" @row-click="handleRowClick" class="cursor-pointer">
                        <Column field="name" sortable header="NAME" class="font-medium"></Column>
                        <Column field="type" sortable header="TYPE"></Column>
                        <Column field="users" header="USERS"></Column>
                        <Column field="groups" header="GROUPS"></Column>
                    </DataTable>
                </DataView>
            </div>
        </div>
    </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { useNavStore } from '@/stores/nav'
import DataView from '@/components/common/DataView.vue'
import { useGetRoles } from '@/composables/rbac/useRoleService'

const router = useRouter()
const navStore = useNavStore()
navStore.update([
    { label: 'Role-Based Access Control', url: 'rbac' },
    { label: 'Roles', url: 'rbac/roles' },
])

const { roles, error, loading } = useGetRoles()

const handleRowClick = (event) => {
    let role = event.data
    router.push({ name: 'rbacRole', params: { roleType: role.type, roleName: role.name } })
}
</script>
