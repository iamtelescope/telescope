<template>
    <ContentBlock header="Target" :collapsible="false">
        <div class="p-4 flex flex-col gap-4">
            <div>
                <label for="connection_address" class="font-medium block mb-1">Address *</label>
                <InputText
                    id="connection_address"
                    v-model="connectionData.address"
                    fluid
                    :invalid="hasError('address')"
                />
                <ErrorText :text="connectionFieldErrors.address" />
            </div>
        </div>
    </ContentBlock>
</template>

<script setup>
import { reactive, watch, onMounted } from 'vue'
import InputText from 'primevue/inputtext'
import ErrorText from '@/components/common/ErrorText.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'

const emit = defineEmits(['connectionDataValidated', 'connectionDataChanged'])
const props = defineProps(['connection', 'validationErrors'])

const getInitialConnectionData = () => {
    let data = {
        address: 'unix:///var/run/docker.sock',
    }
    if (props.connection) {
        data = props.connection.data
    }
    return data
}

const connectionData = reactive(getInitialConnectionData())

const connectionFieldErrors = reactive({
    address: '',
})

const hasError = (key) => {
    return connectionFieldErrors[key] !== ''
}

const resetErrors = () => {
    for (const column in connectionFieldErrors) {
        connectionFieldErrors[column] = ''
    }
}

const validate = () => {
    resetErrors()
    let isValid = true

    if (!connectionData.address || connectionData.address.trim() === '') {
        connectionFieldErrors.address = 'Address is required'
        isValid = false
    }

    return isValid
}

defineExpose({
    validate,
})

// Watch for validation errors from parent form
watch(
    () => props.validationErrors,
    (newErrors) => {
        if (newErrors && Object.keys(newErrors).length > 0) {
            // Apply validation errors to form columns
            for (const [column, errors] of Object.entries(newErrors)) {
                if (connectionFieldErrors.hasOwnProperty(column)) {
                    connectionFieldErrors[column] = errors.join(', ')
                }
            }
        } else {
            // Clear all validation errors when parent sends empty errors
            for (const column in connectionFieldErrors) {
                connectionFieldErrors[column] = ''
            }
        }
    },
    { deep: true, immediate: true },
)

// Watch for changes to emit connectionDataChanged and always provide current data
watch(
    connectionData,
    () => {
        emit('connectionDataChanged')
        // Always emit the current connection data for form submission
        emit('connectionDataValidated', { ...connectionData })
    },
    { deep: true },
)

// Emit initial connection data on mount so parent can capture it
onMounted(() => {
    emit('connectionDataValidated', { ...connectionData })
})
</script>
