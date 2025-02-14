<template>
    <div class="mb-14">
        <div class="flex flex-row">
            <div class="flex flex-col justify-start text-nowrap">
                <span class="font-bold text-3xl">
                    <i class="pi pi-database text-3xl mr-1"></i>
                    <span class="text-gray-400">Sources: </span>
                    <span v-if="source">
                        Edit source: {{ source.slug }}
                    </span>
                    <span v-else>
                        Create new source
                    </span>
                </span>
            </div>
            <div class="flex flex-row w-full justify-end items-center">
                <div>
                    <Button severity="primary" icon="pi pi-check" size="small" :label="submitButtonLabel"
                        @click="handleFormSubmit" :loading="submitButtonLoading" :disabled="!connectionTestPassed" />
                </div>
            </div>
        </div>
    </div>
    <ConnectionStep :source="source" :startConnectionTest="startConnectionTest" @connectionDataValidated="onConnectionDataValidated"
        @connectionTestStarted="onConnectionTestStarted" @connectionDataChanged="onConnectionDataChanged">
    </ConnectionStep>
    <div v-if="connectionTestPassed">
        <SourceStep :schemaFields="schemaFields" :connectionData="connectionData" :sourceFormErrors="sourceFormErrors"
            @sourceDynamicFieldAdded="onSourceDynamicFieldAdded"
            @sourceDynamicFieldRemoved="onSourceDynamicFieldRemoved" @sourceFormDataChanged="onSourceFormDataChanged"
            :source="source">
        </SourceStep>
    </div>
    <div class="flex pt-6 pb-6 justify-end">
        <Button severity="primary" icon="pi pi-check" size="small" :label="submitButtonLabel" @click="handleFormSubmit"
            :loading="submitButtonLoading" :disabled="!connectionTestPassed" />
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useToast } from 'primevue'
import { useRouter } from 'vue-router'

import Button from 'primevue/button'

import SourceStep from '@/components/sources/new/SourceStep.vue'
import ConnectionStep from '@/components/sources/new/ConnectionStep.vue'
import { SourceService } from '@/sdk/services/Source'

const props = defineProps(['source', 'startConnectionTest'])
const toast = useToast()
const router = useRouter()

const sourceSrv = new SourceService()

const submitButtonLabel = computed(() => {
    if (props.source) {
        return 'Save'
    } else {
        return 'Create'
    }
})

const connectionTestPassed = ref(false)

const schemaFields = ref([])
const connectionData = ref(null)

const submitButtonLoading = ref(false)

const getInitialSourceFormErrors = () => {
    let data = {
        'slug': '',
        'name': '',
        'description': '',
        'time_field': '',
        // 'uniq_field': '',
        'severity_field': '',
        'default_chosen_fields': '',
        'fields': {},
    }
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
        suggest: '',
        values: '',
    }
}

const sourceFormErrors = ref(getInitialSourceFormErrors())
const sourceFormData = ref({})

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

const onSourceFormDataChanged = (data) => {
    sourceFormData.value = data
}

const onSourceDynamicFieldAdded = (fieldName) => {
    sourceFormErrors.value.fields[fieldName] = getSourceDynamicFieldDefaultErrors()
}

const onSourceDynamicFieldRemoved = (fieldName) => {
    delete sourceFormErrors.value.fields[fieldName]
}

const resetErrors = () => {
    for (const field in sourceFormErrors.value) {
        if (field == 'fields') {
            sourceFormErrors.value[field] = {}
        } else {
            sourceFormErrors.value[field] = ""
        }
    }
}

const handleFormSubmit = async () => {
    resetErrors()
    submitButtonLoading.value = true

    let data = Object.assign({}, sourceFormData.value)
    data['connection'] = connectionData.value
    data['kind'] = 'clickhouse'
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
                            sourceFormErrors.value.fields[field][key] = value.join(', ')
                        }
                    }

                }
                sourceFormErrors.value[field] = response.validation.fields[field].join(', ')
            }
        } else {
            router.push({ name: 'source', params: { sourceSlug: response.data.slug } }).then(() => response.sendToastMessages(toast))
        }
    }
}
</script>