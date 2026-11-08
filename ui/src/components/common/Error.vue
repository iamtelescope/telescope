<template>
    <Message v-if="error" severity="error" role="alert" class="w-full">
        <span class="whitespace-pre-wrap break-words font-mono">{{ error }}</span>
    </Message>
</template>

<script setup>
import Message from 'primevue/message'

defineProps(['error'])
</script>
