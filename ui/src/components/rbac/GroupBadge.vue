<template>
    <Badge
        :value="text"
        class="bg-primary-300 text-white border border-primary-400 dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600"
    />
</template>

<script setup>
import { Badge } from 'primevue'

defineProps(['text'])
</script>
