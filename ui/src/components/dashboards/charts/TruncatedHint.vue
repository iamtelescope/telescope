<template>
    <div v-if="truncated" class="text-xs text-surface-500 dark:text-surface-400 pt-1">
        Showing the top {{ count }} {{ count === 1 ? 'group' : 'groups' }} only
    </div>
</template>

<script setup>
defineProps(['truncated', 'count'])
</script>
