<template>
    <div class="flex justify-center items-center" :class="small ? 'h-6' : 'h-full'">
        <ProgressSpinner v-if="!small"></ProgressSpinner>
        <ProgressSpinner v-else style="width: 15px; height: 15px" stroke-width="4"></ProgressSpinner>
    </div>
</template>

<script setup>
import ProgressSpinner from 'primevue/progressspinner'

const props = defineProps({
    small: {
        type: Boolean,
        default: false,
    },
})
</script>
