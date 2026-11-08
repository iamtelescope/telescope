<template>
    <div
        class="flex flex-col items-center justify-center text-center mx-auto"
        :class="[compact ? 'py-6 px-4 gap-1.5' : 'py-12 px-6 gap-2', card ? 'empty-card max-w-[600px] w-full' : '']"
        :role="role"
    >
        <div
            v-if="icon"
            class="flex items-center justify-center rounded-full bg-surface-100 dark:bg-surface-800 text-surface-500 dark:text-surface-300"
            :class="compact ? 'w-10 h-10 mb-1' : 'w-14 h-14 mb-2'"
        >
            <component :is="icon" :class="compact ? 'w-5 h-5' : 'w-7 h-7'" aria-hidden="true" />
        </div>
        <div
            v-if="title"
            class="font-semibold text-surface-800 dark:text-surface-0"
            :class="compact ? 'text-sm' : 'text-lg'"
        >
            {{ title }}
        </div>
        <div
            v-if="description || $slots.description"
            class="max-w-[480px] text-sm text-surface-500 dark:text-surface-400"
        >
            <slot name="description">{{ description }}</slot>
        </div>
        <div v-if="$slots.default" class="mt-3 flex flex-wrap items-center justify-center gap-2">
            <slot></slot>
        </div>
    </div>
</template>

<script setup>
// Empty, "no results" and "not found" states. See components/common/README.md.
defineProps({
    icon: { type: [Object, Function], default: null },
    title: { type: String, default: '' },
    description: { type: String, default: '' },
    compact: { type: Boolean, default: false },
    card: { type: Boolean, default: false },
    role: { type: String, default: 'status' },
})
</script>

<style scoped>
.empty-card {
    border: 1px solid var(--p-content-border-color);
    border-radius: 0.5rem;
}
</style>
