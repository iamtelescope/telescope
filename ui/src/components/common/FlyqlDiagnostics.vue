<template>
    <div
        class="mb-2 rounded border-l-2 border-red-500 bg-surface-50 dark:bg-surface-900 px-3 py-2"
        data-testid="flyql-diagnostics"
    >
        <div
            v-for="(diag, idx) in diagnostics"
            :key="idx"
            class="font-mono text-sm leading-5"
            :class="{ 'mt-3': idx > 0 }"
        >
            <div class="text-xs uppercase tracking-wide text-surface-500 dark:text-surface-400 mb-0.5">
                {{ diag.section }}<span v-if="diag.range"> · pos {{ diag.range.start + 1 }}</span>
            </div>
            <pre
                v-if="diag.input"
                class="overflow-x-auto whitespace-pre text-surface-700 dark:text-surface-200 m-0"
            ><span>{{ diag.input }}</span><span v-if="caretLine(diag)">
<span class="text-red-500">{{ caretLine(diag) }}</span></span></pre>
            <div class="text-red-600 dark:text-red-400 mt-0.5">{{ diag.message }}</div>
        </div>
    </div>
</template>

<script setup>
const props = defineProps({
    diagnostics: { type: Array, default: () => [] },
})

function caretLine(diag) {
    if (!diag.range || !diag.input) return ''
    const start = diag.range.start
    const end = diag.range.end ?? start + 1
    const span = Math.max(1, end - start)
    return ' '.repeat(start) + '^'.repeat(span)
}
</script>
