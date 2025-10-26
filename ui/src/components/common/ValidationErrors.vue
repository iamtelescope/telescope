<template>
    <div v-if="filteredErrors.length > 0" class="flex flex-col gap-3">
        <Message severity="error">
            <div class="flex flex-col gap-2">
                <div class="font-bold text-lg">
                    {{ validationErrorTitle }}
                </div>

                <div class="border-l-4 border-orange-500 pl-3 mt-2">
                    <div class="font-bold text-orange-700">Errors:</div>
                    <ul class="list-disc list-inside ml-2">
                        <li v-for="(error, index) in filteredErrors" :key="`validation-error-${index}`" class="mb-1">
                            <span v-if="error.length <= 100">{{ error }}</span>
                            <span v-else>
                                {{ truncateText(error, 100) }}
                                <Button
                                    label="Show full"
                                    text
                                    size="small"
                                    class="ml-2 p-0 h-auto text-orange-600 underline"
                                    @click="showFullError(error)"
                                />
                            </span>
                        </li>
                    </ul>
                </div>
            </div>
        </Message>

        <Dialog
            v-model:visible="dialogVisible"
            modal
            header="Full Error Message"
            :style="{ width: '50rem' }"
            :breakpoints="{ '1199px': '75vw', '575px': '90vw' }"
        >
            <pre
                class="whitespace-pre-wrap text-sm max-h-96 overflow-auto p-3 bg-gray-50 dark:bg-gray-800 rounded border dark:border-[var(--p-surface-900)]"
                >{{ selectedError }}</pre
            >
        </Dialog>
    </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Button, Dialog, Message } from 'primevue'

const props = defineProps(['errors', 'label'])

const dialogVisible = ref(false)
const selectedError = ref('')

const truncateText = (text, length) => {
    return text.length <= length ? text : text.substring(0, length) + '...'
}

const showFullError = (error) => {
    selectedError.value = error
    dialogVisible.value = true
}

const filteredErrors = computed(() => {
    if (!props.errors) return []
    return props.errors.filter((error) => error != null && error !== '')
})

const validationErrorTitle = computed(() => {
    if (props.label) {
        return props.label
    }
    return 'Data validation failed'
})
</script>
