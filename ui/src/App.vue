<template>
    <Toast class="break-all" position="top-center" />
    <div class="flex flex-row w-full h-full overflow-hidden">
        <Sidebar :collapsed="sidebarCollapsed" @toggle-collapse="sidebarCollapsed = !sidebarCollapsed" />
        <div class="flex flex-col flex-1 h-full min-w-0">
            <div class="overflow-auto">
                <router-view />
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue'

import { Toast } from 'primevue'
import Sidebar from '@/components/common/Sidebar.vue'

const getStoredCollapsedState = () => {
    const stored = localStorage.getItem('sidebarCollapsed')
    return stored !== null ? JSON.parse(stored) : false
}

const sidebarCollapsed = ref(getStoredCollapsedState())

watch(sidebarCollapsed, (newValue) => {
    localStorage.setItem('sidebarCollapsed', JSON.stringify(newValue))
})
</script>
