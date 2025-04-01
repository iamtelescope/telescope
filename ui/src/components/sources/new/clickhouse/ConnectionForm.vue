<template>
    <Fieldset class="text-wrap" :class="'mb-9'">
        <template #legend>
            <span class="font-bold">Connection data</span>
        </template>
        <div class="flex flex-col w-full flex-wrap gap-4">
            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <FloatLabel variant="on">
                        <InputText id="connection_host" v-model="connectionData.host" fluid
                            :disabled="connectionTestIsActive" :invalid="hasError('host')" />
                        <label for="connection_label">Host</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.host" />
                </div>
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on">
                        <InputNumber id="connection_port" :useGrouping="false" :min="1" :max="65535"
                            v-model="connectionData.port" fluid :disabled="connectionTestIsActive"
                            :invalid="hasError('port')" />
                        <label for="connection_port">Port</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.port" />
                </div>
            </div>
            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <FloatLabel variant="on">
                        <InputText id="connection_user" v-model="connectionData.user" fluid
                            :disabled="connectionTestIsActive" :invalid="hasError('user')" />
                        <label for="connection_user">User</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.user" />
                </div>
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on">
                        <Password v-model="connectionData.password" toggleMask :feedback="false"
                            inputId="connection_passoword" fluid :disabled="connectionTestIsActive"
                            :invalid="hasError('password')" />
                        <label for="connection_password">Password</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.password" />
                </div>
            </div>
            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <FloatLabel variant="on">
                        <InputText id="connection_database" v-model="connectionData.database" fluid
                            :disabled="connectionTestIsActive" :invalid="hasError('database')" />
                        <label for="connection_database">Database</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.database" />
                </div>
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on" class="w-full">
                        <InputText id="connection_table" v-model="connectionData.table" fluid
                            :disabled="connectionTestIsActive" :invalid="hasError('table')" />
                        <label for="connection_table">Table</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.table" />
                </div>
            </div>
            <div class="flex flex-row">
                <div class="flex flex-col">
                    <div class="flex flex-row items-center">
                        <label for="connection_ssl" class="mr-2 ml-2 font-bold">Use SSL</label>
                        <ToggleSwitch id="connection_ssl" v-model="connectionData.ssl"
                            :disabled="connectionTestIsActive" :invalid="hasError('ssl')" />
                    </div>
                    <ErrorText :text="connectionFieldErrors.ssl" />
                </div>
            </div>
        </div>
        <ConnectionTestResult :data="connectionTestData" :loading="connectionTestIsActive" v-if="connectionTestCalled">
        </ConnectionTestResult>
        <div class="flex pt-5 justify-end">
            <Button label="Validate connection & load schema" icon="pi pi-sync" size="small"
                @click="handleTestConnection" :loading="connectionTestIsActive" />
        </div>
    </Fieldset>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'

import { useToast } from 'primevue/usetoast'
import FloatLabel from 'primevue/floatlabel'
import Fieldset from 'primevue/fieldset'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import InputNumber from 'primevue/inputnumber'
import ConnectionTestResult from '@/components/sources/new/ConnectionTestResult.vue'

import ErrorText from '@/components/common/ErrorText.vue'
import { SourceService } from '@/sdk/services/Source'

const emit = defineEmits(['connectionDataValidated', 'connectionTestStarted', 'connectionDataChanged'])
const props = defineProps(['source', 'startConnectionTest'])

const toast = useToast()
const sourceSrv = new SourceService()
const kind = 'clickhouse'

const connectionTestIsActive = ref(false)
const connectionTestCalled = ref(false)
const connectionTestData = ref(null)
const connectionTestPassed = ref(false)

const getInitialConnectionData = () => {
    let data = {
        'host': "localhost",
        'port': 9000,
        'user': "default",
        'password': "",
        'database': "",
        'table': "",
        'ssl': false,
    }
    if (props.source) {
        data = props.source.connection
    }
    return data
}

const connectionData = reactive(getInitialConnectionData())

const connectionFieldErrors = reactive({
    'host': "",
    'port': "",
    'user': "",
    'password': "",
    'database': "",
    'table': "",
    'ssl': "",
})

const hasError = (key) => {
    return connectionFieldErrors[key] != ""
}

const resetErrors = () => {
    for (const field in connectionFieldErrors) {
        connectionFieldErrors[field] = ""
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
