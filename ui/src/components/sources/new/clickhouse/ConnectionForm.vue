<template>
    <Fieldset class="text-wrap" :class="'mb-9'">
        <template #legend>
            <span class="font-medium">Connection data</span>
        </template>
        <div class="flex flex-col w-full flex-wrap gap-4">
            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <FloatLabel variant="on">
                        <InputText id="connection_protocol" v-model="protocol" fluid :disabled="true" />
                        <label for="connection_label">Protocol</label>
                    </FloatLabel>
                </div>
            </div>
            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <FloatLabel variant="on">
                        <InputText
                            id="connection_host"
                            v-model="connectionData.host"
                            fluid
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('host')"
                        />
                        <label for="connection_label">Host</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.host" />
                </div>
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on">
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
                        <label for="connection_port">Port</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.port" />
                </div>
            </div>
            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <FloatLabel variant="on">
                        <InputText
                            id="connection_user"
                            v-model="connectionData.user"
                            fluid
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('user')"
                        />
                        <label for="connection_user">User</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.user" />
                </div>
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on">
                        <Password
                            v-model="connectionData.password"
                            toggleMask
                            :feedback="false"
                            inputId="connection_passoword"
                            fluid
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('password')"
                        />
                        <label for="connection_password">Password</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.password" />
                </div>
            </div>
            <div class="flex flex-row">
                <div class="flex flex-col w-full mr-2">
                    <FloatLabel variant="on">
                        <InputText
                            id="connection_database"
                            v-model="connectionData.database"
                            fluid
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('database')"
                        />
                        <label for="connection_database">Database</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.database" />
                </div>
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on" class="w-full">
                        <InputText
                            id="connection_table"
                            v-model="connectionData.table"
                            fluid
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('table')"
                        />
                        <label for="connection_table">Table</label>
                    </FloatLabel>
                    <ErrorText :text="connectionFieldErrors.table" />
                </div>
            </div>
            <div class="flex flex-row">
                <div class="flex flex-col">
                    <div class="flex flex-row items-center">
                        <label for="connection_ssl" class="mr-2 ml-2 font-medium">Use SSL</label>
                        <ToggleSwitch
                            id="connection_ssl"
                            v-model="connectionData.ssl"
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('ssl')"
                        />
                    </div>
                    <ErrorText :text="connectionFieldErrors.ssl" />
                </div>
                <div class="flex flex-col ml-6" v-if="connectionData.ssl">
                    <div class="flex flex-row items-center">
                        <label for="connection_verify" class="mr-2 ml-2 font-medium">Verify</label>
                        <ToggleSwitch
                            id="connection_verify"
                            v-model="connectionData.verify"
                            :disabled="connectionTestIsActive"
                            :invalid="hasError('verify')"
                        />
                    </div>
                    <ErrorText :text="connectionFieldErrors.verify" />
                </div>
            </div>
            <div v-if="connectionData.ssl">
                <div class="flex flex-col gap-4">
                    <div class="flex flex-col w-full">
                        <FloatLabel variant="on">
                            <Textarea
                                id="connection_ca_certs"
                                v-model="connectionData.ca_certs"
                                fluid
                                :disabled="connectionTestIsActive"
                                :invalid="hasError('ca_certs')"
                            />
                            <label for="connection_ca_certs">CA Certs</label>
                        </FloatLabel>
                        <ErrorText :text="connectionFieldErrors.ca_certs" />
                    </div>
                    <div class="flex flex-col w-full">
                        <FloatLabel variant="on">
                            <Textarea
                                id="connection_certfile"
                                v-model="connectionData.certfile"
                                fluid
                                :disabled="connectionTestIsActive"
                                :invalid="hasError('certfile')"
                            />
                            <label for="connection_certfile">Cert file</label>
                        </FloatLabel>
                        <ErrorText :text="connectionFieldErrors.certfile" />
                    </div>
                    <div class="flex flex-col w-full">
                        <FloatLabel variant="on" class="w-full">
                            <Textarea
                                id="connection_keyfile"
                                v-model="connectionData.keyfile"
                                fluid
                                :disabled="connectionTestIsActive"
                                :invalid="hasError('keyfile')"
                            />
                            <label for="connection_keyfile">Key file</label>
                        </FloatLabel>
                        <ErrorText :text="connectionFieldErrors.keyfile" />
                    </div>
                    <div class="flex flex-row">
                        <div class="flex flex-col w-full mr-2">
                            <FloatLabel variant="on">
                                <InputText
                                    id="connection_ssl_version"
                                    v-model="connectionData.ssl_version"
                                    fluid
                                    :disabled="connectionTestIsActive"
                                    :invalid="hasError('ssl_version')"
                                />
                                <label for="connection_ssl_version">SSL Version</label>
                            </FloatLabel>
                            <ErrorText :text="connectionFieldErrors.ssl_version" />
                        </div>
                        <div class="flex flex-col w-full">
                            <FloatLabel variant="on" class="w-full">
                                <InputText
                                    id="connection_ciphers"
                                    v-model="connectionData.ciphers"
                                    fluid
                                    :disabled="connectionTestIsActive"
                                    :invalid="hasError('ciphers')"
                                />
                                <label for="connection_ciphers">Ciphers</label>
                            </FloatLabel>
                            <ErrorText :text="connectionFieldErrors.ciphers" />
                        </div>
                    </div>
                    <div class="flex flex-row">
                        <div class="flex flex-col w-full mr-2">
                            <FloatLabel variant="on">
                                <InputText
                                    id="connection_server_hostname"
                                    v-model="connectionData.server_hostname"
                                    fluid
                                    :disabled="connectionTestIsActive"
                                    :invalid="hasError('server_hostname')"
                                />
                                <label for="connection_server_hostname">Server Hostname</label>
                            </FloatLabel>
                            <ErrorText :text="connectionFieldErrors.server_hostname" />
                        </div>
                        <div class="flex flex-col w-full">
                            <FloatLabel variant="on" class="w-full">
                                <InputText
                                    id="connection_alt_hosts"
                                    v-model="connectionData.alt_hosts"
                                    fluid
                                    :disabled="connectionTestIsActive"
                                    :invalid="hasError('alt_hosts')"
                                />
                                <label for="connection_alt_hosts">Alt Hosts</label>
                            </FloatLabel>
                            <ErrorText :text="connectionFieldErrors.alt_hosts" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <ConnectionTestResult :data="connectionTestData" :loading="connectionTestIsActive" v-if="connectionTestCalled">
        </ConnectionTestResult>
        <div class="flex pt-5 justify-end">
            <Button
                label="Validate connection & load schema"
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

