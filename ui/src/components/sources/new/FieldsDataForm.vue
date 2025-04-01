<template>
    <div class="flex flex-col w-full">
        <Fieldset class="text-wrap">
            <template #legend>
                <span class="font-bold">Fields setup</span>
            </template>
            <div class="flex flex-col w-full">
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on">
                        <Select id="time_field" optionLabel="name" v-model="formData['time_field']"
                            :invalid="formErrors['time_field'] != ''" fluid editable
                            :options="sourceStaticFieldChoices['time_field']" optionValue="name" showClear />
                        <label for="time_field">Time field</label>
                    </FloatLabel>
                    <ErrorText :text="formErrors['time_field']" />
                </div>
                <div class="flex flex-col w-full mt-4">
                    <FloatLabel variant="on">
                        <Select id="severity_field" optionLabel="name" v-model="formData['severity_field']"
                            :invalid="formErrors['severity_field'] != ''" fluid editable
                            :disabled="!settings.fields.severity.editable"
                            :options="sourceStaticFieldChoices['severity_field']" optionValue="name" showClear />
                        <label for="severity_field">Severity field</label>
                    </FloatLabel>
                    <ErrorText :text="formErrors['severity_field']" />
                </div>
                <div class="flex flex-col w-full mt-4">
                    <FloatLabel variant="on">
                        <InputText id="default_chosen_fields" v-model="formData['default_chosen_fields']" fluid
                            :invalid="formErrors['default_chosen_fields'] != ''" />
                        <label for="default_chosen_fields">Default chosen fields</label>
                    </FloatLabel>
                    <ErrorText :text="formErrors['default_chosen_fields']" />
                </div>
                <div class="flex flex-row justify-end mb-6 mt-7">
                    <Button class="mr-2" severity="primary" icon="pi pi-download" label="Load fields from schema"
                        size="small" @click="handleLoadSourceDynamicFieldsFromSchema"
                        :disabled="schemaFields.length == 0" />
                    <Button severity="primary" icon="pi pi-plus" label="Add manually" size="small"
                        @click="newSourceDynamicFieldDialogData.visible = true" v-if="settings.allowAddManualFields" />
                </div>

                <BorderCard v-for="field in sourceDynamicFieldsList" :key="field.name" class="mb-4 pb-2 pl-4 pr-4">
                    <div class="flex flex-row w-full pb-6">
                        <div class="flex w-full justify-start">
                            <span class="font-bold text-lg">{{ field.name }}</span>
                        </div>
                        <div class="flex w-full justify-end">
                            <span class="cursor-pointer text-gray-400 hover:text-gray-900"
                                @click="handleRemoveSourceDynamicField(field.name)">
                                <i class="pi pi-times"></i>
                            </span>
                        </div>
                    </div>
                    <div class="flex flex-row w-full items-center mb-4">
                        <div class="flex">
                            <span>Autocomplete</span>
                        </div>
                        <div class="flex pl-2">
                            <ToggleSwitch :id="field.name + '_autocomplete'"
                                v-model="formData['fields'][field.name]['autocomplete']" />
                        </div>
                        <div class="flex pl-6">
                            <span>Suggest</span>
                        </div>
                        <div class="flex pl-2">
                            <ToggleSwitch :id="field.name + '_suggest'"
                                v-model="formData['fields'][field.name]['suggest']" />
                        </div>
                        <div class="flex pl-6">
                            <span>Treat as JSON String</span>
                        </div>
                        <div class="flex pl-2">
                            <ToggleSwitch :id="field.name + '_jsonstring'"
                                v-model="formData['fields'][field.name]['jsonstring']" />
                        </div>
                        <div class="flex pl-6">
                            <span>Allow in GROUP BY</span>
                        </div>
                        <div class="flex pl-2">
                            <ToggleSwitch :id="field.name + '_group_by'"
                                v-model="formData['fields'][field.name]['group_by']" />
                        </div>
                    </div>
                    <div class="flex flex-row w-full items-center mb-4">
                        <div class="flex w-32">
                            <span>Display Name</span>
                        </div>
                        <div class="flex flex-col pl-6 w-96">
                            <InputText :id="field.name + '_display_name'"
                                v-model="formData['fields'][field.name]['display_name']"
                                :invalid="dynamicFieldHasError(field.name, 'display_name')" fluid />
                            <ErrorText :text="formErrors['fields'][field.name]['display_name']" />
                        </div>
                    </div>
                    <div class="flex flex-row w-full items-center mb-4">
                        <div class="flex w-32">
                            <span>Type</span>
                        </div>
                        <div class="flex flex-col pl-6 w-96">
                            <Select :id="field.name + '_type'" fluid v-model="formData['fields'][field.name]['type']"
                                :options="sourceDynamicFieldTypes" :invalid="dynamicFieldHasError(field.name, 'type')"
                                editable filter autoFilterFocus />
                            <ErrorText :text="formErrors['fields'][field.name]['type']" />
                        </div>
                    </div>
                    <div class="flex flex-row w-full items-center mb-4">
                        <div class="flex w-32">
                            <span>Values</span>
                        </div>
                        <div class="flex flex-col pl-6 w-96">
                            <InputText :id="field.name + '_values'" v-model="formData['fields'][field.name]['values']"
                                :invalid="dynamicFieldHasError(field.name, 'values')" fluid />
                            <ErrorText :text="formErrors['fields'][field.name]['values']" />
                        </div>
                    </div>
                </BorderCard>
            </div>
        </Fieldset>
        <Dialog v-model:visible="newSourceDynamicFieldDialogData.visible" modal header="Add field"
            :style="{ width: '25rem' }">
            <div class="flex items-center mb-4">
                <div class="flex flex-col w-full">
                    <FloatLabel variant="on" :invalid="newSourceDynamicFieldDialogData.invalid">
                        <InputText id="new_name" v-model="newSourceDynamicFieldDialogData.value" fluid
                            :invalid="newSourceDynamicFieldDialogData.invalid" />
                        <label for="new_name">Name</label>
                    </FloatLabel>
                    <ErrorText :text="newSourceDynamicFieldDialogData.error" />
                </div>
            </div>
            <div class="flex justify-end gap-2">
                <Button type="button" label="Cancel" severity="secondary"
                    @click="handleNewDynamicFieldDialogClose"></Button>
                <Button type="button" icon="pi pi-check" label="Submit" @click="handleAddSourceDynamicField"></Button>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue'

