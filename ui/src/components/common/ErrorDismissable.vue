<template>
    <Message
        v-if="modelValue"
        severity="error"
        size="small"
        :closable="true"
        @close="handleClose"
        :pt="{
            closeButton: { class: 'self-start' },
        }"
    >
        {{ modelValue }}
    </Message>
</template>

<script setup>
import { Message } from 'primevue'

const props = defineProps({
    modelValue: String,
})

const emit = defineEmits(['update:modelValue'])

const handleClose = () => {
    emit('update:modelValue', '')
}
</script>
