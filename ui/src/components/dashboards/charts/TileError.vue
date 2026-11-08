<template>
    <div
        class="flex flex-col items-center justify-center gap-1.5 h-full p-2 text-center text-sm text-surface-500 dark:text-surface-400"
        role="alert"
        data-testid="tile-error"
    >
        <i class="pi pi-exclamation-triangle text-xl text-red-500 dark:text-red-400"></i>
        <span class="font-medium text-surface-700 dark:text-surface-200">Query failed</span>
        <pre
            class="max-w-full max-h-[50%] overflow-auto whitespace-pre-wrap break-words text-left text-xs font-mono px-2"
            >{{ error }}</pre
        >
        <Button
            label="Retry"
            icon="pi pi-refresh"
            size="small"
            severity="secondary"
            outlined
            data-testid="tile-retry"
            @click="emit('retry')"
        />
    </div>
</template>

<script setup>
import { Button } from 'primevue'

defineProps(['error'])
const emit = defineEmits(['retry'])
</script>
