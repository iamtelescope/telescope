<template>
    <div class="min-h-[1.5rem]">
        <slot name="loader" v-if="isLoading">
            <Loader :small="smallLoader" />
        </slot>
        <slot v-if="!isLoading && !hasErrors" />
        <slot v-else-if="hasErrors && props.showErrors" name="errors">
            <ErrorState :error="errorList" title="Could not load this" compact />
        </slot>
    </div>
</template>
<script setup>
import { computed } from 'vue'
import Loader from '@/components/common/Loader.vue'
import ErrorState from '@/components/common/ErrorState.vue'

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
// Empty entries and repeats (one failure seen by several loaders) are dropped.
const errorList = computed(() => [...new Set((props.errors || []).filter((x) => x != null && x !== ''))])
const hasErrors = computed(() => errorList.value.length > 0)
</script>