import { FloatLabel, Fieldset, ToggleSwitch, Button, InputText, Password, InputNumber, Textarea } from 'primevue'

import ConnectionTestResult from '@/components/sources/new/ConnectionTestResult.vue'

import ErrorText from '@/components/common/ErrorText.vue'
import { SourceService } from '@/sdk/services/source'

const emit = defineEmits(['connectionDataValidated', 'connectionTestStarted', 'connectionDataChanged'])
const props = defineProps(['source', 'startConnectionTest'])

const toast = useToast()
const sourceSrv = new SourceService()
const kind = 'clickhouse'
const protocol = ref('native')

const connectionTestIsActive = ref(false)
const connectionTestCalled = ref(false)
const connectionTestData = ref(null)
const connectionTestPassed = ref(false)

const getInitialConnectionData = () => {
    let data = {
        host: 'localhost',
        port: 9000,
        user: 'default',
        password: '',
        database: '',
        table: '',
        ssl: false,
        verify: true,
        ciphers: '',
        ssl_version: '',
        ca_certs: '',
        certfile: '',
        keyfile: '',
        server_hostname: '',
        alt_hosts: '',
    }
    if (props.source) {
        data = props.source.connection
    }
    return data
}

const connectionData = reactive(getInitialConnectionData())

const connectionFieldErrors = reactive({
    host: '',
    port: '',
    user: '',
    password: '',
    database: '',
    table: '',
    ssl: '',
    verify: '',
    ca_certs: '',
    certfile: '',
    keyfile: '',
    ciphers: '',
    ssl_version: '',
    server_hostname: '',
    alt_hosts: '',
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
