<template>
    <div
        v-if="modelValue"
        class="mt-2 bg-red-50 dark:bg-red-900/20 p-3 rounded border-l-4 border-red-500 text-red-600 dark:text-red-400 flex justify-between items-start gap-3"
    >
        <pre class="flex-1 m-0 whitespace-pre-wrap break-words overflow-hidden">{{ modelValue }}</pre>
        <button
            v-if="dismissable"
            @click="handleClose"
            class="ml-3 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 flex-shrink-0"
            aria-label="Close"
        >
            <i class="pi pi-times"></i>
        </button>
    </div>
</template>

<script setup>
const props = defineProps({
    modelValue: String,
    dismissable: {
        type: Boolean,
        default: false,
    },
})

const emit = defineEmits(['update:modelValue'])

const handleClose = () => {
    emit('update:modelValue', '')
}
</script>
