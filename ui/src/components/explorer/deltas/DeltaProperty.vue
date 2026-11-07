<template>
    <div
        class="rounded-lg border border-neutral-200 dark:border-neutral-700 p-2.5 text-sm"
        :data-key="property.key"
        data-testid="deltas-property"
    >
        <div class="flex items-baseline justify-between gap-2 pb-1.5">
            <span class="font-mono text-xs font-medium break-all" data-testid="deltas-property-key">{{
                property.key
            }}</span>
            <span
                class="shrink-0 text-xs tabular-nums text-neutral-500 dark:text-neutral-400"
                v-tooltip.top="'How differently the values split, 0 (same) to 100 (disjoint)'"
                data-testid="deltas-property-score"
            >
                {{ Math.round(property.score) }}
            </span>
        </div>
        <div
            v-for="v in shown"
            :key="String(v.value)"
            class="group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 py-0.5"
            data-testid="deltas-value"
        >
            <div class="min-w-0">
                <div class="flex items-center gap-1">
                    <span
                        class="truncate text-xs"
                        :class="{ 'italic text-neutral-500': v.value === null }"
                        :title="label(v)"
                    >
                        {{ label(v) }}
                    </span>
                    <span v-if="filterable && v.value !== null" class="hidden group-hover:flex shrink-0">
                        <button
                            type="button"
                            class="px-1 text-neutral-500 hover:text-primary"
                            aria-label="Filter by this value"
                            v-tooltip.top="'Filter by this value'"
                            @click="emit('filter', v.value, '=')"
                            data-testid="deltas-filter"
                        >
                            <i class="pi pi-search-plus text-xs"></i>
                        </button>
                        <button
                            type="button"
                            class="px-1 text-neutral-500 hover:text-primary"
                            aria-label="Exclude this value"
                            v-tooltip.top="'Exclude this value'"
                            @click="emit('filter', v.value, '!=')"
                            data-testid="deltas-exclude"
                        >
                            <i class="pi pi-search-minus text-xs"></i>
                        </button>
                    </span>
                </div>
                <div class="flex flex-col gap-0.5 mt-0.5">
                    <div class="h-1.5 rounded-sm" :style="bar(v.outlier, colors.selection)"></div>
                    <div class="h-1.5 rounded-sm" :style="bar(v.inlier, colors.background)"></div>
                </div>
            </div>
            <div class="flex flex-col text-right text-xs tabular-nums leading-tight">
                <span>{{ formatPercent(v.outlier) }}</span>
                <span class="text-neutral-500 dark:text-neutral-400">{{ formatPercent(v.inlier) }}</span>
            </div>
        </div>
        <div v-if="property.distinct > shown.length" class="pt-1 text-xs text-neutral-500 dark:text-neutral-400">
            {{ property.distinct - shown.length }} more values
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue'

import { formatPercent } from '@/components/explorer/deltas/deltas'

const props = defineProps({ property: Object, colors: Object, filterable: Boolean })
const emit = defineEmits(['filter'])

const VALUES = 5
const shown = computed(() => props.property.values.slice(0, VALUES))

const label = (v) => (v.value === null ? '(not set)' : v.value === '' ? '(empty)' : v.value)

// A bar of 0..100 percent; an empty one keeps a 2px stub so its row stays readable.
const bar = (pct, color) => ({ width: `${Math.max(pct, 0.5)}%`, minWidth: '2px', background: color })
</script>
