<template>
    <Loader v-if="loading" />
    <div v-else>
        <Error v-if="error" :error="error" />
        <slot v-else></slot>
    </div>
</template>

<script setup>
import Error from '@/components/common/Error.vue'
import Loader from '@/components/common/Loader.vue'

const props = defineProps(['loading', 'error'])
</script>
