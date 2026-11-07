<template>
    <div></div>
</template>

<script>
// Row.vue renders this only when available(source, row) is true.
export function available(source, row) {
    return false
}
</script>

<script setup>
defineProps(['source', 'row', 'timeZone'])
</script>
