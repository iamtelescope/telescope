<template>
    <ContentBlock header="Target" :collapsible="false">
        <div class="p-4 flex flex-col w-full flex-wrap gap-4">
            <!-- Host and Port -->
            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <label for="connection_host" class="font-medium block mb-1">Host *</label>
                    <InputText
                        id="connection_host"
                        v-model="connectionData.host"
                        fluid
                        :disabled="connectionTestIsActive"
                        :invalid="hasError('host')"
                    />
                    <ErrorText :text="connectionFieldErrors.host" />
                </div>
                <div class="flex flex-col w-full">
                    <label for="connection_port" class="font-medium block mb-1">Port *</label>
                    <InputNumber
                        id="connection_port"
                        :useGrouping="false"
                        :min="1"
                        :max="65535"
                        v-model="connectionData.port"
                        fluid
                        :disabled="connectionTestIsActive"
                        :invalid="hasError('port')"
                    />
                    <ErrorText :text="connectionFieldErrors.port" />
                </div>
            </div>

            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <label for="connection_user" class="font-medium block mb-1">User *</label>
                    <InputText
                        id="connection_user"
                        v-model="connectionData.user"
                        fluid
                        :disabled="connectionTestIsActive"
                        :invalid="hasError('user')"
                    />
                    <ErrorText :text="connectionFieldErrors.user" />
                </div>
                <div class="flex flex-col w-full">
                    <label for="connection_password" class="font-medium block mb-1">Password</label>
                    <Password
                        v-model="connectionData.password"
                        toggleMask
                        :feedback="false"
                        inputId="connection_password"
                        fluid
                        :disabled="connectionTestIsActive"
                        :invalid="hasError('password')"
                    />
                    <ErrorText :text="connectionFieldErrors.password" />
                </div>
            </div>

            <ContentBlock header="HTTPS/TLS Configuration" :collapsible="false" class="mt-4">
                <template #actions>
                    <div class="flex items-center gap-6">
                        <div class="flex items-center" v-if="connectionData.ssl">
                            <label for="advanced_setup" class="mr-2 font-medium">Advanced setup</label>
                            <ToggleSwitch
                                id="advanced_setup"
                                v-model="showAdvancedSetup"
                                :disabled="connectionTestIsActive"
                            />
                        </div>
                        <div class="flex items-center">
                            <label for="connection_ssl" class="mr-2 font-medium">HTTPS enabled</label>
                            <ToggleSwitch
                                id="connection_ssl"
                                v-model="connectionData.ssl"
                                :disabled="connectionTestIsActive"
                            />
                        </div>
                    </div>
                </template>

                <div v-if="connectionData.ssl && showAdvancedSetup" class="p-4 flex flex-col gap-4">
                    <div class="flex items-center">
                        <label for="connection_verify" class="mr-2 font-medium">Verify</label>
                        <ToggleSwitch
                            id="connection_verify"
                            v-model="connectionData.verify"
                            :disabled="connectionTestIsActive"
                        />
                    </div>

                    <div>
                        <label for="connection_ca_cert" class="font-medium block mb-1">CA Certificate</label>
                        <Textarea
                            id="connection_ca_cert"
                            v-model="connectionData.ca_cert"
                            fluid
                            rows="3"
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('ca_cert')"
                        />
                        <ErrorText :text="connectionFieldErrors.ca_cert" />
                    </div>

                    <div>
                        <label for="connection_client_cert" class="font-medium block mb-1">Client Certificate</label>
                        <Textarea
                            id="connection_client_cert"
                            v-model="connectionData.client_cert"
                            fluid
                            rows="3"
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('client_cert')"
                        />
                        <ErrorText :text="connectionFieldErrors.client_cert" />
                    </div>

                    <div>
                        <label for="connection_client_cert_key" class="font-medium block mb-1"
                            >Client Certificate Key</label
                        >
                        <Textarea
                            id="connection_client_cert_key"
                            v-model="connectionData.client_cert_key"
                            fluid
                            rows="3"
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('client_cert_key')"
                        />
                        <ErrorText :text="connectionFieldErrors.client_cert_key" />
                    </div>

                    <div>
                        <label for="connection_server_host_name" class="font-medium block mb-1">Server Host Name</label>
                        <InputText
                            id="connection_server_host_name"
                            v-model="connectionData.server_host_name"
                            fluid
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('server_host_name')"
                        />
                        <ErrorText :text="connectionFieldErrors.server_host_name" />
                    </div>

                    <div>
                        <label for="connection_tls_mode" class="font-medium block mb-1">TLS Mode</label>
                        <Select
                            id="connection_tls_mode"
                            v-model="connectionData.tls_mode"
                            fluid
                            :options="tlsModeOptions"
                            :disabled="connectionTestIsActive"
                            optionLabel="label"
                            optionValue="value"
                            :invalid="hasError('tls_mode')"
                            showClear
                        />
                        <ErrorText :text="connectionFieldErrors.tls_mode" />
                    </div>
                </div>
            </ContentBlock>
        </div>

        <ValidationErrors
            :errors="connectionTestErrors"
            label="Connection Test Failed"
            v-if="connectionTestErrors.length > 0"
            class="mt-4"
        />

        <ConnectionTestResult
            :data="connectionTestData"
            :loading="connectionTestIsActive"
            v-if="connectionTestCalled"
        />
    </ContentBlock>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Password from 'primevue/password'
