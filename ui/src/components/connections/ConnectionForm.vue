<template>
    <Content>
        <template #header>
            <Header>
                <template #title> <Cable class="mr-3 w-8 h-8" /> Connections</template>
            </Header>
        </template>
        <template #content>
            <DataView>
                <div class="flex flex-col max-w-[1000px]">
                    <Header>
                        <template #title>
                            <span v-if="connection">Edit connection: {{ connection.name }}</span>
                            <span v-else>New</span>
                        </template>
                    </Header>
                    <div class="mt-4">
                        <ContentBlock header="General">
                            <div class="p-4 flex flex-col gap-4">
                                <div>
                                    <FloatLabel variant="on">
                                        <Select
                                            id="connection_kind"
                                            v-model="formData.kind"
                                            fluid
                                            :options="connectionKindOptions"
                                            :disabled="connection != null"
                                            optionLabel="label"
                                            optionValue="value"
                                            :invalid="hasError('kind')"
                                        >
                                            <template #value="{ value }">
                                                <div v-if="value" class="flex items-center">
                                                    <img
                                                        :src="require(`@/assets/${value}.png`)"
                                                        height="20px"
                                                        width="20px"
                                                        class="mr-2"
                                                        :title="value"
                                                    />
                                                    {{ getConnectionTypeLabel(value) }}
                                                </div>
                                            </template>
                                            <template #option="{ option }">
                                                <div class="flex items-center">
                                                    <img
                                                        :src="require(`@/assets/${option.value}.png`)"
                                                        height="20px"
                                                        width="20px"
                                                        class="mr-2"
                                                        :title="option.value"
                                                    />
                                                    {{ option.label }}
                                                </div>
                                            </template>
                                        </Select>
                                        <label for="connection_kind">Kind *</label>
                                    </FloatLabel>
                                    <ErrorText :text="columnErrors.kind" />
                                </div>

                                <div>
                                    <FloatLabel variant="on">
                                        <InputText
                                            id="connection_name"
                                            v-model="formData.name"
                                            fluid
                                            :invalid="hasError('name')"
                                            @keyup.enter="handleFormSubmit"
                                        />
                                        <label for="connection_name">Name *</label>
                                    </FloatLabel>
                                    <ErrorText :text="columnErrors.name" />
                                </div>

                                <div>
                                    <FloatLabel variant="on">
                                        <InputText
                                            id="connection_description"
                                            v-model="formData.description"
                                            fluid
                                            :invalid="hasError('description')"
                                            @keyup.enter="handleFormSubmit"
                                        />
                                        <label for="connection_description">Description</label>
                                    </FloatLabel>
                                    <ErrorText :text="columnErrors.description" />
                                </div>
                            </div>
                        </ContentBlock>

                        <ClickHouseConnectionStep
                            v-if="formData.kind === 'clickhouse'"
                            class="mt-4"
                            ref="connectionFormRef"
                            :connection="connection"
                            :validationErrors="connectionDataValidationErrors"
                            @connectionDataValidated="onConnectionDataChanged"
                            @connectionDataChanged="onConnectionDataChanged"
                        />
                        <StarRocksConnectionStep
                            v-else-if="formData.kind === 'starrocks'"
                            class="mt-4"
                            ref="connectionFormRef"
                            :connection="connection"
                            :validationErrors="connectionDataValidationErrors"
                            @connectionDataValidated="onConnectionDataChanged"
                            @connectionDataChanged="onConnectionDataChanged"
                        />
                        <DockerConnectionStep
                            v-else-if="formData.kind === 'docker'"
                            class="mt-4"
                            ref="connectionFormRef"
                            :connection="connection"
                            :validationErrors="connectionDataValidationErrors"
                            @connectionDataValidated="onConnectionDataChanged"
                            @connectionDataChanged="onConnectionDataChanged"
                        />
                        <KubernetesConnectionStep
                            v-else-if="formData.kind === 'kubernetes'"
                            class="mt-4"
                            ref="connectionFormRef"
                            :connection="connection"
                            :validationErrors="connectionDataValidationErrors"
                            @connectionDataValidated="onConnectionDataChanged"
                            @connectionDataChanged="onConnectionDataChanged"
                        />

                        <ConnectionTestResult :data="testResult" :loading="testConnectionLoading" v-if="testResult" />

                        <div class="flex flex-row justify-end w-full mt-4 gap-3">
                            <Button
                                v-if="formData.kind"
                                label="Test connectivity"
                                icon="pi pi-link"
                                size="small"
                                severity="secondary"
                                @click="handleTestConnection"
                                :loading="testConnectionLoading"
                            />
                            <Button
                                severity="primary"
                                icon="pi pi-check"
                                size="small"
                                :label="submitButtonLabel"
                                @click="handleFormSubmit"
                                :loading="submitButtonLoading"
                                :disabled="false"
                            />
                        </div>
                    </div>
                </div>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useToast } from 'primevue'
import { useRouter } from 'vue-router'
import { Cable } from 'lucide-vue-next'

import { Button, Select, InputText, FloatLabel } from 'primevue'

import Content from '@/components/common/Content.vue'
import DataView from '@/components/common/DataView.vue'
import Header from '@/components/common/Header.vue'
import ClickHouseConnectionStep from '@/components/connections/new/clickhouse/ConnectionForm.vue'
import StarRocksConnectionStep from '@/components/connections/new/starrocks/ConnectionForm.vue'
import DockerConnectionStep from '@/components/connections/new/docker/ConnectionForm.vue'
import KubernetesConnectionStep from '@/components/connections/new/kubernetes/ConnectionForm.vue'
import ConnectionTestResult from '@/components/connections/new/ConnectionTestResult.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'

import { ConnectionService } from '@/sdk/services/connection'

