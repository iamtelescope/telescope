<template>
  <div class="d-flex justify-center border rounded-lg border-neutral-300 dark:border-neutral-600">
    <ProgressBar v-if="loading" class="bg-transparent rounded-t-lg rounded-b-none" mode="indeterminate" style="height: 2px"></ProgressBar>
    <div v-else style="height: 2px; width:100%"></div>
    <div class="p-2">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { ProgressBar } from 'primevue'

const props = defineProps(['loading'])

</script>