import ToggleSwitch from 'primevue/toggleswitch'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import ConnectionTestResult from '@/components/connections/new/ConnectionTestResult.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import ValidationErrors from '@/components/common/ValidationErrors.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import { ConnectionService } from '@/sdk/services/connection'

const emit = defineEmits([
    'connectionDataValidated',
    'connectionTestStarted',
    'connectionTestEnded',
    'connectionDataChanged',
])
const props = defineProps(['connection', 'startConnectionTest', 'validationErrors'])

const toast = useToast()
const connectionSrv = new ConnectionService()

const tlsModeOptions = [
    { label: 'Mutual', value: 'mutual' },
    { label: 'Strict', value: 'strict' },
    { label: 'Proxy', value: 'proxy' },
]

const connectionTestIsActive = ref(false)
const connectionTestCalled = ref(false)
const connectionTestData = ref({})
const connectionTestErrors = ref([])

const connectionData = reactive({
    host: props.connection?.data?.host || 'localhost',
    port: props.connection?.data?.port || 8123,
    user: props.connection?.data?.user || 'default',
    password: props.connection?.data?.password || '',
    ssl: props.connection?.data?.ssl !== undefined ? props.connection?.data?.ssl : false,
    verify: props.connection?.data?.verify || true,
    ca_cert: props.connection?.data?.ca_cert || '',
    client_cert: props.connection?.data?.client_cert || '',
    client_cert_key: props.connection?.data?.client_cert_key || '',
    server_host_name: props.connection?.data?.server_host_name || '',
    tls_mode: props.connection?.data?.tls_mode || '',
})

// Check if any advanced TLS parameters have non-default values
const hasAdvancedTLSConfig = () => {
    return (
        connectionData.ca_cert ||
        connectionData.client_cert ||
        connectionData.client_cert_key ||
        connectionData.server_host_name ||
        connectionData.tls_mode
    )
}

const showAdvancedSetup = ref(hasAdvancedTLSConfig())

const connectionFieldErrors = reactive({
    host: '',
    port: '',
    user: '',
    password: '',
    ca_cert: '',
    client_cert: '',
    client_cert_key: '',
    server_host_name: '',
    tls_mode: '',
})

const hasError = (column) => {
    return connectionFieldErrors[column] !== ''
}

const resetErrors = () => {
    for (const column in connectionFieldErrors) {
        connectionFieldErrors[column] = ''
    }
    connectionTestErrors.value = []
}

const validate = () => {
    resetErrors()
    let isValid = true

    if (!connectionData.host || connectionData.host.trim() === '') {
        connectionFieldErrors.host = 'Host is required'
        isValid = false
    }

    if (!connectionData.port) {
        connectionFieldErrors.port = 'Port is required'
        isValid = false
    }

    if (!connectionData.user || connectionData.user.trim() === '') {
        connectionFieldErrors.user = 'User is required'
        isValid = false
    }

    return isValid
}

defineExpose({
    validate,
})

const handleTestConnection = async () => {
    resetErrors()
    connectionTestIsActive.value = true
    connectionTestCalled.value = true

    emit('connectionTestStarted')

    try {
        const response = await connectionSrv.testConnection('clickhouse', { ...connectionData })

        connectionTestData.value = response

        const isValidationPassed = response.result && (!response.validation || response.validation.result)
        const isReachabilityPassed = response.data.result === true

        if (isValidationPassed && isReachabilityPassed) {
            emit('connectionDataValidated', { ...connectionData })
        } else {
            if (response.validation && !response.validation.result) {
                for (const [column, errors] of Object.entries(response.validation.columns)) {
                    if (connectionFieldErrors.hasOwnProperty(column)) {
                        connectionFieldErrors[column] = errors[0]
                    } else {
                        // Add validation errors for columns that don't have form inputs to the general error list
                        connectionTestErrors.value = [...connectionTestErrors.value, `${column}: ${errors[0]}`]
                    }
                }
                if (response.validation.non_column && response.validation.non_column.length > 0) {
                    connectionTestErrors.value = [...connectionTestErrors.value, ...response.validation.non_column]
                }
            }

            // Only add general API errors to connectionTestErrors
            // Connection test specific errors are handled by ConnectionTestResult component
            if (response.errors && response.errors.length > 0) {
                connectionTestErrors.value = [...connectionTestErrors.value, ...response.errors]
            }
        }
    } catch (error) {
        toast.add({
            severity: 'error',
            summary: 'Connection Test Failed',
            detail: 'Unable to test connection',
            life: 3000,
        })
    } finally {
        connectionTestIsActive.value = false
        emit('connectionTestEnded')
    }
}

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

// Emit initial connection data on mount so parent can capture it
onMounted(() => {
    emit('connectionDataValidated', { ...connectionData })
})
</script>