const props = defineProps(['connection', 'startConnectionTest'])
const toast = useToast()
const router = useRouter()

const connectionKindOptions = [
    { label: 'ClickHouse', value: 'clickhouse' },
    { label: 'StarRocks', value: 'starrocks' },
    { label: 'Docker', value: 'docker' },
    { label: 'Kubernetes', value: 'kubernetes' },
]

const connectionSrv = new ConnectionService()

const submitButtonLabel = computed(() => {
    if (props.connection) {
        return 'Save'
    } else {
        return 'Create'
    }
})

const submitButtonLoading = ref(false)
const testConnectionLoading = ref(false)
const testResult = ref(null)

const formData = ref({
    name: props.connection?.name || '',
    description: props.connection?.description || '',
    kind: props.connection?.kind || null,
})

const connectionData = ref({}) // Connection-specific data from child components

// Basic errors for main form columns
const columnErrors = ref({
    name: '',
    description: '',
    kind: '',
})

const connectionDataValidationErrors = ref({})

const hasError = (column) => {
    return columnErrors.value[column] !== ''
}

const connectionFormRef = ref(null)

const getConnectionTypeLabel = (value) => {
    const option = connectionKindOptions.find((opt) => opt.value === value)
    return option ? option.label : value
}

const onConnectionDataChanged = (data) => {
    connectionData.value = data
}

const handleTestConnection = async () => {
    if (!connectionFormRef.value) {
        return
    }

    if (!connectionData.value || Object.keys(connectionData.value).length === 0) {
        testResult.value = {
            data: {
                result: false,
                error: 'Please fill in connection details first',
            },
        }
        return
    }

    const currentConnectionData = connectionData.value

    testConnectionLoading.value = true

    try {
        const response = await connectionSrv.testConnection(formData.value.kind, currentConnectionData)

        if (response.result) {
            // Check if validation failed
            if (response.validation && !response.validation.result) {
                // Extract validation errors
                let errorMessages = []

                if (response.validation.columns) {
                    for (const [column, errors] of Object.entries(response.validation.columns)) {
                        errorMessages.push(`${column}: ${errors.join(', ')}`)
                    }
                }

                if (response.validation.non_column && response.validation.non_column.length > 0) {
                    errorMessages.push(...response.validation.non_column)
                }

                testResult.value = {
                    data: {
                        result: false,
                        error: errorMessages.length > 0 ? errorMessages.join('; ') : 'Validation failed',
                    },
                }
            } else if (response.data && response.data.result === true) {
                testResult.value = {
                    data: {
                        result: true,
                    },
                }
            } else {
                // Extract detailed error information from connection test failure
                let errorMessage = 'Connection failed'

                if (response.data?.error) {
                    errorMessage = response.data.error
                } else if (response.data?.message) {
                    errorMessage = response.data.message
                } else if (response.data?.detail) {
                    errorMessage = response.data.detail
                } else if (response.errors && response.errors.length > 0) {
                    errorMessage = response.errors.join('; ')
                } else if (response.data && typeof response.data === 'string') {
                    errorMessage = response.data
                }

                testResult.value = {
                    data: {
                        result: false,
                        error: errorMessage,
                    },
                }
            }
        } else {
            // Extract error details from failed request
            let errorMessage = 'Request failed'

            if (response.errors && response.errors.length > 0) {
                errorMessage = response.errors.join('; ')
            } else if (response.message) {
                errorMessage = response.message
            } else if (response.detail) {
                errorMessage = response.detail
            }

            testResult.value = {
                data: {
                    result: false,
                    error: errorMessage,
                },
            }
        }
    } catch (error) {
        let errorMessage = 'Unable to test connection'

        if (error.response?.data?.error) {
            errorMessage = error.response.data.error
        } else if (error.response?.data?.message) {
            errorMessage = error.response.data.message
        } else if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
        } else if (error.message) {
            errorMessage = `Network error: ${error.message}`
        }

        testResult.value = {
            data: {
                result: false,
                error: errorMessage,
            },
        }
    } finally {
        testConnectionLoading.value = false
    }
}

const resetErrors = () => {
    for (const column in columnErrors.value) {
        columnErrors.value[column] = ''
    }
    connectionDataValidationErrors.value = {}
}

const handleFormSubmit = async () => {
    resetErrors()
    submitButtonLoading.value = true

    try {
        const submitData = {
            name: formData.value.name,
            description: formData.value.description,
            kind: formData.value.kind,
            data: connectionData.value,
        }

        let response
        if (props.connection) {
            response = await connectionSrv.update(props.connection.id, submitData)
        } else {
            response = await connectionSrv.create(submitData)
        }

        if (response.result) {
            if (response.validation && !response.validation.result) {
                // Handle validation errors from server
                for (const [column, errors] of Object.entries(response.validation.columns)) {
                    if (columnErrors.value.hasOwnProperty(column)) {
                        // Top-level connection columns (name, description, kind)
                        columnErrors.value[column] = errors.join(', ')
                    } else {
                        // Connection data columns (host, port, user, etc.) - pass to child component
                        connectionDataValidationErrors.value[column] = errors
                    }
                }
            } else {
                toast.add({
                    severity: 'success',
                    summary: 'Success',
                    detail: props.connection ? 'Connection updated successfully' : 'Connection created successfully',
                    life: 3000,
                })
                if (props.connection) {
                    router.push(`/connections/${props.connection.id}`)
                } else {
                    router.push('/connections')
                }
            }
        } else {
            toast.add({
                severity: 'error',
                summary: 'Error',
                detail: 'Failed to save connection',
                life: 3000,
            })
        }
    } catch (error) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to save connection',
            life: 3000,
        })
    } finally {
        submitButtonLoading.value = false
    }
}
</script>
