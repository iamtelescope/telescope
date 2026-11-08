<template>
    <Drawer
        :visible="!!pattern"
        @update:visible="(v) => !v && emit('close')"
        position="right"
        :modal="false"
        header="Pattern"
        pt:root:style="width:min(640px, 100vw);"
        data-testid="pattern-drawer"
    >
        <div v-if="pattern" class="flex flex-col gap-4 text-sm">
            <div
                class="font-mono text-xs [overflow-wrap:anywhere] rounded border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900 p-2"
                data-testid="pattern-drawer-template"
            >
                {{ pattern.pattern }}
            </div>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-neutral-600 dark:text-neutral-300">
                <span>
                    <span class="font-semibold tabular-nums">{{ pattern.est_total.toLocaleString() }}</span>
                    {{ sampled ? 'rows (estimated)' : 'rows' }}
                </span>
                <span>{{ formatShare(pattern.share) }} of the sample</span>
            </div>
            <div class="flex flex-col gap-1">
                <span class="text-xs text-neutral-500 dark:text-neutral-400">Filter</span>
                <code class="font-mono text-xs break-all" data-testid="pattern-drawer-filter">{{
                    pattern.filter
                }}</code>
                <div>
                    <Button
                        label="Filter to pattern"
                        icon="pi pi-filter"
                        size="small"
                        class="mt-1"
                        @click="emit('filter', pattern)"
                        data-testid="pattern-filter-btn"
                    />
                </div>
            </div>
            <div class="flex flex-col gap-2">
                <span class="text-xs text-neutral-500 dark:text-neutral-400">Samples</span>
                <div
                    v-for="(row, i) in pattern.sample_rows"
                    :key="i"
                    class="rounded border border-neutral-200 dark:border-neutral-700 p-2"
                    data-testid="pattern-sample"
                >
                    <div class="text-xs text-neutral-500 dark:text-neutral-400 tabular-nums">
                        {{ getDateTimeString(row.time, timeZone) }}
                    </div>
                    <div class="font-mono text-xs whitespace-pre-wrap [overflow-wrap:anywhere]">{{ row.body }}</div>
                </div>
            </div>
        </div>
    </Drawer>
</template>

<script setup>
import { Button } from 'primevue'
import Drawer from 'primevue/drawer'

import { formatShare } from '@/components/explorer/patterns/patterns'
import { getDateTimeString } from '@/utils/datetimeranges'

defineProps(['pattern', 'sampled', 'timeZone'])
const emit = defineEmits(['close', 'filter'])
</script>
