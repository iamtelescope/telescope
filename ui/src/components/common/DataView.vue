<template>
  <div>
    <slot name="loader" v-if="isLoading">
      <Loader/>
    </slot>
    <slot v-if="!isLoading && !hasErrors"/>
    <slot v-else-if="hasErrors" name="errors">
      <div class="flex flex-col p-4 gap-4">
        <Error v-for="error in errors" :key="error" :error="error"/>
      </div>
    </slot>
  </div>
</template>
<script setup>
import {computed} from 'vue'
import Loader from '@/components/common/Loader.vue'
import Error from '@/components/common/Error.vue'

const props = defineProps(['loadings', 'errors'])

const isLoading = computed(() => {
  return props.loadings.some(Boolean)
})
const hasErrors = computed(() => {
  return props.errors.some((x) => x != null && x !== '')
})
</script>
