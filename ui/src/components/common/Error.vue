<template>
  <div class="d-flex justify-center">
    <pre><Message severity="error">{{ error }}</Message></pre>
  </div>
</template>

<script setup>
import Message from 'primevue/message'

const props = defineProps(['error'])
</script>