<template>
    <div class="min-h-[1.5rem]">
        <slot name="loader" v-if="isLoading">
            <Loader :small="smallLoader" />
        </slot>
        <slot v-if="!isLoading && !hasErrors" />
        <slot v-else-if="hasErrors && props.showErrors" name="errors">
            <div class="flex flex-col p-4 gap-4">
                <Error v-for="error in errors" :key="error" :error="error" />
            </div>
        </slot>
    </div>
</template>
<script setup>
import { computed } from 'vue'
import Loader from '@/components/common/Loader.vue'
import Error from '@/components/common/Error.vue'

const props = defineProps({
    loadings: Array,
    errors: Array,
    smallLoader: {
        type: Boolean,
        default: false,
    },
    showErrors: {
        type: Boolean,
        default: true,
    },
})

const isLoading = computed(() => {
    return props.loadings && props.loadings.some(Boolean)
})
const hasErrors = computed(() => {
    return props.errors && props.errors.some((x) => x != null && x !== '')
})
</script>
