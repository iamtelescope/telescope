<template>
    <nav
        aria-label="Main navigation"
        class="sidebar flex flex-col h-full shrink-0 transition-[width] duration-200 overflow-hidden text-gray-300 bg-gradient-to-b from-primary-800 to-primary-950"
        :class="collapsed ? 'w-16' : 'w-64'"
    >
        <div
            class="flex items-center h-[50px] min-h-[50px] bg-primary-800"
            :class="collapsed ? 'justify-center' : 'px-3'"
        >
            <router-link
                to="/"
                class="flex items-center rounded-md text-white hover:opacity-80"
                aria-label="Telescope home"
            >
                <img src="@/assets/logo.png" alt="" height="29" width="29" />
                <span v-if="!collapsed" class="pl-2.5 text-xl font-medium">Telescope</span>
            </router-link>
            <button
                v-if="!collapsed"
                class="ml-auto flex items-center justify-center w-8 h-8 rounded-md hover:bg-white/15"
                @click="$emit('toggle-collapse')"
                aria-label="Collapse sidebar"
                v-tooltip.right="'Collapse sidebar'"
                data-testid="sidebar-collapse-btn"
            >
                <PanelLeftClose :size="18" :stroke-width="1.5" />
            </button>
        </div>

        <div class="flex flex-col gap-1 pt-2" :class="collapsed ? 'items-center' : ''">
            <button
                v-if="collapsed"
                class="flex items-center justify-center w-10 h-10 rounded-md hover:bg-white/15"
                @click="$emit('toggle-collapse')"
                aria-label="Expand sidebar"
                v-tooltip.right="'Expand sidebar'"
                data-testid="sidebar-expand-btn"
            >
                <PanelLeftOpen :size="18" :stroke-width="1.5" />
            </button>
            <button
                class="flex items-center rounded-md border border-white/15 bg-white/5 hover:bg-white/15 text-gray-300"
                :class="collapsed ? 'justify-center w-10 h-10' : 'mx-2 px-3 h-9 gap-3'"
                @click="shell.paletteOpen = true"
                aria-label="Search and jump to"
                aria-keyshortcuts="Control+K Meta+K"
                v-tooltip.right="collapsed ? `Search (${modKey} K)` : null"
                data-testid="sidebar-search"
            >
                <Search class="w-4 h-4 shrink-0" aria-hidden="true" />
                <template v-if="!collapsed">
                    <span class="flex-1 text-left text-gray-400">Search…</span>
                    <kbd class="kbd-dark">{{ modKey }} K</kbd>
                </template>
            </button>
        </div>

        <div
            class="flex flex-col flex-1 overflow-y-auto overflow-x-hidden pb-2"
            :class="collapsed ? 'items-center' : ''"
        >
            <template v-for="section in sections" :key="section.id">
                <div
                    v-if="!collapsed"
                    class="pl-5 pt-5 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400"
                >
                    {{ section.label }}
                </div>
                <div v-else class="w-8 border-t border-white/15 mt-3 mb-2" role="separator"></div>
                <router-link
                    v-for="item in section.items"
                    :key="item.to"
                    :to="item.to"
                    class="nav-link flex items-center rounded"
                    :class="[
                        collapsed ? 'justify-center w-10 h-10 mb-0.5' : 'ml-2 mr-2 gap-3 px-3 h-9 mb-0.5',
                        isActive(item) ? 'nav-link-active' : '',
                    ]"
                    :aria-current="isActive(item) ? 'page' : undefined"
                    :aria-label="collapsed ? item.label : undefined"
                    v-tooltip.right="collapsed ? item.label : null"
                    :data-testid="item.testid"
                >
                    <component :is="item.icon" class="w-4 h-4 shrink-0" aria-hidden="true" />
                    <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
                </router-link>
            </template>
        </div>

        <div class="flex flex-col gap-0.5 py-2 border-t border-white/10" :class="collapsed ? 'items-center' : ''">
            <button
                class="footer-link"
                :class="collapsed ? 'footer-link-icon' : 'footer-link-row'"
                @click="shell.shortcutsOpen = true"
                aria-label="Keyboard shortcuts"
                v-tooltip.right="collapsed ? 'Keyboard shortcuts (?)' : null"
                data-testid="sidebar-shortcuts"
            >
                <Keyboard class="w-4 h-4 shrink-0" aria-hidden="true" />
                <template v-if="!collapsed">
                    <span class="flex-1 text-left">Shortcuts</span>
                    <kbd class="kbd-dark">?</kbd>
                </template>
            </button>
            <a
                v-for="link in externalLinks"
                :key="link.label"
                :href="link.href"
                target="_blank"
                rel="noopener"
                class="footer-link"
                :class="collapsed ? 'footer-link-icon' : 'footer-link-row'"
                :aria-label="`${link.label} (opens in a new tab)`"
                v-tooltip.right="collapsed ? link.label : null"
            >
                <i :class="link.icon" class="w-4 text-center" aria-hidden="true"></i>
                <template v-if="!collapsed">
                    <span class="flex-1">{{ link.label }}</span>
                    <ExternalLink class="w-3 h-3 opacity-60" aria-hidden="true" />
                </template>
            </a>
            <button
                class="footer-link"
                :class="collapsed ? 'footer-link-icon' : 'footer-link-row'"
                @click="toggleDark()"
                :aria-label="themeLabel"
                v-tooltip.right="collapsed ? themeLabel : null"
                data-testid="theme-toggle"
            >
                <component :is="isDark ? Sun : Moon" class="w-4 h-4 shrink-0" aria-hidden="true" />
                <span v-if="!collapsed" class="flex-1 text-left">{{ themeLabel }}</span>
            </button>
            <router-link
                to="/profile"
                class="footer-link"
                :class="[
                    collapsed ? 'footer-link-icon' : 'footer-link-row !h-11',
                    $route.name === 'userProfile' ? 'nav-link-active' : '',
                ]"
                :aria-label="`Profile: ${user?.username || ''}`"
                v-tooltip.right="collapsed ? user?.username : null"
                data-testid="sidebar-profile"
            >
                <Avatar
                    :image="user?.avatarUrl || null"
                    :icon="user?.avatarUrl ? null : 'pi pi-user'"
                    class="avaimg shrink-0 !w-7 !h-7"
                    style="color: rgb(209 213 219); background-color: var(--p-primary-700)"
                />
                <div v-if="!collapsed" class="flex-1 min-w-0 leading-tight">
                    <div class="font-medium truncate text-gray-200" :title="user?.username">{{ user?.username }}</div>
                    <div class="text-xs text-gray-400 flex items-center">
                        <i v-if="user?.type == 'github'" class="pi pi-github mr-1 text-xs"></i>
                        {{ user?.type }}
                    </div>
                </div>
            </router-link>
        </div>
    </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Avatar } from 'primevue'
