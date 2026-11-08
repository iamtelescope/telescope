<template>
    <EmptyState
        :icon="TriangleAlert"
        :title="title"
        :compact="compact"
        :card="card"
        role="alert"
        data-testid="error-state"
    >
        <template #description>
            <span v-if="description">{{ description }}</span>
            <pre
                v-for="(e, i) in errorList"
                :key="i"
                class="mt-2 w-full text-left whitespace-pre-wrap break-words text-xs font-mono p-2 rounded bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"
                >{{ e }}</pre
            >
        </template>
        <Button
            v-if="retry"
            label="Try again"
            icon="pi pi-refresh"
            size="small"
            severity="secondary"
            @click="$emit('retry')"
        />
        <slot></slot>
    </EmptyState>
</template>

<script setup>
// A failed load, with the server's error text and an optional "Try again". See components/common/README.md.
import { computed } from 'vue'
import { Button } from 'primevue'
import { TriangleAlert } from 'lucide-vue-next'
import EmptyState from '@/components/common/EmptyState.vue'

const props = defineProps({
    title: { type: String, default: 'Something went wrong' },
    description: { type: String, default: '' },
    error: { type: [String, Array], default: null },
    retry: { type: Boolean, default: false },
    compact: { type: Boolean, default: false },
    card: { type: Boolean, default: false },
})
defineEmits(['retry'])

const errorList = computed(() => [].concat(props.error || []).filter(Boolean))
</script>
