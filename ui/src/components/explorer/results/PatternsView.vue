<template>
    <div></div>
</template>

<script>
// Explorer shows the results-mode toggle only when available(source) is true.
export function available(source) {
    return false
}
</script>

<script setup>
defineProps(['source', 'searchSeq', 'timeZone'])
</script>
