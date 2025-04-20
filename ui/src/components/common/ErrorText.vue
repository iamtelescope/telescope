<template>
    <span v-if="text" class="text-rose-500">{{ text }}</span>
</template>
<script setup>
const props = defineProps(['text'])
</script>
