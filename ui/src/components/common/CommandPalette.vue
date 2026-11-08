<template>
    <Dialog
        v-model:visible="shell.paletteOpen"
        modal
        dismissableMask
        :showHeader="false"
        position="top"
        class="w-[640px] max-w-[92vw] !mt-[12vh]"
        :pt="{ content: { class: '!p-0' } }"
        @show="onShow"
        @hide="query = ''"
    >
        <div data-testid="command-palette" @keydown="onKeydown">
            <div class="flex items-center gap-3 px-4 border-b border-surface-200 dark:border-surface-700">
                <Search class="w-4 h-4 text-surface-500 dark:text-surface-400 shrink-0" aria-hidden="true" />
                <input
                    ref="input"
                    v-model="query"
                    class="flex-1 h-12 bg-transparent outline-none text-base text-surface-900 dark:text-surface-0 placeholder:text-surface-500 dark:placeholder:text-surface-400"
                    placeholder="Search pages, dashboards, saved views, sources…"
                    role="combobox"
                    aria-label="Search pages, dashboards, saved views and sources"
                    aria-expanded="true"
                    aria-controls="command-palette-list"
                    aria-autocomplete="list"
                    :aria-activedescendant="flat[active] ? `cp-item-${active}` : undefined"
                    data-testid="command-palette-input"
                />
                <ProgressSpinner v-if="loading" class="!w-4 !h-4" strokeWidth="6" aria-label="Loading" />
                <kbd class="kbd">Esc</kbd>
            </div>
            <div id="command-palette-list" ref="list" role="listbox" class="max-h-[56vh] overflow-y-auto py-2">
                <template v-for="group in groups" :key="group.name">
                    <div
                        class="px-4 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400"
                        role="presentation"
                    >
                        {{ group.name }}
                    </div>
                    <div
                        v-for="item in group.items"
                        :key="item.key"
                        :id="`cp-item-${item.index}`"
                        role="option"
                        :aria-selected="item.index === active"
                        class="mx-2 px-3 py-2 rounded-md flex items-center gap-3 cursor-pointer"
                        :class="
                            item.index === active
                                ? 'bg-primary-50 text-primary-800 dark:bg-primary-400/20 dark:text-surface-0'
                                : 'text-surface-700 dark:text-surface-200'
                        "
                        @mousemove="active = item.index"
                        @click="run(item)"
                        data-testid="command-palette-item"
                    >
                        <component :is="item.icon" class="w-4 h-4 shrink-0 opacity-70" aria-hidden="true" />
                        <span class="truncate shrink-0 max-w-[60%]">{{ item.label }}</span>
                        <span v-if="item.sub" class="truncate min-w-0 text-xs text-surface-500 dark:text-surface-400">
                            {{ item.sub }}
                        </span>
                        <CornerDownLeft
                            v-if="item.index === active"
                            class="ml-auto w-3.5 h-3.5 shrink-0 opacity-60"
                            aria-hidden="true"
                        />
                    </div>
                </template>
                <EmptyState
                    v-if="!flat.length"
                    compact
                    :icon="SearchX"
                    :title="loading ? 'Loading…' : `Nothing matches “${query}”`"
                    description="Try a page name, a dashboard, a saved view or a source slug."
                />
            </div>
            <div
                class="flex items-center gap-4 px-4 py-2 border-t border-surface-200 dark:border-surface-700 text-xs text-surface-500 dark:text-surface-400"
            >
                <span><kbd class="kbd">↑</kbd> <kbd class="kbd">↓</kbd> to move</span>
                <span><kbd class="kbd">Enter</kbd> to open</span>
                <span class="ml-auto"><kbd class="kbd">?</kbd> all shortcuts</span>
            </div>
        </div>
    </Dialog>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Dialog, ProgressSpinner } from 'primevue'
