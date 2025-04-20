<template>
    <div class="mb-14">
        <div class="flex flex-row">
            <div class="flex flex-col justify-start text-nowrap">
                <span class="font-bold text-3xl">
                    <i class="pi pi-database text-3xl mr-1"></i>
                    <span class="text-gray-400">Sources: </span>
                    <span v-if="source"> Edit source: {{ source.slug }} </span>
                    <span v-else> Create new source </span>
                </span>
            </div>
            <div class="flex flex-row w-full justify-end items-center">
                <div>
                    <Button
                        severity="primary"
                        icon="pi pi-check"
                        size="small"
                        :label="submitButtonLabel"
                        @click="handleFormSubmit"
                        :loading="submitButtonLoading"
                        :disabled="!connectionTestPassed"
                    />
                </div>
            </div>
        </div>
    </div>
    <FloatLabel variant="on" class="mb-6">
        <Select
            id="source_kind"
            v-model="sourceKindSelected"
            fluid
            :options="sourceKindOptions"
            :disabled="source != null"
        />
        <label for="source_kind">Source kind</label>
    </FloatLabel>

    <ClickhouseConnectionStep
        v-if="sourceKindSelected == 'clickhouse'"
        :source="source"
        :startConnectionTest="startConnectionTest"
        @connectionDataValidated="onConnectionDataValidated"
        @connectionTestStarted="onConnectionTestStarted"
        @connectionDataChanged="onConnectionDataChanged"
    >
    </ClickhouseConnectionStep>
    <DockerConnectionStep
        v-else-if="sourceKindSelected == 'docker'"
        :startConnectionTest="startConnectionTest"
        @connectionDataValidated="onConnectionDataValidated"
        @connectionTestStarted="onConnectionTestStarted"
        @connectionDataChanged="onConnectionDataChanged"
    ></DockerConnectionStep>
    <div v-if="connectionTestPassed">
        <CommonDataForm
            :source="source"
            :formErrors="sourceCommonDataFormErrors"
            @formDataChanged="onCommonFormDataChange"
        />
        <FieldsDataForm
            :source="source"
            :schemaFields="schemaFields"
            :kind="sourceKindSelected.value"
            :connectionData="connectionData"
            :formErrors="sourceFieldsDataFormErrors"
            :settings="fieldsSettings"
            @dynamicFieldAdded="onSourceDynamicFieldAdded"
            @dynamicFieldRemoved="onSourceDynamicFieldRemoved"
            @formDataChanged="onSourceFormDataChanged"
        />
    </div>
    <div class="flex pt-6 pb-6 justify-end">
        <Button
            severity="primary"
            icon="pi pi-check"
            size="small"
            :label="submitButtonLabel"
            @click="handleFormSubmit"
            :loading="submitButtonLoading"
            :disabled="!connectionTestPassed"
        />
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useToast } from 'primevue'
import { useRouter } from 'vue-router'

import { Button, Select, FloatLabel } from 'primevue'

import CommonDataForm from '@/components/sources/new/CommonDataForm.vue'
import FieldsDataForm from '@/components/sources/new/FieldsDataForm.vue'
import ClickhouseConnectionStep from '@/components/sources/new/clickhouse/ConnectionForm.vue'
import DockerConnectionStep from '@/components/sources/new/docker/ConnectionForm.vue'

import { SourceService } from '@/sdk/services/Source'

const props = defineProps(['source', 'startConnectionTest'])
const toast = useToast()
const router = useRouter()
const sourceKindSelected = ref(props.source ? props.source.kind : null)
const sourceKindOptions = ['clickhouse', 'docker']

const sourceSrv = new SourceService()

const submitButtonLabel = computed(() => {
    if (props.source) {
        return 'Save'
    } else {
        return 'Create'
    }
})

const formFieldsInitialErrors = {
    common: {
        slug: '',
        name: '',
        description: '',
    },
    fields: {
        time_field: '',
        severity_field: '',
        default_chosen_fields: '',
        fields: {},
    },
}

const connectionTestPassed = ref(false)

const schemaFields = ref([])
const connectionData = ref(null)

const submitButtonLoading = ref(false)

