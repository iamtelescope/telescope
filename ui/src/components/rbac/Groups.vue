<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280">
            <div class="w-full">
                <div class="flex flex-row w-full mb-14 align-middle">
                    <div class="flex flex-col w-full">
                        <span class="font-bold text-3xl"><i class="pi pi-users text-3xl"></i> Groups</span>
                        <span class="text-gray-400">Groups let you manage permissions and access for teams within your
                            organization more efficiently</span>
                    </div>
                    <div class="flex items-center w-full justify-end">
                        <Button size="small" severity="primary" icon="pi pi-plus" label="Create" @click="handleGroupCreate" />
                    </div>
                </div>
                <div class="mb-6">
                    <InputText placeholder="Filter by group name" v-model="filters.global.value" fluid
                        class="placeholder-gray-300" />
                </div>
                <DataView :loading="loading" :error="error">
                    <div class="flex flex-row w-full mt-5">
                        <DataTable v-if="groups.length" :value="groups" v-model:filters="filters" sortField="name" removableSort
                            :sortOrder="1" paginator :rows="20" :row-hover="true"
                            @row-click="handleRowClick" class="w-full cursor-pointer">
                            <Column field="name" sortable header="NAME"></Column>
                            <Column field="userCount" sortable header="MEMBERS"></Column>
                        </DataTable>
                        <div v-else>There is no groups</div>
                    </div>
                </DataView>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { FilterMatchMode } from '@primevue/core/api';
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

import { useNavStore } from '@/stores/nav'
import DataView from '@/components/common/DataView'
import { useGetGroups } from '@/composables/rbac/useGroupService';

const navStore = useNavStore()
const router = useRouter()

const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
})
const { groups, error, loading } = useGetGroups()

navStore.update([
    { label: 'Role-Based Access Control', url: '/rbac' },
    { label: 'Groups', url: '/rbac/groups' },
])

const handleGroupCreate = () => {
    router.push({ name: 'rbacGroupNew' })
}

const handleRowClick = (event) => {
    let group = event.data
    router.push({ name: 'rbacGroup', params: { groupId: group.id } })
}
</script>