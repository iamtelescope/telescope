<template>
    <span v-if="text" class="text-red-600 dark:text-red-500">{{ text }}</span>
</template>
<script setup>
const props = defineProps(['text'])
</script>
