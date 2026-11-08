<template>
    <div
        class="flex flex-col items-center justify-center gap-3"
        :class="compact ? 'py-4' : 'py-12'"
        role="status"
        aria-live="polite"
    >
        <ProgressSpinner :class="compact ? '!w-5 !h-5' : '!w-10 !h-10'" strokeWidth="4" aria-hidden="true" />
        <span class="text-sm text-surface-500 dark:text-surface-400" :class="{ 'sr-only': !label }">{{
            label || 'Loading'
        }}</span>
    </div>
</template>

<script setup>
// A centred spinner with an optional label; screen readers hear "Loading". See components/common/README.md.
import { ProgressSpinner } from 'primevue'

defineProps({
    label: { type: String, default: '' },
    compact: { type: Boolean, default: false },
})
</script>
