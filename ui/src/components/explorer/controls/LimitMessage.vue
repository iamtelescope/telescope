<template>
    <div
        v-if="display"
        class="flex items-center gap-2 text-sm text-amber-800 dark:text-amber-300 pb-2"
        data-testid="explorer-limit-message"
    >
        <i class="pi pi-info-circle"></i>
        <span v-if="message">{{ message }} Narrow the query or raise the limit to see more.</span>
        <span v-else>
            Showing <span class="font-semibold">{{ rowsCount.toLocaleString() }}</span> of
            <span class="font-semibold">{{ totalCount.toLocaleString() }}</span> matching rows. Load more below, raise
            the limit or narrow the query.
        </span>
    </div>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps(['rowsCount', 'totalCount', 'message'])

const display = computed(() => {
    return props.message || props.rowsCount < props.totalCount
})
</script>