import { useDark, useToggle } from '@vueuse/core'
import { ExternalLink, Keyboard, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { navSections, isNavItemActive } from '@/components/common/navigation'
import { shell, modKey } from '@/components/common/shell'

defineProps(['collapsed'])
defineEmits(['toggle-collapse'])

const route = useRoute()
const configStore = useConfigStore()
configStore.load()
const { user } = storeToRefs(useAuthStore())

const sections = computed(() => navSections(user.value))
const isActive = (item) => isNavItemActive(item, route)

const externalLinks = computed(() => {
    const c = configStore.config
    return [
        c.show_docs_url && { label: 'Docs', href: c.docs_url, icon: 'pi pi-book' },
        c.show_github_url && { label: 'GitHub', href: c.github_url, icon: 'pi pi-github' },
    ].filter(Boolean)
})

const isDark = useDark()
const toggleDark = useToggle(isDark)
const themeLabel = computed(() => (isDark.value ? 'Switch to light theme' : 'Switch to dark theme'))
</script>

<style scoped>
.nav-link,
.footer-link {
    color: rgb(209 213 219);
}
.nav-link:hover,
.footer-link:hover {
    background-color: rgb(255 255 255 / 0.12);
    color: #fff;
}
.nav-link-active,
.nav-link-active:hover {
    background-color: rgb(0 0 0 / 0.3);
    color: #fff;
    box-shadow: inset 3px 0 0 var(--p-primary-200);
}
.footer-link {
    display: flex;
    align-items: center;
    border-radius: 0.375rem;
}
.footer-link-row {
    gap: 0.75rem;
    margin: 0 0.5rem;
    padding: 0 0.75rem;
    height: 2rem;
}
.footer-link-icon {
    justify-content: center;
    width: 2.5rem;
    height: 2.25rem;
}
.kbd-dark {
    font-family: inherit;
    font-size: 11px;
    line-height: 1;
    padding: 3px 5px;
    border-radius: 4px;
    border: 1px solid rgb(255 255 255 / 0.2);
    color: rgb(209 213 219);
}
/* A white ring: the default dark one disappears on the blue sidebar. */
.sidebar :focus-visible {
    outline: 2px solid #fff;
    outline-offset: -2px;
}
</style>
