<template>
    <ContentBlock header="Target" :collapsible="false">
        <div class="p-4 flex flex-col gap-4">
            <div class="flex items-center">
                <Checkbox
                    id="kubeconfig_is_local"
                    v-model="connectionData.kubeconfig_is_local"
                    :binary="true"
                    @change="handleLocalPathChange"
                />
                <label for="kubeconfig_is_local" class="ml-2 font-medium">
                    Use local file path instead of content
                </label>
            </div>

            <div v-if="connectionData.kubeconfig_is_local">
                <label for="connection_kubeconfig_path" class="font-medium text-lg block mb-1"> Kubeconfig File Path * </label>
                <InputText
                    id="connection_kubeconfig_path"
                    v-model="connectionData.kubeconfig"
                    placeholder="/path/to/kubeconfig.yaml"
                    fluid
                    :invalid="hasError('kubeconfig')"
                    class="font-mono text-sm"
                    @input="updateHash"
                />
                <ErrorText :text="connectionFieldErrors.kubeconfig" />
                <Message size="small" severity="secondary" variant="simple">
                    Enter the file path (e.g., /etc/kubeconfig) or home-relative path (e.g., ~/.kube/config) to your
                    kubeconfig file
                </Message>
            </div>

            <div v-else>
                <label for="connection_kubeconfig" class="font-medium text-lg block mb-1"> Kubeconfig Yaml Content * </label>
                <Textarea
                    id="connection_kubeconfig"
                    v-model="connectionData.kubeconfig"
                    rows="10"
                    placeholder="Paste your complete kubeconfig file content here"
                    fluid
                    :invalid="hasError('kubeconfig')"
                    class="font-mono text-sm"
                    @input="updateHash"
                />
                <ErrorText :text="connectionFieldErrors.kubeconfig" />
                <Message size="small" severity="secondary" variant="simple">
                    Paste the complete kubeconfig file content including certificates and keys and a single context
                </Message>
            </div>

            <InputText type="hidden" v-model="connectionData.kubeconfig_hash" />

            <div>
                <label for="context_filter" class="font-medium text-lg block mb-1"> Context FlyQL Filter </label>
                <InputText
                    id="context_filter"
                    v-model="connectionData.context_filter"
                    placeholder='(name ~ "staging" or name ~ "development") and not name ~ "production"'
                    fluid
                    :invalid="hasError('context_filter')"
                    class="font-mono text-sm"
                />
                <ErrorText :text="connectionFieldErrors.context_filter" />
                <Message size="small" severity="secondary" variant="simple">
                    Optional FlyQL query to filter available contexts from kubeconfig. Leave empty to use all contexts.
                    Available columns: name, cluster, user, namespace
                </Message>
            </div>

            <div>
                <label for="max_concurrent_requests" class="font-medium text-lg block mb-1"> Max Concurrent Requests </label>
                <InputNumber
                    id="max_concurrent_requests"
                    v-model="connectionData.max_concurrent_requests"
                    :min="1"
                    :step="1"
                    showButtons
                    fluid
                    :invalid="hasError('max_concurrent_requests')"
                />
                <ErrorText :text="connectionFieldErrors.max_concurrent_requests" />
                <Message size="small" severity="secondary" variant="simple">
                    Maximum number of concurrent requests for parallel log fetching from single context. Lower values
                    reduce load on the Kubernetes API server.
                </Message>
            </div>
        </div>
    </ContentBlock>
</template>

<script setup>
import { reactive, watch, onMounted } from 'vue'
import Textarea from 'primevue/textarea'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
import ErrorText from '@/components/common/ErrorText.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'

const emit = defineEmits(['connectionDataValidated', 'connectionDataChanged'])
const props = defineProps(['connection', 'validationErrors'])

const getInitialConnectionData = () => {
    let data = {
        kubeconfig: '',
        kubeconfig_hash: '',
        kubeconfig_is_local: false,
        context_filter: '',
        max_concurrent_requests: 20,
    }
    if (props.connection) {
        data = { ...data, ...props.connection.data }
    }
    return data
}

const connectionData = reactive(getInitialConnectionData())

const connectionFieldErrors = reactive({
    kubeconfig: '',
    context_filter: '',
    max_concurrent_requests: '',
})

const hasError = (key) => {
    return connectionFieldErrors[key] !== ''
}

const resetErrors = () => {
    for (const column in connectionFieldErrors) {
        connectionFieldErrors[column] = ''
    }
}

const generateHash = async (text) => {
    const encoder = new TextEncoder()
    const data = encoder.encode(text)
    const hashBuffer = await crypto.subtle.digest('SHA-256', data)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
}

const updateHash = async () => {
    if (connectionData.kubeconfig) {
        connectionData.kubeconfig_hash = await generateHash(connectionData.kubeconfig)
    } else {
        connectionData.kubeconfig_hash = ''
    }
}

const handleLocalPathChange = () => {
    connectionData.kubeconfig = ''
    connectionData.kubeconfig_hash = ''
}

const validate = () => {
    resetErrors()
    let isValid = true

    if (!connectionData.kubeconfig || connectionData.kubeconfig.trim() === '') {
        connectionFieldErrors.kubeconfig = 'Kubeconfig content or file path is required'
        isValid = false
    }

    if (connectionData.kubeconfig_is_local) {
        // Validate file path format for local paths
        const path = connectionData.kubeconfig.trim()
        if (path && !path.startsWith('/') && !path.startsWith('~')) {
            connectionFieldErrors.kubeconfig = 'Local file path must start with / or ~'
            isValid = false
        }
    } else {
        // Validate kubeconfig content format
        const content = connectionData.kubeconfig.trim()
        if (content && !content.includes('apiVersion:')) {
            connectionFieldErrors.kubeconfig = 'Kubeconfig content must contain valid YAML with apiVersion'
            isValid = false
        }
    }

    if (!connectionData.kubeconfig_hash) {
        connectionFieldErrors.kubeconfig = 'Kubeconfig hash is required - please ensure content is provided'
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
            for (const [column, errors] of Object.entries(newErrors)) {
                if (connectionFieldErrors.hasOwnProperty(column)) {
                    connectionFieldErrors[column] = errors.join(', ')
                }
            }
        } else {
            for (const column in connectionFieldErrors) {
                connectionFieldErrors[column] = ''
            }
        }
    },
    { deep: true, immediate: true },
)

watch(
    connectionData,
    async (newData, oldData) => {
        if (newData.kubeconfig !== oldData.kubeconfig) {
            await updateHash()
        }
        emit('connectionDataChanged')
        emit('connectionDataValidated', { ...connectionData })
    },
    { deep: true },
)

onMounted(() => {
    emit('connectionDataValidated', { ...connectionData })
})
</script>
