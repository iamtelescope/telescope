<template>
    <div v-if="display" class="text-yellow-700 pl-5 pb-2">
        <i class="pi pi-exclamation-triangle"></i>
        <span v-if="message">{{ message }}</span>
        <span v-else>
            Displaying limited results: Only
            <span class="font-black">{{ rowsCount }} out of {{ totalCount }}</span> matching entries are shown.
        </span>
        Refine your filter or adjust the limit to view more.
    </div>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps(['rowsCount', 'totalCount', 'message'])

const display = computed(() => {
    return props.message || props.rowsCount < props.totalCount
})
</script>
