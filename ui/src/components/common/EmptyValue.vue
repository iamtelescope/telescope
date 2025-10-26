<template>
    <span>{{ displayValue }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps(['value', 'fallback'])

const displayValue = computed(() => {
    // Check if value is null, undefined, empty string, empty array, or empty object
    if (
        props.value === null ||
        props.value === undefined ||
        props.value === '' ||
        (Array.isArray(props.value) && props.value.length === 0) ||
        (typeof props.value === 'object' && props.value !== null && Object.keys(props.value).length === 0)
    ) {
        return props.fallback || '—'
    }

    return props.value
})
</script>