import { useDark } from '@vueuse/core'
import {
    Bookmark,
    CornerDownLeft,
    Database,
    Keyboard,
    KeyRound,
    LayoutDashboard,
    LogOut,
    Moon,
    Plus,
    Search,
    SearchX,
    User,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { SourceService } from '@/sdk/services/source'
import { DashboardService } from '@/sdk/services/dashboard'
import EmptyState from '@/components/common/EmptyState.vue'
import { navSections } from '@/components/common/navigation'
import { shell } from '@/components/common/shell'

const PER_GROUP = 8
const router = useRouter()
const { user } = storeToRefs(useAuthStore())
const isDark = useDark()

const query = ref('')
const active = ref(0)
const input = ref(null)
const list = ref(null)
const loading = ref(false)
const data = ref({ sources: [], dashboards: [], views: [] })
let loadedAt = 0

const sourceSrv = new SourceService()
const dashboardSrv = new DashboardService()

// Lists are fetched when the palette opens and reused for a minute.
const load = async () => {
    if (Date.now() - loadedAt < 60_000) return
    loading.value = true
    const [sources, dashboards] = await Promise.all([sourceSrv.getSources(), dashboardSrv.getDashboards()])
    const srcList = sources.result ? sources.data : []
    const viewLists = await Promise.all(srcList.map((s) => sourceSrv.getSavedViews(s.slug)))
    data.value = {
        sources: srcList,
        dashboards: dashboards.result ? dashboards.data : [],
        views: viewLists.flatMap((r, i) => (r.result ? r.data.map((v) => ({ ...v, source: srcList[i] })) : [])),
    }
    loadedAt = Date.now()
    loading.value = false
}

const can = (perm) => (user.value?.permissions || []).includes(perm)

const items = computed(() => {
    const pages = navSections(user.value).flatMap((s) =>
        s.items.map((i) => ({ group: 'Pages', label: i.label, icon: i.icon, to: i.to, keywords: i.keywords })),
    )
    const actions = [
        { label: 'Dashboard templates', icon: Plus, to: '/dashboards/templates', keywords: 'new dashboard preset' },
        can('global_create_source') && { label: 'New source', icon: Plus, to: '/sources/new', keywords: 'create' },
        can('global_create_connection') && {
            label: 'New connection',
            icon: Plus,
            to: '/connections/new',
            keywords: 'create',
        },
        { label: 'Profile', icon: User, to: '/profile', keywords: 'account user me' },
        { label: 'New API token', icon: KeyRound, to: '/profile/new_api_token', keywords: 'create key' },
        {
            label: isDark.value ? 'Switch to light theme' : 'Switch to dark theme',
            icon: Moon,
            run: () => (isDark.value = !isDark.value),
            keywords: 'dark light mode theme appearance',
        },
        { label: 'Keyboard shortcuts', icon: Keyboard, run: () => (shell.shortcutsOpen = true), keywords: 'help keys' },
        { label: 'Log out', icon: LogOut, run: () => (window.location.href = '/logout'), keywords: 'sign out' },
    ]
        .filter(Boolean)
        .map((a) => ({ group: 'Actions', ...a }))
    const d = data.value
    return [
        ...pages,
        ...d.dashboards.map((x) => ({
            group: 'Dashboards',
            label: x.name,
            sub: x.description,
            icon: LayoutDashboard,
            to: `/dashboards/${x.slug}`,
        })),
        ...d.views.map((v) => ({
            group: 'Saved views',
            label: v.name,
            sub: v.source.name || v.source.slug,
            icon: Bookmark,
            to: { name: 'explore', params: { sourceSlug: v.source.slug }, query: { view: v.slug } },
        })),
        ...d.sources.map((s) => ({
            group: 'Sources',
            label: s.name || s.slug,
            sub: s.slug,
            icon: Database,
            to: { name: 'explore', params: { sourceSlug: s.slug } },
            keywords: 'explore search logs',
        })),
        ...actions,
    ]
})

// Every word must appear somewhere. Rank: label before sub (slug, description), then start, word start, anywhere.
const rank = (item, q, words) => {
    const hay = [item.label, item.sub, item.keywords, item.group].join(' ').toLowerCase()
    if (!words.every((w) => hay.includes(w))) return -1
    const at = (text, extra) => {
        const t = (text || '').toLowerCase()
        if (t.startsWith(q)) return extra
        if (t.includes(` ${q}`)) return extra + 1
        if (t.includes(q)) return extra + 2
        return 9
    }
    return Math.min(at(item.label, 0), at(item.sub, 0.5), 6)
}

const ORDER = ['Pages', 'Dashboards', 'Saved views', 'Sources', 'Actions']

const groups = computed(() => {
    const q = query.value.trim().toLowerCase()
    const words = q.split(/\s+/)
    // Sorted best first, so each group's first item carries its best rank.
    const found = q
        ? items.value
              .map((item) => ({ item, r: rank(item, q, words) }))
              .filter((x) => x.r >= 0)
              .sort((a, b) => a.r - b.r)
        : items.value.map((item) => ({ item, r: 0 }))
    const ranked = ORDER.map((name) => {
        const all = found.filter((x) => x.item.group === name)
        const limit = q || name === 'Pages' || name === 'Actions' ? PER_GROUP : 5
        return { name, best: all[0]?.r, items: all.slice(0, limit).map((x) => x.item) }
    }).filter((g) => g.items.length)
    // The group holding the best match comes first; ties keep the usual order.
    if (q) ranked.sort((a, b) => a.best - b.best)
    let index = 0
    return ranked.map((g) => ({
        name: g.name,
        items: g.items.map((i) => ({
            ...i,
            key: `${g.name}:${i.label}:${JSON.stringify(i.to || '')}`,
            index: index++,
        })),
    }))
})

const flat = computed(() => groups.value.flatMap((g) => g.items))

watch(query, () => (active.value = 0))

const scrollToActive = () =>
    nextTick(() => list.value?.querySelector(`#cp-item-${active.value}`)?.scrollIntoView({ block: 'nearest' }))

const onKeydown = (e) => {
    const n = flat.value.length
    if (e.key === 'ArrowDown' && n) {
        active.value = (active.value + 1) % n
        scrollToActive()
    } else if (e.key === 'ArrowUp' && n) {
        active.value = (active.value - 1 + n) % n
        scrollToActive()
    } else if (e.key === 'Enter' && flat.value[active.value]) {
        run(flat.value[active.value])
    } else return
    e.preventDefault()
}

const run = (item) => {
    shell.paletteOpen = false
    if (item.run) item.run()
    else router.push(item.to)
}

const onShow = () => {
    active.value = 0
    input.value?.focus()
    load()
}
</script>

<style scoped>
.kbd {
    font-family: inherit;
    font-size: 11px;
    line-height: 1;
    padding: 2px 5px;
    border-radius: 4px;
    border: 1px solid var(--p-content-border-color);
    background: var(--p-content-background);
}
</style>
