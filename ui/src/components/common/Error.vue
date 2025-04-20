<template>
    <div class="d-flex justify-center">
        <pre class="whitespace-pre-wrap"><Message severity="error">{{ error }}</Message></pre>
    </div>
</template>

<script setup>
import Message from 'primevue/message'

const props = defineProps(['error'])
</script>
