<template>
    <div class="flex flex-col">
        <div class="flex mb-4" :class="showBack ? 'justify-between' : 'justify-end'">
            <Button
                v-if="showBack"
                label="Back"
                severity="secondary"
                size="small"
                icon="pi pi-arrow-left"
                @click="emit('prev')"
            />
            <Button
                label="Next"
                icon="pi pi-arrow-right"
                size="small"
                iconPos="right"
                @click="handleNext"
                :disabled="!isValid"
            />
        </div>
        <div class="flex flex-col gap-3">
            <div>
                <label for="connection_kind" class="font-medium">Type *</label>
                <Select
                    id="connection_kind"
                    v-model="selectedKind"
                    :options="connectionKindOptions"
                    :disabled="!!connection"
                    optionLabel="label"
                    optionValue="value"
                    placeholder="Select a connection type..."
                    class="w-full mt-1"
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
            </div>

            <!-- ClickHouse specific columns -->
            <template v-if="selectedKind === 'clickhouse'">
                <ClickHouseConnectionStep
                    ref="clickhouseFormRef"
                    :connection="connection"
                    :validationErrors="{}"
                    @connectionDataValidated="onConnectionDataChanged"
                    @connectionDataChanged="onConnectionDataChanged"
                />
            </template>

            <!-- StarRocks specific columns -->
            <template v-if="selectedKind === 'starrocks'">
                <StarRocksConnectionStep
                    ref="starrocksFormRef"
                    :connection="connection"
                    :validationErrors="{}"
                    @connectionDataValidated="onConnectionDataChanged"
                    @connectionDataChanged="onConnectionDataChanged"
                />
            </template>

            <!-- Docker specific columns -->
            <template v-if="selectedKind === 'docker'">
                <DockerConnectionStep
                    ref="dockerFormRef"
                    :connection="connection"
                    :validationErrors="{}"
                    @connectionDataValidated="onConnectionDataChanged"
                    @connectionDataChanged="onConnectionDataChanged"
                />
            </template>

            <!-- Kubernetes specific columns -->
            <template v-if="selectedKind === 'kubernetes'">
                <KubernetesConnectionStep
                    ref="kubernetesFormRef"
                    :connection="connection"
                    :validationErrors="{}"
                    @connectionDataValidated="onConnectionDataChanged"
                    @connectionDataChanged="onConnectionDataChanged"
                />
            </template>

            <!-- Test Connection -->
            <div v-if="selectedKind && connectionData && Object.keys(connectionData).length > 0">
                <div class="flex justify-end">
                    <Button
                        label="Test connectivity"
                        icon="pi pi-link"
                        size="small"
                        severity="secondary"
                        @click="handleTestConnection"
                        :loading="testConnectionLoading"
                    />
                </div>
                <ConnectionTestResult
                    v-if="testResult"
                    :data="testResult"
                    :loading="testConnectionLoading"
                    class="mt-4"
                />
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Button, Select } from 'primevue'
import { useToast } from 'primevue/usetoast'
import ClickHouseConnectionStep from '@/components/connections/new/clickhouse/ConnectionForm.vue'
import StarRocksConnectionStep from '@/components/connections/new/starrocks/ConnectionForm.vue'
import DockerConnectionStep from '@/components/connections/new/docker/ConnectionForm.vue'
import KubernetesConnectionStep from '@/components/connections/new/kubernetes/ConnectionForm.vue'
import ConnectionTestResult from '@/components/connections/new/ConnectionTestResult.vue'
import { ConnectionService } from '@/sdk/services/connection'

const props = defineProps({
    modelValue: Object,
    connection: Object,
    showBack: {
        type: Boolean,
        default: true,
    },
})
const emit = defineEmits(['prev', 'next', 'update:modelValue', 'testResult'])

const connectionSrv = new ConnectionService()
const toast = useToast()

const connectionKindOptions = [
    { label: 'ClickHouse', value: 'clickhouse' },
    { label: 'StarRocks', value: 'starrocks' },
    { label: 'Docker', value: 'docker' },
    { label: 'Kubernetes', value: 'kubernetes' },
]

const selectedKind = ref(props.modelValue?.kind || props.connection?.kind || null)
const connectionData = ref(props.modelValue?.data || {})
const testConnectionLoading = ref(false)
const testResult = ref(null)

const clickhouseFormRef = ref(null)
const starrocksFormRef = ref(null)
const dockerFormRef = ref(null)
const kubernetesFormRef = ref(null)

const getConnectionTypeLabel = (value) => {
    const option = connectionKindOptions.find((opt) => opt.value === value)
    return option ? option.label : value
}

const isValid = computed(() => {
    return selectedKind.value && connectionData.value && Object.keys(connectionData.value).length > 0
})

const validateForm = () => {
    if (!selectedKind.value) {
        toast.add({
            severity: 'error',
            summary: 'Validation Error',
            detail: 'Please select a connection type',
            life: 3000,
        })
        return false
    }

    // Validate the appropriate form based on selected kind
    if (selectedKind.value === 'clickhouse' && clickhouseFormRef.value) {
        return clickhouseFormRef.value.validate()
    }

    if (selectedKind.value === 'starrocks' && starrocksFormRef.value) {
        return starrocksFormRef.value.validate()
    }

    if (selectedKind.value === 'docker' && dockerFormRef.value) {
        return dockerFormRef.value.validate()
    }
    if (selectedKind.value === 'kubernetes' && kubernetesFormRef.value) {
        return kubernetesFormRef.value.validate()
    }

    return true
}

watch(
    () => props.modelValue,
    (newValue) => {
        if (newValue) {
            selectedKind.value = newValue.kind
            connectionData.value = newValue.data || {}
        }
    },
    { immediate: true, deep: true },
)

const onConnectionDataChanged = (data) => {
    connectionData.value = data
    // Update parent's v-model
    emit('update:modelValue', {
        kind: selectedKind.value,
        data: data,
    })
}

const handleTestConnection = async () => {
    // Validate form before testing
    if (!validateForm()) {
        return
    }

    testConnectionLoading.value = true

    try {
        const response = await connectionSrv.testConnection(selectedKind.value, connectionData.value)

        if (response.result) {
            if (response.validation && !response.validation.result) {
                let errorMessages = []
                if (response.validation.columns) {
                    for (const [column, errors] of Object.entries(response.validation.columns)) {
                        errorMessages.push(`${column}: ${errors.join(', ')}`)
                    }
                }
                testResult.value = {
                    data: {
                        result: false,
                        error: errorMessages.length > 0 ? errorMessages.join('; ') : 'Validation failed',
                    },
                }
            } else if (response.data && response.data.result === true) {
                testResult.value = {
                    data: response.data,
                }
                // Emit test result for use in review step
                emit('testResult', response.data)
            } else {
                let errorMessage = 'Connection failed'
                if (response.data?.error) {
                    errorMessage = response.data.error
                } else if (response.errors && response.errors.length > 0) {
                    errorMessage = response.errors.join('; ')
                }
                testResult.value = {
                    data: {
                        result: false,
                        error: errorMessage,
                    },
                }
            }
        } else {
            testResult.value = {
                data: {
                    result: false,
                    error: response.errors?.join('; ') || 'Request failed',
                },
            }
        }
    } catch (error) {
        testResult.value = {
            data: {
                result: false,
                error: error.response?.data?.error || error.message || 'Unable to test connection',
            },
        }
    } finally {
        testConnectionLoading.value = false
    }
}

const handleNext = () => {
    if (validateForm()) {
        emit('update:modelValue', {
            kind: selectedKind.value,
            data: connectionData.value,
        })
        emit('next')
    }
}
</script>
