<template>
    <div class="overflow-x-auto" data-testid="pattern-table">
        <table class="w-full min-w-full text-sm">
            <thead>
                <tr class="text-left text-xs uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
                    <th class="px-2 py-1 font-medium border-b border-neutral-200 dark:border-neutral-700 w-24">
                        Count
                    </th>
                    <th class="px-2 py-1 font-medium border-b border-neutral-200 dark:border-neutral-700 w-20">
                        Share
                    </th>
                    <th class="px-2 py-1 font-medium border-b border-neutral-200 dark:border-neutral-700 w-40">
                        Trend
                    </th>
                    <th class="px-2 py-1 font-medium border-b border-neutral-200 dark:border-neutral-700">Pattern</th>
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="(pattern, i) in patterns"
                    :key="pattern.id"
                    class="cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800 border-b border-neutral-100 dark:border-neutral-800"
                    :class="{ 'bg-neutral-100 dark:bg-neutral-800': pattern.id === selectedId }"
                    :title="`${pattern.count.toLocaleString()} rows in the sample`"
                    @click="emit('select', pattern)"
                    :data-testid="`pattern-row-${i}`"
                >
                    <td class="px-2 py-1 tabular-nums whitespace-nowrap" data-testid="pattern-count">
                        {{ sampled ? '~' : '' }}{{ pattern.est_total.toLocaleString() }}
                    </td>
                    <td class="px-2 py-1 tabular-nums whitespace-nowrap">
                        <div class="flex items-center gap-1">
                            <div class="w-8 h-1.5 rounded-sm bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                                <div class="h-full bg-primary" :style="{ width: `${pattern.share * 100}%` }"></div>
                            </div>
                            <span class="text-xs opacity-80">{{ formatShare(pattern.share) }}</span>
                        </div>
                    </td>
                    <td class="px-2 py-1">
                        <svg
                            :viewBox="`0 0 ${pattern.trend.length} 20`"
                            preserveAspectRatio="none"
                            class="w-36 h-5 block text-primary"
                            data-testid="pattern-trend"
                        >
                            <rect
                                v-for="(value, b) in pattern.trend"
                                :key="b"
                                :x="b + 0.1"
                                :y="20 - barHeight(pattern, value)"
                                width="0.8"
                                :height="barHeight(pattern, value)"
                                fill="currentColor"
                            />
                        </svg>
                    </td>
                    <td class="px-2 py-1 font-mono text-xs [overflow-wrap:anywhere]" data-testid="pattern-text">
                        <template v-for="(part, p) in templateParts(pattern.pattern)" :key="p">
                            <span
                                v-if="part === '<*>'"
                                class="px-0.5 rounded whitespace-nowrap bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                                >&lt;*&gt;</span
                            >
                            <span v-else>{{ part }}</span>
                        </template>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script setup>
import { formatShare, templateParts } from '@/components/explorer/patterns/patterns'

defineProps(['patterns', 'sampled', 'selectedId'])
const emit = defineEmits(['select'])

// Bars share one scale per row; non-zero buckets keep a minimum height.
const barHeight = (pattern, value) => {
    const max = Math.max(...pattern.trend, 1)
    return value > 0 ? Math.max((value / max) * 20, 1.5) : 0
}
</script>
