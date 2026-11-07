<template></template>

<script setup>
// Extra Tile.vue menu entries come from the exposed items array (PrimeVue MenuItem shape).
defineProps(['tile', 'range', 'timeZone'])
defineExpose({ items: [] })
</script>
