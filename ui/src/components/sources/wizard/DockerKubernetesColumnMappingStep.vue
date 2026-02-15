<template>
    <div class="flex flex-col">
        <div class="flex justify-between mb-4">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button label="Next" icon="pi pi-arrow-right" size="small" iconPos="right" @click="handleNext" />
        </div>
        <div class="flex flex-col gap-4">
            <div class="grid grid-cols-2 gap-3">
                <!-- Time column - read-only for docker/kubernetes -->
                <div>
                    <label for="timeField" class="font-medium block mb-2">Time column</label>
                    <InputText id="timeField" v-model="timeField" class="w-full" disabled />
                </div>

                <!-- Default chosen columns -->
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

            <!-- Severity Rules Editor -->
            <div class="border dark:border-neutral-600 rounded p-4">
                <SeverityRulesEditor v-model="severityRules" />
            </div>

            <!-- Execute query on open toggle -->
            <div class="pt-3 flex items-center gap-2">
                <ToggleSwitch v-model="executeQueryOnOpen" inputId="executeQueryOnOpen" />
                <label for="executeQueryOnOpen" class="font-medium">Execute query on open</label>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Button, InputText, Message, ToggleSwitch } from 'primevue'
import SeverityRulesEditor from './SeverityRulesEditor.vue'

const props = defineProps(['modelValue', 'columnsSetupData', 'connectionData'])
const emit = defineEmits(['prev', 'next', 'update:modelValue'])

const showValidation = ref(false)

// Time field is always "time" for docker/kubernetes
const timeField = ref('time')

// Severity rules
const severityRules = ref(props.modelValue?.severity_rules || { extract: [], remap: {} })

const executeQueryOnOpen = ref(
    props.modelValue?.execute_query_on_open !== undefined
        ? props.modelValue.execute_query_on_open
        : props.connectionData?.connection?.kind === 'kubernetes'
          ? false
          : true,
)

const defaultChosenFields = ref(
    props.modelValue?.default_chosen_columns
        ? Array.isArray(props.modelValue.default_chosen_columns)
            ? props.modelValue.default_chosen_columns.join(', ')
            : props.modelValue.default_chosen_columns
        : props.connectionData?.connection?.kind === 'docker'
          ? 'stream, container_name, body'
          : 'pod, container, body',
)

const sourceTypeName = computed(() => {
    const kind = props.connectionData?.connection?.kind
    return kind === 'docker' ? 'Docker' : 'Kubernetes'
})

const isDockerConnection = computed(() => {
    return props.connectionData?.connection?.kind === 'docker'
})

const isKubernetesConnection = computed(() => {
    return props.connectionData?.connection?.kind === 'kubernetes'
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

    // Emit the complete model value
    const modelValue = {
        time_column: 'time', // Fixed for docker/kubernetes
        date_column: '', // Not used for docker/kubernetes
        severity_column: '', // Not used when severity_rules is present
        severity_rules:
            severityRules.value.extract.length > 0 || severityRules.value.remap.length > 0 ? severityRules.value : null,
        default_chosen_columns: defaultChosenFields.value,
        execute_query_on_open: executeQueryOnOpen.value,
    }

    emit('update:modelValue', modelValue)
    emit('next')
}

// Watch for changes and emit updates
watch([severityRules, defaultChosenFields, executeQueryOnOpen], () => {
    const modelValue = {
        time_column: 'time',
        date_column: '',
        severity_column: '',
        severity_rules:
            severityRules.value.extract.length > 0 || severityRules.value.remap.length > 0 ? severityRules.value : null,
        default_chosen_columns: defaultChosenFields.value,
        execute_query_on_open: executeQueryOnOpen.value,
    }
    emit('update:modelValue', modelValue)
})
</script>