import { useToast } from 'primevue/usetoast'
import ToggleSwitch from 'primevue/toggleswitch'
import FloatLabel from 'primevue/floatlabel'
import Fieldset from 'primevue/fieldset'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Dialog from 'primevue/dialog'
import BorderCard from '@/components/common/BorderCard.vue'

import ErrorText from '@/components/common/ErrorText.vue'

import { FieldTypes } from '@/utils/constants'

const emit = defineEmits(['formDataChanged', 'dynamicFieldAdded', 'dynamicFieldRemoved'])
const props = defineProps([
    'source',
    'kind',
    'schemaFields',
    'connectionData',
    'formErrors',
    'settings',
])

const toast = useToast()
const getInitialFormData = () => {
    let data = {
        'time_field': props.settings.fields.time.default,
        'severity_field': '',
        'default_chosen_fields': props.settings.fields.defaultChosenFields.default,
        'fields': {},
    }
    if (props.source) {
        data.time_field = props.source.timeField
        data.severity_field = props.source.severityField
        data.default_chosen_fields = props.source.defaultChosenFields?.join(', ')

        for (const [fieldName, fieldData] of Object.entries(props.source.fields)) {
            data.fields[fieldName] = fieldData
        }
    }
    return data
}


const getInitialDynamicFieldsList = () => {
    let data = []
    if (props.source) {
        for (const [fieldName, _] of Object.entries(props.source.fields)) {
            data.push({ 'name': fieldName })
        }
    }
    return data
}

