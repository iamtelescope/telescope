<template>
    <a href="#main-content" class="skip-link">Skip to content</a>
    <Toast class="break-words" position="bottom-right" />
    <ConfirmDialog group="app" class="max-w-[480px]" />
    <CommandPalette />
    <ShortcutsDialog />
    <div class="flex flex-row w-full h-full overflow-hidden">
        <Sidebar :collapsed="sidebarCollapsed" @toggle-collapse="sidebarCollapsed = !sidebarCollapsed" />
        <main id="main-content" tabindex="-1" class="flex flex-col flex-1 h-full min-w-0 outline-none">
            <div class="overflow-auto">
                <router-view v-slot="{ Component, route }">
                    <!-- A new dashboard slug gets a fresh DashboardView instead of a reused one. -->
                    <component :is="Component" :key="route.name === 'dashboard' ? route.path : undefined" />
                </router-view>
            </div>
        </main>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useEventListener } from '@vueuse/core'

import { ConfirmDialog, Toast } from 'primevue'
import Sidebar from '@/components/common/Sidebar.vue'
import CommandPalette from '@/components/common/CommandPalette.vue'
import ShortcutsDialog from '@/components/common/ShortcutsDialog.vue'
import { shell, isTypingTarget } from '@/components/common/shell'

const getStoredCollapsedState = () => {
    try {
        const stored = localStorage.getItem('sidebarCollapsed')
        return stored !== null ? JSON.parse(stored) : false
    } catch {
        return false
    }
}

const sidebarCollapsed = ref(getStoredCollapsedState())

watch(sidebarCollapsed, (newValue) => {
    localStorage.setItem('sidebarCollapsed', JSON.stringify(newValue))
})

// Cmd/Ctrl+K opens the palette anywhere but a code editor; "?" opens the shortcut list outside text fields.
useEventListener(document, 'keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && !e.altKey && e.key.toLowerCase() === 'k') {
        if (e.target?.closest?.('.monaco-editor')) return
        e.preventDefault()
        shell.shortcutsOpen = false
        shell.paletteOpen = !shell.paletteOpen
    } else if (e.key === '?' && !e.metaKey && !e.ctrlKey && !isTypingTarget(e.target)) {
        e.preventDefault()
        shell.shortcutsOpen = true
    }
})
</script>

<style>
.skip-link {
    position: fixed;
    left: 0.5rem;
    top: -3rem;
    z-index: 2000;
    padding: 0.5rem 0.75rem;
    border-radius: 0.375rem;
    background: var(--p-primary-700);
    color: #fff;
}
.skip-link:focus {
    top: 0.5rem;
}
</style>
