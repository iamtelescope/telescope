<template>
    <ContentBlock header="Target" :collapsible="false">
        <div class="p-4 flex flex-col gap-4">
            <label for="connection_kubeconfig" class="font-medium block mb-1">Kubeconfig Content *</label>
            <Textarea
                id="connection_kubeconfig"
                v-model="connectionData.kubeconfig"
                rows="10"
                placeholder="Paste your complete kubeconfig file content here"
                fluid
                :invalid="hasError('kubeconfig')"
                class="font-mono text-sm"
            />
            <ErrorText :text="connectionFieldErrors.kubeconfig" />
            <small class="text-gray-600 mt-1 block">
                Paste the complete kubeconfig file content including certificates and keys
            </small>
        </div>
    </ContentBlock>
</template>

<script setup>
import { reactive, watch, onMounted } from 'vue'
import Textarea from 'primevue/textarea'
import ErrorText from '@/components/common/ErrorText.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'

const emit = defineEmits(['connectionDataValidated', 'connectionDataChanged'])
const props = defineProps(['connection', 'validationErrors'])

const getInitialConnectionData = () => {
    let data = {
        kubeconfig: '',
    }
    if (props.connection) {
        data = { ...data, ...props.connection.data }
    }
    return data
}

const connectionData = reactive(getInitialConnectionData())

const connectionFieldErrors = reactive({
    kubeconfig: '',
})

const hasError = (key) => {
    return connectionFieldErrors[key] !== ''
}

const resetErrors = () => {
    for (const field in connectionFieldErrors) {
        connectionFieldErrors[field] = ''
    }
}

const validate = () => {
    resetErrors()
    let isValid = true
    if (!connectionData.kubeconfig || connectionData.kubeconfig.trim() === '') {
        connectionFieldErrors.kubeconfig = 'Kubeconfig content is required'
        isValid = false
    }
    return isValid
}

defineExpose({
    validate,
})

watch(
    () => props.validationErrors,
    (newErrors) => {
        if (newErrors && Object.keys(newErrors).length > 0) {
            for (const [field, errors] of Object.entries(newErrors)) {
                if (connectionFieldErrors.hasOwnProperty(field)) {
                    connectionFieldErrors[field] = errors.join(', ')
                }
            }
        } else {
            for (const field in connectionFieldErrors) {
                connectionFieldErrors[field] = ''
            }
        }
    },
    { deep: true, immediate: true },
)

watch(
    connectionData,
    () => {
        emit('connectionDataChanged')
        emit('connectionDataValidated', { ...connectionData })
    },
    { deep: true },
)

onMounted(() => {
    emit('connectionDataValidated', { ...connectionData })
})
</script>