const getSourceDynamicFieldDefaultData = () => {
    return {
        display_name: '',
        type: '',
        autocomplete: false,
        suggest: false,
        jsonstring: false,
        group_by: false,
        values: '',
    }
}

const sourceDynamicFieldTypes = ref(FieldTypes[props.kind])

const sourceStaticFieldChoices = computed(() => {
    let timeFieldChoices = []
    let severityChoices = []

    for (const [fieldName, fieldData] of Object.entries(formData.fields)) {
        let item = Object.assign({ 'name': fieldName }, fieldData)
        let itemType = item.type.toLowerCase()
        if (itemType.includes('datetime') ||
            itemType.includes('datetime64') ||
            itemType.includes('timestamp') ||
            itemType.includes('int64') ||
            itemType.includes('uint64')) {
            timeFieldChoices.push(item);
        } else {
            severityChoices.push(item)
        }
    }
    return {
        time_field: timeFieldChoices,
        severity_field: severityChoices,
    }
})

const formData = reactive(getInitialFormData())
const sourceDynamicFieldsList = ref(getInitialDynamicFieldsList())

const dynamicFieldHasError = (field, prop) => {
    if (props.formErrors.fields[field]?.[prop]) {
        return true
    } else {
        return false
    }
}

const newSourceDynamicFieldDialogData = reactive({
    'invalid': false,
    'value': '',
    'error': '',
    'visible': false,
})

const handleNewDynamicFieldDialogClose = () => {
    newSourceDynamicFieldDialogData.value = ''
    newSourceDynamicFieldDialogData.invalid = false
    newSourceDynamicFieldDialogData.visible = false
}

const handleRemoveSourceDynamicField = (fieldName) => {
    sourceDynamicFieldsList.value = sourceDynamicFieldsList.value.filter((field) => field.name != fieldName);
    emit('dynamicFieldRemoved', fieldName)
    delete formData.fields[fieldName]
}

const handleAddSourceDynamicField = () => {
    let name = newSourceDynamicFieldDialogData.value.trim()
    if (newSourceDynamicFieldDialogData.value == "") {
        newSourceDynamicFieldDialogData.invalid = true
        newSourceDynamicFieldDialogData.error = 'Name is required.'
    } else if (name in formData.fields) {
        newSourceDynamicFieldDialogData.invalid = true
        newSourceDynamicFieldDialogData.error = 'Field with that name already exist.'
    } else {
        newSourceDynamicFieldDialogData.invalid = false
        newSourceDynamicFieldDialogData.value = ''
        newSourceDynamicFieldDialogData.error = ''
        formData.fields[name] = getSourceDynamicFieldDefaultData()
        sourceDynamicFieldsList.value.push({ 'name': name })
        emit('dynamicFieldAdded', name)
        toast.add({ severity: 'success', summary: 'Success', detail: `Added field ${name} to list`, life: 3000 });
        newSourceDynamicFieldDialogData.visible = false
    }
}

const handleLoadSourceDynamicFieldsFromSchema = () => {
    let fieldsAdded = []
    for (const field of props.schemaFields) {
        let data = Object.assign({}, field)
        let name = data.name
        delete data.name
        if (!(name in formData.fields)) {
            formData.fields[name] = data
            sourceDynamicFieldsList.value.push({ 'name': name })
            fieldsAdded.push(name)
            emit('dynamicFieldAdded', name)
        }
    }
    if (fieldsAdded.length != 0) {
        let message = `Added ${fieldsAdded.length} to list: ${fieldsAdded.join(', ')}`
        toast.add({ severity: 'success', summary: 'Success', detail: message, life: 3000 });
    } else {
        toast.add({ severity: 'warn', summary: 'Warning', detail: 'no fields were added', life: 3000 });
    }
}

watch(formData, () => {
    emit('formDataChanged', formData)
})

onMounted(() => {
    if (props.settings.autoLoadFieldsFromSchema) {
        handleLoadSourceDynamicFieldsFromSchema()
    }
})

emit('formDataChanged', formData)

</script>
