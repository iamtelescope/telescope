<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280">
            <DataView :loadings="[loading]" :errors="[error]">
                <div class="flex flex-row mb-14">
                    <div class="flex flex-col justify-start text-nowrap">
                        <span class="font-medium text-3xl">
                            <i class="pi pi-key text-3xl mr-1"></i>
                            <span class="text-gray-400">Roles: </span>
                            {{ role.name }}</span
                        >
                        <span class="text-gray-400"
                            >assigned to {{ role.users }} users and {{ role.groups }} groups</span
                        >
                    </div>
                </div>
                <div class="w-full">
                    <DataRow name="NAME" :value="role.name" />
                    <DataRow name="TYPE" :value="role.type" />
                    <DataRow name="PERMISSIONS">
                        <div class="flex flex-wrap gap-2">
                            <Badge
                                v-for="perm in role.permissions"
                                :key="perm"
                                :value="perm"
                                severity="secondary"
                                size="large"
                            ></Badge>
                        </div>
                    </DataRow>
                </div>
            </DataView>
        </div>
    </div>
</template>

<script setup>
import { watch, ref } from 'vue'

import { useRoute } from 'vue-router'

import { useNavStore } from '@/stores/nav'
import { useGetRole } from '@/composables/rbac/useRoleService'
import Badge from 'primevue/badge'
import DataView from '@/components/common/DataView.vue'
import DataRow from '@/components/common/DataRow.vue'

const navStored = ref(false)
const route = useRoute()
const navStore = useNavStore()

const { role, loading, error } = useGetRole(route.params.roleType, route.params.roleName)

navStore.update([
    { label: 'Role-Based Access Control', url: '/rbac' },
    { label: 'Roles', url: '/rbac/roles' },
])

watch(role, () => {
    if (!navStored.value) {
        navStore.append({ label: role.value.name, url: `/rbac/roles/${role.value.type}/${role.value.name}` })
        navStored.value = true
    }
})
</script>
