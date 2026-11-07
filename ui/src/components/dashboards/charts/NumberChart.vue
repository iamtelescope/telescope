<template>
    <div class="flex items-center justify-center h-full text-4xl font-medium truncate" :title="String(data.value)">
        {{ formatValue(data.value, numberFormat) }}
    </div>
</template>

<script setup>
import { formatValue } from '@/utils/dashboards.js'

defineProps(['data', 'numberFormat'])
</script>
