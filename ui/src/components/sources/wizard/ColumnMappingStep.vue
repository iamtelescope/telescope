<template>
    <div class="flex flex-col">
        <div class="flex justify-between mb-4">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button label="Next" icon="pi pi-arrow-right" size="small" iconPos="right" @click="handleNext" />
        </div>
        <div class="flex flex-col gap-1">
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label for="timeField" class="font-medium block mb-2">Time column *</label>
                    <Select
                        id="timeField"
                        v-model="timeField"
                        :options="columnChoices.time_column"
                        optionLabel="name"
                        optionValue="name"
                        editable
                        showClear
                        class="w-full"
                        :invalid="!timeField && showValidation"
                    />
                    <Message v-if="!timeField && showValidation" severity="error" size="small" variant="simple">
                        Time column is required
                    </Message>
                </div>
                <div>
                    <label for="dateField" class="font-medium block mb-2">Date column</label>
                    <Select
                        id="dateField"
                        v-model="dateField"
                        :options="columnChoices.date_column"
                        optionLabel="name"
                        optionValue="name"
                        editable
                        showClear
                        class="w-full"
                        :disabled="isDockerConnection || isKubernetesConnection"
                    />
                </div>
                <div>
                    <label for="severityField" class="font-medium block mb-2">Severity column</label>
                    <Select
                        id="severityField"
                        v-model="severityField"
                        :options="columnChoices.severity_column"
                        optionLabel="name"
                        optionValue="name"
                        showClear
                        class="w-full"
                        :disabled="isDockerConnection || isKubernetesConnection"
                    />
                </div>
                <div>
                    <label for="defaultChosenFields" class="font-medium block mb-2">Default chosen columns *</label>
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
                        Default chosen columns is required
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

const props = defineProps(['modelValue', 'columnsSetupData', 'connectionData'])
const emit = defineEmits(['prev', 'next', 'update:modelValue'])

const showValidation = ref(false)
const timeField = ref(props.modelValue?.time_column || '')
const dateField = ref(props.modelValue?.date_column || '')
const severityField = ref(props.modelValue?.severity_column || '')
const executeQueryOnOpen = ref(props.modelValue?.execute_query_on_open ?? true)

// Convert array to comma-separated string if needed
const getInitialDefaultChosenFields = () => {
    const value = props.modelValue?.default_chosen_columns
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

const columnChoices = computed(() => {
    let timeFieldChoices = []
    let dateFieldChoices = []
    let severityChoices = []

    const columns = props.columnsSetupData?.columns || []

    for (const column of columns) {
        if (!column.name || !column.type) continue

        let item = { name: column.name, type: column.type }
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
        time_column: timeFieldChoices,
        date_column: dateFieldChoices,
        severity_column: severityChoices,
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

    const existingFieldNames = (props.columnsSetupData?.columns || []).map((f) => f.name)
    const invalidColumns = []

    for (const chosenField of chosenFieldNames) {
        if (!existingFieldNames.includes(chosenField)) {
            invalidColumns.push(chosenField)
        }
    }

    if (invalidColumns.length > 0) {
        return `Column(s) not found: ${invalidColumns.join(', ')}`
    }

    return ''
})

const isValid = computed(() => {
    // Time column is required
    if (!timeField.value || timeField.value.trim() === '') {
        return false
    }

    // Default chosen columns is required
    if (!defaultChosenFields.value || defaultChosenFields.value.trim() === '') {
        return false
    }

    // Validate default chosen columns - all comma-separated values must exist in columns
    const chosenFieldNames = defaultChosenFields.value
        .split(',')
        .map((name) => name.trim())
        .filter((name) => name !== '')

    const existingFieldNames = (props.columnsSetupData?.columns || []).map((f) => f.name)

    // Check if all chosen columns exist
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
        time_column: timeField.value,
        date_column: dateField.value,
        severity_column: severityField.value,
        default_chosen_columns: defaultChosenFields.value,
        execute_query_on_open: executeQueryOnOpen.value,
    })
    emit('next')
}

watch([timeField, dateField, severityField, defaultChosenFields, executeQueryOnOpen], () => {
    emit('update:modelValue', {
        time_column: timeField.value,
        date_column: dateField.value,
        severity_column: severityField.value,
        default_chosen_columns: defaultChosenFields.value,
        execute_query_on_open: executeQueryOnOpen.value,
    })
})

// Clear date and severity columns for Docker/Kubernetes connections and set defaults
watch(
    [isDockerConnection, isKubernetesConnection, () => props.columnsSetupData?.columns],
    ([isDocker, isKubernetes, columns]) => {
        if (isDocker || isKubernetes) {
            dateField.value = ''
            severityField.value = ''

            // Set default time column to "time" if it exists
            if (columns && columns.length > 0 && !timeField.value) {
                const hasTimeColumn = columns.some((f) => f.name === 'time')
                if (hasTimeColumn) {
                    timeField.value = 'time'
                }
            }

            // Set default chosen columns if not already set
            if (!defaultChosenFields.value && columns && columns.length > 0) {
                let defaultColumns = []
                if (isDocker) {
                    defaultColumns = ['stream', 'container_name', 'body']
                } else if (isKubernetes) {
                    defaultColumns = ['pod_name', 'node_name', 'body']
                }
                const existingColumns = columns.map((f) => f.name)
                const validDefaults = defaultColumns.filter((column) => existingColumns.includes(column))

                if (validDefaults.length > 0) {
                    defaultChosenFields.value = validDefaults.join(', ')
                }
            }
        }
    },
    { immediate: true },
)
</script>
