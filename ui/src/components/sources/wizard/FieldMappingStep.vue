<template>
    <div class="flex flex-col">
        <div class="flex justify-between mb-4">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button label="Next" icon="pi pi-arrow-right" size="small" iconPos="right" @click="handleNext" />
        </div>
        <div class="flex flex-col gap-1">
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label for="timeField" class="font-medium block mb-2">Time field *</label>
                    <Select
                        id="timeField"
                        v-model="timeField"
                        :options="fieldChoices.time_field"
                        optionLabel="name"
                        optionValue="name"
                        editable
                        showClear
                        class="w-full"
                        :invalid="!timeField && showValidation"
                    />
                    <Message v-if="!timeField && showValidation" severity="error" size="small" variant="simple">
                        Time field is required
                    </Message>
                </div>
                <div>
                    <label for="dateField" class="font-medium block mb-2">Date field</label>
                    <Select
                        id="dateField"
                        v-model="dateField"
                        :options="fieldChoices.date_field"
                        optionLabel="name"
                        optionValue="name"
                        editable
                        showClear
                        class="w-full"
                        :disabled="isDockerConnection || isKubernetesConnection"
                    />
                </div>
                <div>
                    <label for="severityField" class="font-medium block mb-2">Severity field</label>
                    <Select
                        id="severityField"
                        v-model="severityField"
                        :options="fieldChoices.severity_field"
                        optionLabel="name"
                        optionValue="name"
                        showClear
                        class="w-full"
                        :disabled="isDockerConnection || isKubernetesConnection"
                    />
                </div>
                <div>
                    <label for="defaultChosenFields" class="font-medium block mb-2">Default chosen fields *</label>
                    <InputText
                        id="defaultChosenFields"
                        v-model="defaultChosenFields"
                        class="w-full"
                        fluid
                        :invalid="(defaultChosenFieldsError || !defaultChosenFields) && showValidation"
                    />
                    <Message
                        v-if="!defaultChosenFields && showValidation"
                        severity="error"
                        size="small"
                        variant="simple"
                    >
                        Default chosen fields is required
                    </Message>
                    <Message
                        v-else-if="defaultChosenFieldsError && showValidation"
                        severity="error"
                        size="small"
                        variant="simple"
                    >
                        {{ defaultChosenFieldsError }}
                    </Message>
                </div>
            </div>
            <div class="pt-3 flex items-center gap-2">
                <ToggleSwitch v-model="executeQueryOnOpen" inputId="executeQueryOnOpen" />
                <label for="executeQueryOnOpen" class="font-medium">Execute query on open</label>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Button, InputText, Select, Message, ToggleSwitch } from 'primevue'

const props = defineProps(['modelValue', 'fieldsSetupData', 'connectionData'])
const emit = defineEmits(['prev', 'next', 'update:modelValue'])

const showValidation = ref(false)
const timeField = ref(props.modelValue?.time_field || '')
const dateField = ref(props.modelValue?.date_field || '')
const severityField = ref(props.modelValue?.severity_field || '')
const executeQueryOnOpen = ref(props.modelValue?.execute_query_on_open ?? true)

// Convert array to comma-separated string if needed
const getInitialDefaultChosenFields = () => {
    const value = props.modelValue?.default_chosen_fields
    if (!value) return ''
    if (Array.isArray(value)) {
        return value.join(', ')
    }
    return value
}
const defaultChosenFields = ref(getInitialDefaultChosenFields())

const isDockerConnection = computed(() => {
    return props.connectionData?.connection?.kind === 'docker'
})

const isKubernetesConnection = computed(() => {
    return props.connectionData?.connection?.kind === 'kubernetes'
})

