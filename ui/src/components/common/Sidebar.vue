<template>
    <div
        class="flex flex-col h-full transition-all duration-300 relative overflow-hidden text-gray-300 bg-gradient-to-b from-primary-800 to-primary-950"
        :class="collapsed ? 'w-16' : 'w-64'"
    >
        <div
            class="fixed top-0 z-10 flex flex-row items-center justify-between min-h-[50px] h-[50px] max-h-[50px] transition-all duration-300 overflow-x-hidden bg-primary-800"
            :class="collapsed ? 'w-16' : 'w-64'"
        >
            <router-link to="/" class="flex items-center pl-3 hover:opacity-80 transition-opacity text-white">
                <img src="@/assets/logo.png" alt="telescope" height="29px" width="29px" />
                <span
                    class="pl-2.5 text-xl font-medium transition-opacity duration-300"
                    :class="collapsed ? 'opacity-0' : 'opacity-100'"
                    >Telescope</span
                >
            </router-link>

            <div class="pr-4 transition-opacity duration-300" :class="collapsed ? 'opacity-0' : 'opacity-100'">
                <button
                    class="flex items-center justify-center w-10 h-10 rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                    @click="$emit('toggle-collapse')"
                    title="Collapse Panel"
                    :disabled="collapsed"
                >
                    <PanelLeftClose :size="20" :stroke-width="1.5" />
                </button>
            </div>
        </div>

        <div
            class="flex justify-center py-4 transition-opacity duration-300"
            :class="collapsed ? 'opacity-100' : 'opacity-0'"
            :style="{ marginTop: '50px', paddingTop: '1rem' }"
        >
            <button
                class="flex items-center justify-center w-10 h-10 rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                @click="$emit('toggle-collapse')"
                title="Expand Panel"
                :disabled="!collapsed"
            >
                <PanelLeftOpen :size="20" :stroke-width="1.5" />
            </button>
        </div>

        <div
            v-if="!collapsed"
            class="flex flex-col w-full flex-1 overflow-y-auto overflow-x-hidden"
            :style="{ paddingTop: '50px' }"
        >
            <div class="pl-4 py-3 text-base font-semibold text-gray-300">
                <span class="transition-opacity duration-300">Explore</span>
            </div>
            <router-link
                to="/"
                class="flex items-center ml-2 mr-4 px-3 py-2 mb-2 text-base rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name === 'root' || $route.name === 'explore' }"
            >
                <ScrollText class="mr-3 w-4 h-4" />
                <span class="transition-opacity duration-300">Logs</span>
            </router-link>

            <div class="pl-4 py-3 text-base font-semibold text-gray-300 mt-4">Data</div>
            <router-link
                to="/connections"
                class="flex items-center ml-2 mr-3 px-3 py-2 mb-2 text-base rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name?.startsWith('connection') }"
            >
                <Cable class="mr-3 w-4 h-4" />
                Connections
            </router-link>
            <router-link
                to="/sources"
                class="flex items-center ml-2 mr-3 px-3 py-2 mb-2 text-base rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{
                    'bg-black bg-opacity-30':
                        $route.name === 'sources' ||
                        $route.name === 'source' ||
                        $route.name === 'sourceEdit' ||
                        $route.name === 'sourceNew',
                }"
            >
                <i class="pi pi-database mr-3 text-lg"></i>
                Sources
            </router-link>

            <div v-if="user.hasAccessToSettings()" class="pl-4 py-3 text-base font-semibold text-gray-300 mt-4">
                Administration
            </div>
            <router-link
                v-if="user.hasAccessToSettings()"
                to="/rbac/users"
                class="flex items-center ml-2 mr-3 px-3 py-2 mb-2 text-base rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name === 'rbacUsers' }"
            >
                <i class="pi pi-users mr-3 text-lg"></i>
                Users
            </router-link>
            <router-link
                v-if="user.hasAccessToSettings()"
                to="/rbac/groups"
                class="flex items-center ml-2 mr-3 px-3 py-2 mb-2 text-base rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name?.startsWith('rbacGroup') }"
            >
                <i class="pi pi-user-plus mr-3 text-lg"></i>
                Groups
            </router-link>
            <router-link
                v-if="user.hasAccessToSettings()"
                to="/rbac/roles"
                class="flex items-center ml-2 mr-3 px-3 py-2 mb-2 text-base rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name?.startsWith('rbacRole') }"
            >
                <i class="pi pi-key mr-3 text-lg"></i>
                Roles
            </router-link>
        </div>

        <div
            v-else
            class="flex flex-col items-center w-16 max-w-16 overflow-x-hidden flex-1 overflow-y-auto"
            :style="{ paddingTop: '50px' }"
        >
            <div class="py-3 text-base font-semibold text-gray-300 opacity-0 pointer-events-none">
                <span>Explore</span>
            </div>
            <router-link
                to="/"
                class="flex items-center justify-center w-10 h-10 mb-2 rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name === 'root' || $route.name === 'explore' }"
                title="Logs"
            >
                <ScrollText class="w-4 h-4" />
            </router-link>

            <!-- Invisible Data Section Header for height consistency -->
            <div class="py-3 text-base font-semibold text-gray-300 mt-4 opacity-0 pointer-events-none">Data</div>
            <router-link
                to="/connections"
                class="flex items-center justify-center w-10 h-10 mb-2 rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name?.startsWith('connection') }"
                title="Connections"
            >
                <Cable class="w-4 h-4" />
            </router-link>
            <router-link
                to="/sources"
                class="flex items-center justify-center w-10 h-10 mb-2 rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{
                    'bg-black bg-opacity-30':
                        $route.name === 'sources' ||
                        $route.name === 'source' ||
                        $route.name === 'sourceEdit' ||
                        $route.name === 'sourceNew',
                }"
                title="Sources"
            >
                <i class="pi pi-database text-lg"></i>
            </router-link>

            <!-- Invisible Administration Section Header for height consistency -->
            <div
                v-if="user.hasAccessToSettings()"
                class="py-3 text-base font-semibold text-gray-300 mt-4 opacity-0 pointer-events-none"
            >
                Administration
            </div>
            <router-link
                v-if="user.hasAccessToSettings()"
                to="/rbac/users"
                class="flex items-center justify-center w-10 h-10 mb-2 rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name === 'rbacUsers' }"
                title="Users"
            >
                <i class="pi pi-users text-lg"></i>
            </router-link>
            <router-link
                v-if="user.hasAccessToSettings()"
                to="/rbac/groups"
                class="flex items-center justify-center w-10 h-10 mb-2 rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name?.startsWith('rbacGroup') }"
                title="Groups"
            >
                <i class="pi pi-user-plus text-lg"></i>
            </router-link>
            <router-link
                v-if="user.hasAccessToSettings()"
                to="/rbac/roles"
                class="flex items-center justify-center w-10 h-10 mb-2 rounded text-gray-300 hover:bg-white hover:bg-opacity-30"
                :class="{ 'bg-black bg-opacity-30': $route.name?.startsWith('rbacRole') }"
                title="Roles"
            >
                <i class="pi pi-key text-lg"></i>
            </router-link>
        </div>

        <!-- Buttons -->
        <div v-if="!collapsed">
            <div class="p-4 flex flex-col gap-2">
                <Button
                    v-if="configStore.config.show_github_url"
                    icon="pi pi-github"
                    outlined
                    severity="contrast"
                    size="small"
                    as="a"
                    :href="configStore.config.github_url"
                    target="_blank"
                    rel="noopener"
                    label="GitHub"
                    class="hover:bg-white hover:bg-opacity-30"
                    style="border-color: var(--p-primary-700); color: rgb(209 213 219)"
                ></Button>
                <Button
                    v-if="configStore.config.show_docs_url"
                    icon="pi pi-book"
                    outlined
                    severity="contrast"
                    size="small"
                    as="a"
                    :href="configStore.config.docs_url"
                    target="_blank"
                    rel="noopener"
                    label="Docs"
                    class="hover:bg-white hover:bg-opacity-30"
                    style="border-color: var(--p-primary-700); color: rgb(209 213 219)"
                ></Button>
                <Button
                    :icon="themeIcon"
                    outlined
                    severity="contrast"
                    size="small"
                    :label="isDark ? 'Light' : 'Dark'"
                    @click="toggleDark()"
                    class="hover:bg-white hover:bg-opacity-30"
                    style="border-color: var(--p-primary-700); color: rgb(209 213 219)"
                ></Button>
            </div>
        </div>

        <!-- User Info -->
        <div v-if="!collapsed">
            <div class="p-4">
                <div
                    v-if="user.avatarUrl"
                    class="flex flex-row items-center cursor-pointer hover:bg-white hover:bg-opacity-30 rounded p-2 -m-2"
                    :class="{ 'bg-black bg-opacity-30': $route.name === 'userProfile' }"
                    @click="router.push('/profile')"
                    title="Profile"
                >
                    <Avatar
                        :image="user.avatarUrl"
                        class="avaimg"
                        style="color: rgb(209 213 219); background-color: var(--p-primary-700)"
                    />
                    <div class="ml-3 flex-1">
                        <div class="font-medium text-sm" v-tooltip.right="usernameTooltip">
                            {{ displayUsername }}
                        </div>
                        <div class="text-xs text-gray-400 flex items-center">
                            <i v-if="user.type == 'github'" class="pi pi-github mr-1"></i>
                            {{ user.type }}
                        </div>
                    </div>
                </div>
                <div
                    v-else
                    class="flex flex-row items-center cursor-pointer hover:bg-white hover:bg-opacity-30 rounded p-2 -m-2"
                    :class="{ 'bg-black bg-opacity-30': $route.name === 'userProfile' }"
                    @click="router.push('/profile')"
                    title="Profile"
                >
                    <Avatar icon="pi pi-user" style="color: rgb(209 213 219); background-color: var(--p-primary-700)" />
                    <div class="ml-3 flex-1">
                        <div class="font-medium text-sm" v-tooltip.right="usernameTooltip">
                            {{ displayUsername }}
                        </div>
                        <div class="text-xs text-gray-400 flex items-center">
                            <i v-if="user.type == 'github'" class="pi pi-github mr-1"></i>
                            {{ user.type }}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Collapsed Bottom Section -->
        <div class="p-2 flex flex-col items-center gap-2" v-else>
            <Button
                v-if="configStore.config.show_github_url"
                icon="pi pi-github"
                outlined
                severity="contrast"
                size="small"
                as="a"
                :href="configStore.config.github_url"
                target="_blank"
                rel="noopener"
                title="GitHub"
                class="hover:bg-white hover:bg-opacity-30"
                style="border-color: var(--p-primary-500); color: rgb(209 213 219)"
            ></Button>
            <Button
                v-if="configStore.config.show_docs_url"
                icon="pi pi-book"
                outlined
                severity="contrast"
                size="small"
                as="a"
                :href="configStore.config.docs_url"
                target="_blank"
                rel="noopener"
                title="Docs"
                class="hover:bg-white hover:bg-opacity-30"
                style="border-color: var(--p-primary-500); color: rgb(209 213 219)"
            ></Button>
            <Button
                :icon="themeIcon"
                outlined
                severity="contrast"
                size="small"
                @click="toggleDark()"
                class="hover:bg-white hover:bg-opacity-30"
                :title="isDark ? 'Switch to Light' : 'Switch to Dark'"
                style="border-color: var(--p-primary-500); color: rgb(209 213 219)"
            ></Button>
            <div class="rounded p-1 -m-1" :class="{ 'bg-black bg-opacity-30': $route.name === 'userProfile' }">
                <Avatar
                    :image="user.avatarUrl"
                    :icon="user.avatarUrl ? null : 'pi pi-user'"
                    size="small"
                    class="cursor-pointer"
                    @click="router.push('/profile')"
                    title="Profile"
                    style="color: rgb(209 213 219); background-color: var(--p-primary-700)"
                />
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Avatar, Button } from 'primevue'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { useDark, useToggle } from '@vueuse/core'
import { PanelLeftOpen, PanelLeftClose, Cable, ScrollText } from 'lucide-vue-next'

defineProps(['collapsed'])

defineEmits(['toggle-collapse'])

const router = useRouter()
const configStore = useConfigStore()
configStore.load()
const { user } = storeToRefs(useAuthStore())

const isDark = useDark()

// Truncate username if longer than 20 characters
const displayUsername = computed(() => {
    if (!user.value?.username) return ''
    return user.value.username.length > 20 ? user.value.username.substring(0, 20) + '...' : user.value.username
})

// Show tooltip only if username is truncated
const usernameTooltip = computed(() => {
    return user.value?.username?.length > 20 ? user.value.username : null
})
const toggleDark = useToggle(isDark)

const themeIcon = computed(() => {
    if (isDark.value) {
        return 'pi pi-sun'
    } else {
        return 'pi pi-moon'
    }
})
</script>
