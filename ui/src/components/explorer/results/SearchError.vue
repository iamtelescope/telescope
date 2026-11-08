<template>
    <div
        class="rounded border-l-4 border-red-500 bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm"
        role="alert"
        data-testid="search-error"
    >
        <div class="flex items-start gap-2">
            <i class="pi pi-exclamation-circle text-red-600 dark:text-red-400 mt-0.5"></i>
            <div class="flex-1 min-w-0">
                <div class="font-semibold text-red-700 dark:text-red-300">{{ title }}</div>
                <div class="text-neutral-800 dark:text-neutral-200 break-words" data-testid="search-error-summary">
                    {{ summary }}
                </div>
                <button
                    v-if="summary !== text"
                    class="mt-1 text-xs underline text-red-700 dark:text-red-200 hover:no-underline"
                    :aria-expanded="open ? 'true' : 'false'"
                    @click="open = !open"
                    data-testid="search-error-toggle"
                >
                    {{ open ? 'Hide details' : 'Show details' }}
                </button>
                <pre
                    v-if="open"
                    class="mt-1 max-h-64 overflow-auto whitespace-pre-wrap break-all text-xs text-neutral-700 dark:text-neutral-300"
                    >{{ text }}</pre
                >
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// compact: a short summary for narrow places such as the facet sidebar.
const props = defineProps({
    error: [String, Array, Object],
    title: { type: String, default: 'Search failed' },
    compact: Boolean,
})
const open = ref(false)

const text = computed(() => {
    const e = props.error
    if (Array.isArray(e)) return e.join('\n')
    return typeof e === 'string' ? e : JSON.stringify(e)
})

// The ClickHouse reason without the driver prefix, the SQL echo and the list of expected tokens.
const summary = computed(() => {
    const t = text.value.trim()
    const match = t.match(/DB::Exception:\s*([\s\S]*?)(?:\.\s*Expected one of|:\s*In scope|\s*\(([A-Z_]+)\)\s*$|$)/)
    const reason = (match ? match[1] : t.split('\n')[0])
        .replace(/\s+/g, ' ')
        .replace(/(\(line \d+, col \d+\)):.*$/, '$1')
        .trim()
    const code = t.match(/\(([A-Z_]{3,})\)\s*$/)?.[1]
    const max = props.compact ? 90 : 300
    const short = reason.length > max ? reason.slice(0, max) + '…' : reason
    return code && !short.includes(code) ? `${short} (${code})` : short
})
</script>
