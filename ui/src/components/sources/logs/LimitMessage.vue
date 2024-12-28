<template>
    <div v-if="display" class="text-yellow-700 pl-5 pb-2">
        <i class="pi pi-exclamation-triangle"></i> Displaying limited results: Only <span class="font-black">{{
            meta.rows }} out of {{ meta.total }}</span> matching entries are shown. Refine your
        filter or adjust
        the limit to view more.
    </div>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps(['meta'])

const display = computed(() => {
    return props.meta.rows < props.meta.total
})
</script>