<template>
    <Dialog
        v-model:visible="shell.shortcutsOpen"
        modal
        dismissableMask
        header="Keyboard shortcuts"
        class="w-[560px] max-w-[92vw]"
        data-testid="shortcuts-dialog"
    >
        <div v-for="(rows, group) in grouped" :key="group" class="mb-4 last:mb-0">
            <div class="text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400 mb-1">
                {{ group }}
            </div>
            <div
                v-for="row in rows"
                :key="row.label"
                class="flex items-center justify-between gap-4 py-1.5 border-b last:border-b-0 border-surface-200 dark:border-surface-700"
            >
                <span class="text-surface-700 dark:text-surface-200">{{ row.label }}</span>
                <span class="flex items-center gap-1 shrink-0">
                    <template v-for="(k, i) in row.keys" :key="k">
                        <span v-if="i" class="text-xs text-surface-500 px-0.5">{{
                            row.join === 'or' ? 'or' : '+'
                        }}</span>
                        <kbd class="kbd">{{ k }}</kbd>
                    </template>
                </span>
            </div>
        </div>
    </Dialog>
</template>

<script setup>
import { computed } from 'vue'
import { Dialog } from 'primevue'
import { shell, SHORTCUTS } from '@/components/common/shell'

const grouped = computed(() => SHORTCUTS.reduce((acc, row) => ((acc[row.group] ||= []).push(row), acc), {}))
</script>

<style scoped>
.kbd {
    font-family: inherit;
    font-size: 11px;
    line-height: 1;
    min-width: 1.5rem;
    text-align: center;
    padding: 3px 6px;
    border-radius: 4px;
    border: 1px solid var(--p-content-border-color);
    border-bottom-width: 2px;
    background: var(--p-content-background);
}
</style>
