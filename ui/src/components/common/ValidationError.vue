<template>
    <Message severity="error">
        <span class="text-2xl">{{ message }}</span
        ><br />
        <span v-if="validation.non_fields">{{ validation.non_field }}<br /></span>
        <span v-for="name in Object.keys(validation.fields)" :key="name"
            ><span class="font-medium">{{ name }}</span
            >: {{ validation.fields[name].join(', ') }}<br
        /></span>
    </Message>
</template>

<script setup>
import Message from 'primevue/message'

const props = defineProps(['message', 'validation'])
</script>
