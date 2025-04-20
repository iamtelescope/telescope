<template>
    <span>{{ formattedValue }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { DateTime } from 'luxon'

const props = defineProps(['value'])

const formattedValue = computed(() => {
    return DateTime.fromISO(props.value).toFormat('yyyy-MM-dd HH:mm:ss ZZZZ')
})
</script>
