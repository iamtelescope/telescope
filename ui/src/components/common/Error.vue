<template>
  <div class="d-flex justify-center">
    <Message severity="error">{{ error }}</Message>
  </div>
</template>

<script setup>
import Message from 'primevue/message'

const props = defineProps(['error'])
</script>