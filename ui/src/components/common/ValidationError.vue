<template>
    <Message severity="error">
        <span class="text-2xl">{{ message }}</span
        ><br />
        <span v-if="validation.non_field && validation.non_field.length"
            >{{ validation.non_field.join(', ') }}<br
        /></span>
        <span v-for="name in Object.keys(fieldErrors)" :key="name"
            ><span class="font-medium">{{ name }}</span
            >: {{ fieldErrors[name].join(', ') }}<br
        /></span>
    </Message>
</template>

<script setup>
import { computed } from 'vue'
import Message from 'primevue/message'

const props = defineProps(['message', 'validation'])

const fieldErrors = computed(() => ({
    ...(props.validation?.fields || {}),
    ...(props.validation?.columns || {}),
}))
</script>
