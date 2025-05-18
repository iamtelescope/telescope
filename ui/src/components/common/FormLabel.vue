<template>
    <label
        :for="props.for ? props.for : label.toLowerCase()"
        class="font-medium"
        :class="{ 'text-red-500': invalid }"
        >{{ label }}</label
    >
</template>
<script setup>
const props = defineProps(['for', 'label', 'invalid'])
</script>