const fieldChoices = computed(() => {
    let timeFieldChoices = []
    let dateFieldChoices = []
    let severityChoices = []

    const fields = props.fieldsSetupData?.fields || []

    for (const field of fields) {
        if (!field.name || !field.type) continue

        let item = { name: field.name, type: field.type }
        let itemType = item.type.toLowerCase()

        if (
            itemType.includes('datetime') ||
            itemType.includes('datetime64') ||
            itemType.includes('timestamp') ||
            itemType.includes('int64') ||
            itemType.includes('uint64')
        ) {
            timeFieldChoices.push(item)
        } else if (itemType.includes('date') || itemType.includes('date32')) {
            dateFieldChoices.push(item)
        } else {
            severityChoices.push(item)
        }
    }

    return {
        time_field: timeFieldChoices,
        date_field: dateFieldChoices,
        severity_field: severityChoices,
    }
})

const defaultChosenFieldsError = computed(() => {
    if (!defaultChosenFields.value || defaultChosenFields.value.trim() === '') {
        return ''
    }

    const chosenFieldNames = defaultChosenFields.value
        .split(',')
        .map((name) => name.trim())
        .filter((name) => name !== '')

    const existingFieldNames = (props.fieldsSetupData?.fields || []).map((f) => f.name)
    const invalidFields = []

    for (const chosenField of chosenFieldNames) {
        if (!existingFieldNames.includes(chosenField)) {
            invalidFields.push(chosenField)
        }
    }

    if (invalidFields.length > 0) {
        return `Field(s) not found: ${invalidFields.join(', ')}`
    }

    return ''
})

const isValid = computed(() => {
    // Time field is required
    if (!timeField.value || timeField.value.trim() === '') {
        return false
    }

    // Default chosen fields is required
    if (!defaultChosenFields.value || defaultChosenFields.value.trim() === '') {
        return false
    }

    // Validate default chosen fields - all comma-separated values must exist in fields
    const chosenFieldNames = defaultChosenFields.value
        .split(',')
        .map((name) => name.trim())
        .filter((name) => name !== '')

    const existingFieldNames = (props.fieldsSetupData?.fields || []).map((f) => f.name)

    // Check if all chosen fields exist
    for (const chosenField of chosenFieldNames) {
        if (!existingFieldNames.includes(chosenField)) {
            return false
        }
    }

    return true
})

const handleNext = () => {
    if (!isValid.value) {
        showValidation.value = true
        return
    }

    emit('update:modelValue', {
        time_field: timeField.value,
        date_field: dateField.value,
        severity_field: severityField.value,
        default_chosen_fields: defaultChosenFields.value,
        execute_query_on_open: executeQueryOnOpen.value,
    })
    emit('next')
}

watch([timeField, dateField, severityField, defaultChosenFields, executeQueryOnOpen], () => {
    emit('update:modelValue', {
        time_field: timeField.value,
        date_field: dateField.value,
        severity_field: severityField.value,
        default_chosen_fields: defaultChosenFields.value,
        execute_query_on_open: executeQueryOnOpen.value,
    })
})

// Clear date and severity fields for Docker/Kubernetes connections and set defaults
watch(
    [isDockerConnection, isKubernetesConnection, () => props.fieldsSetupData?.fields],
    ([isDocker, isKubernetes, fields]) => {
        if (isDocker || isKubernetes) {
            dateField.value = ''
            severityField.value = ''

            // Set default time field to "time" if it exists
            if (fields && fields.length > 0 && !timeField.value) {
                const hasTimeField = fields.some((f) => f.name === 'time')
                if (hasTimeField) {
                    timeField.value = 'time'
                }
            }

            // Set default chosen fields if not already set
            if (!defaultChosenFields.value && fields && fields.length > 0) {
                let defaultFields = []
                if (isDocker) {
                    defaultFields = ['stream', 'container_name', 'message']
                } else if (isKubernetes) {
                    defaultFields = ['pod_name', 'node_name', 'message']
                }
                const existingFields = fields.map((f) => f.name)
                const validDefaults = defaultFields.filter((field) => existingFields.includes(field))

                if (validDefaults.length > 0) {
                    defaultChosenFields.value = validDefaults.join(', ')
                }
            }
        }
    },
    { immediate: true },
)
</script>
