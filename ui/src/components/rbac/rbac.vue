<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-wrap justify-start min-w-1280 max-w-1280 gap-2">
            <div class="w-full">
                <div class="flex flex-col w-full mb-14 align-middle">
                    <span class="font-bold text-3xl"
                        ><i class="pi pi-shield text-3xl"></i> Role-Based Access Control</span
                    >
                    <span class="text-gray-400"
                        >Helps manage permissions by assigning roles to users and groups,<br />ensuring efficient and
                        secure access control in your organization</span
                    >
                </div>
            </div>
            <Card
                class="max-w-400 cursor-pointer hover:drop-shadow-md dark:drop-shadow-md dark:hover:drop-shadow-xl"
                @click="handleRolesClick"
            >
                <template #title> <i class="pi pi-key"></i> Roles </template>
                <template #content>
                    Roles determine the access levels and permissions assigned to users, enabling control over actions
                    within your organization
                </template>
            </Card>
            <Card
                class="max-w-400 cursor-pointer hover:drop-shadow-md dark:drop-shadow-md dark:hover:drop-shadow-xl"
                @click="handleGroupsClick"
            >
                <template #title> <i class="pi pi-users"></i> Groups </template>
                <template #content>
                    Groups let you manage permissions and access for teams within your organization more efficiently
                </template>
            </Card>
            <Card
                class="max-w-400 cursor-pointer hover:drop-shadow-md dark:drop-shadow-md dark:hover:drop-shadow-xl"
                @click="handleUsersClick"
            >
                <template #title> <i class="pi pi-user"></i> Users </template>
                <template #content>
                    Users are members of your organization with specific permissions that control their access and
                    actions
                </template>
            </Card>
        </div>
    </div>
</template>
<script setup>
import { useRouter } from 'vue-router'
import { useNavStore } from '@/stores/nav'

import Card from 'primevue/card'

const navStore = useNavStore()
const router = useRouter()

navStore.update([{ label: 'Role-Based Access Control', url: '/rbac', class: 'text-gray-100' }])

const handleRolesClick = () => {
    router.push({ name: 'rbacRoles' })
}
const handleGroupsClick = () => {
    router.push({ name: 'rbacGroups' })
}
const handleUsersClick = () => {
    router.push({ name: 'rbacUsers' })
}
</script>
