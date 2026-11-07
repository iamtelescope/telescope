<template>
    <div v-if="truncated" class="text-xs text-surface-500 dark:text-surface-400 pt-1">
        truncated: showing top {{ count }}
    </div>
</template>

<script setup>
defineProps(['truncated', 'count'])
</script>
