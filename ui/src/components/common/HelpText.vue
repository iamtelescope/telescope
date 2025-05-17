<template>
  <Message v-if="text" size="small" severity="secondary" variant="simple">{{ text }}</Message>
</template>
<script setup>
import {Message} from 'primevue'

const props = defineProps(['text'])
</script>