const fieldsSettings = computed(() => {
    let settings = {
        allowAddManualFields: true,
        autoLoadFieldsFromSchema: false,
        fields: {
            time: {
                default: '',
            },
            severity: {
                editable: true,
            },
            defaultChosenFields: {
                default: '',
            },
        },
    }
    if (sourceKindSelected.value == 'docker') {
        settings.autoLoadFieldsFromSchema = props.source ? false : true
        settings.allowAddManualFields = false
        settings.fields.time.default = 'time'
        settings.fields.severity.editable = false
        settings.fields.defaultChosenFields.default = 'container_short_id, stream, message'
    }
    return settings
})

const getInitialSourceCommonDataFormErrors = () => {
    return Object.assign({}, formFieldsInitialErrors.common)
}

const getInitialSourceFieldsDataFormErrors = () => {
    let data = Object.assign({}, formFieldsInitialErrors.fields)
    if (props.source) {
        for (const [key, _] of Object.entries(props.source.fields)) {
            data.fields[key] = getSourceDynamicFieldDefaultErrors()
        }
    }
    return data
}

const getSourceDynamicFieldDefaultErrors = () => {
    return {
        display_name: '',
        type: '',
        autocomplete: '',
        jsonstring: '',
        suggest: '',
        group_by: '',
        values: '',
    }
}

const sourceCommonDataFormErrors = ref(getInitialSourceCommonDataFormErrors())
const sourceFieldsDataFormErrors = ref(getInitialSourceFieldsDataFormErrors())
const sourceCommonData = ref({})
const sourceFieldsData = ref({})

const onConnectionDataValidated = (data, fields) => {
    connectionTestPassed.value = true
    connectionData.value = data
    schemaFields.value = fields
}

const onConnectionTestStarted = () => {
    connectionTestPassed.value = false
}

const onConnectionDataChanged = () => {
    connectionTestPassed.value = false
}

const onCommonFormDataChange = (data) => {
    sourceCommonData.value = data
}

const onSourceFormDataChanged = (data) => {
    sourceFieldsData.value = data
}

const onSourceDynamicFieldAdded = (fieldName) => {
    sourceFieldsDataFormErrors.value.fields[fieldName] = getSourceDynamicFieldDefaultErrors()
}

const onSourceDynamicFieldRemoved = (fieldName) => {
    delete sourceFieldsDataFormErrors.value.fields[fieldName]
}

const resetErrors = () => {
    for (const field in sourceCommonDataFormErrors.value) {
        sourceCommonDataFormErrors.value[field] = ''
    }
    for (const field in sourceFieldsDataFormErrors.value) {
        if (field == 'fields') {
            for (const key in sourceFieldsDataFormErrors.value[field]) {
                sourceFieldsDataFormErrors.value[field][key] = getSourceDynamicFieldDefaultErrors()
            }
        } else {
            sourceFieldsDataFormErrors.value[field] = ''
        }
    }
}

const handleFormSubmit = async () => {
    resetErrors()
    submitButtonLoading.value = true

    let data = Object.assign({}, sourceCommonData.value)
    for (const [key, value] of Object.entries(sourceFieldsData.value)) {
        data[key] = value
    }
    data['connection'] = connectionData.value
    data['kind'] = sourceKindSelected.value

    let response
    if (props.source) {
        response = await sourceSrv.updateSource(props.source.slug, data)
    } else {
        response = await sourceSrv.createSource(data)
    }

    submitButtonLoading.value = false
    response.sendToast(toast)

    if (response.result) {
        if (!response.validation.result) {
            for (const field in response.validation.fields) {
                if (field == 'fields') {
                    for (const name in response.validation.fields.fields) {
                        for (const [key, value] of Object.entries(response.validation.fields.fields[name])) {
                            sourceFieldsDataFormErrors.value.fields[name][key] = value.join(', ')
                        }
                    }
                } else {
                    if (field in formFieldsInitialErrors.common) {
                        sourceCommonDataFormErrors.value[field] = response.validation.fields[field].join(', ')
                    } else {
                        sourceFieldsDataFormErrors.value[field] = response.validation.fields[field].join(', ')
                    }
                }
            }
        } else {
            router
                .push({ name: 'source', params: { sourceSlug: response.data.slug } })
                .then(() => response.sendToastMessages(toast))
        }
    }
}
</script>
