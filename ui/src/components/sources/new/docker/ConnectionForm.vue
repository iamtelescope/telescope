<template>
    <Fieldset class="text-wrap" :class="'mb-9'">
        <template #legend>
            <span class="font-bold">Connection data</span>
        </template>
        <div class="flex flex-col w-full flex-wrap gap-4">
            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <FloatLabel variant="on">
                        <InputText
                            id="connection_address"
                            v-model="connectionData.address"
                            fluid
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('address')"
                        />
                        <label for="connection_label">Address</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.address" />
                </div>
            </div>
        </div>
        <ConnectionTestResult :data="connectionTestData" :loading="connectionTestIsActive" v-if="connectionTestCalled">
        </ConnectionTestResult>
        <div class="flex pt-5 justify-end">
            <Button
                label="Validate connection"
                icon="pi pi-sync"
                size="small"
                @click="handleTestConnection"
                :loading="connectionTestIsActive"
            />
        </div>
    </Fieldset>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'

import { useToast } from 'primevue/usetoast'
import FloatLabel from 'primevue/floatlabel'
import Fieldset from 'primevue/fieldset'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ConnectionTestResult from '@/components/sources/new/ConnectionTestResult.vue'

import ErrorText from '@/components/common/ErrorText.vue'
import { SourceService } from '@/sdk/services/source'

const emit = defineEmits(['connectionDataValidated', 'connectionTestStarted', 'connectionDataChanged'])
const props = defineProps(['source', 'startConnectionTest'])

const toast = useToast()
const sourceSrv = new SourceService()
const kind = 'docker'

const connectionTestIsActive = ref(false)
const connectionTestCalled = ref(false)
const connectionTestData = ref(null)
const connectionTestPassed = ref(false)

const getInitialConnectionData = () => {
    let data = {
        address: 'unix:///var/run/docker.sock',
    }
    if (props.source) {
        data = props.source.connection
    }
    return data
}

const connectionData = reactive(getInitialConnectionData())

const connectionFieldErrors = reactive({
    address: '',
})

const hasError = (key) => {
    return connectionFieldErrors[key] != ''
}

const resetErrors = () => {
    for (const field in connectionFieldErrors) {
        connectionFieldErrors[field] = ''
    }
}

const handleTestConnection = async () => {
    resetErrors()
    emit('connectionTestStarted')
    connectionTestCalled.value = true
    connectionTestPassed.value = false
    connectionTestIsActive.value = true
    let response = await sourceSrv.testConnection(kind, connectionData)
    connectionTestIsActive.value = false
    response.sendToast(toast)
    if (response.result) {
        connectionTestData.value = response.data
        connectionTestPassed.value = true
        if (!response.validation.result) {
            connectionTestCalled.value = false
            for (const field in response.validation.fields) {
                connectionFieldErrors[field] = response.validation.fields[field].join(', ')
            }
        } else {
            let fields = []
            if (response.data.schema.result) {
                fields = response.data.schema.data
            }
            emit('connectionDataValidated', Object.assign({}, connectionData), fields)
        }
    }
}

watch(connectionData, () => {
    emit('connectionDataChanged')
})

onMounted(() => {
    if (props.startConnectionTest) {
        handleTestConnection()
    }
})
</script>
