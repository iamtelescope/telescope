<template>
    <PageHeader :loading="loading">
        <template #left>
            <div class="text-3xl font-thin">
                <slot name="title"></slot>
            </div>
            <div class="text-gray-400">
                <slot name="subtitle"></slot>
            </div>
        </template>
        <template #right>
            <slot name="actions"></slot>
        </template>
    </PageHeader>
</template>

<script setup>
import PageHeader from '@/components/common/PageHeader.vue'

const props = defineProps({
    loading: {
        type: Boolean,
        default: false,
    },
})
</script>
