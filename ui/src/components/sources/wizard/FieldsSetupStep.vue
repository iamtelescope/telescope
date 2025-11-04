<template>
    <div class="flex flex-col">
        <div class="flex justify-between mb-4">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button label="Next" icon="pi pi-arrow-right" size="small" iconPos="right" @click="handleNext" />
        </div>
        <div class="flex flex-col gap-1">
            <div class="flex justify-between items-center mb-3 gap-2">
                <Button
                    v-if="fields.length > 0"
                    :label="allFieldsCollapsed ? 'Expand all' : 'Collapse all'"
                    :icon="allFieldsCollapsed ? 'pi pi-chevron-down' : 'pi pi-chevron-up'"
                    size="small"
                    text
                    @click="toggleAllFields"
                />
                <div v-else></div>
                <div class="flex gap-2">
                    <Button
                        label="Autoload fields"
                        icon="pi pi-download"
                        size="small"
                        severity="secondary"
                        @click="handleAutoloadFields"
                        :loading="loadingSchema"
                    />
                    <Button
                        v-if="!isDocker"
                        label="Add Field"
                        icon="pi pi-plus"
                        size="small"
                        outlined
                        @click="addField"
                    />
                </div>
            </div>

            <InlineError v-model="autoloadError" :dismissable="true" class="mb-3" />

            <div v-if="fields.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
                <p>No fields configured yet. Click "Add Field" to start.</p>
            </div>

            <ContentBlock
                v-for="(field, index) in fields"
                :key="index"
                :collapsible="true"
                :collapsed="fieldCollapsedStates[index]"
                headerClass="font-mono"
                class="mb-3"
            >
                <template #header_text>
                    <span>{{ field.name || 'New field' }}</span>
                    <span v-if="field.type" class="text-sm text-cyan-600 dark:text-cyan-400 ml-2">
                        {{ field.type }}
                    </span>
                </template>
                <template #actions>
                    <Button
                        icon="pi pi-trash"
                        severity="danger"
                        size="small"
                        class="max-h-[25px]"
                        text
                        @click="removeField(index)"
                    />
                </template>

                <div class="p-4">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <FloatLabel variant="on">
                                <InputText
                                    :id="'name-' + index"
                                    :ref="
                                        (el) => {
                                            if (el) nameInputs[index] = el
                                        }
                                    "
                                    v-model="field.name"
                                    class="w-full"
                                    fluid
                                    :invalid="!field.name && showValidation"
                                />
                                <label :for="'name-' + index">Name *</label>
                            </FloatLabel>
                            <Message
                                v-if="!field.name && showValidation"
                                severity="error"
                                size="small"
                                variant="simple"
                            >
                                Field name is required
                            </Message>
                        </div>
                        <div>
                            <FloatLabel variant="on">
                                <InputText
                                    :id="'displayName-' + index"
                                    v-model="field.display_name"
                                    class="w-full"
                                    fluid
                                />
                                <label :for="'displayName-' + index">Display Name</label>
                            </FloatLabel>
                        </div>
                        <div>
                            <FloatLabel variant="on">
                                <Select
                                    :inputId="'type-' + index"
                                    v-model="field.type"
                                    :options="fieldTypes"
                                    editable
                                    :filter="isClickHouse"
                                    class="w-full"
                                    :invalid="!field.type && showValidation"
                                />
                                <label :for="'type-' + index">Type *</label>
                            </FloatLabel>
                            <Message
                                v-if="!field.type && showValidation"
                                severity="error"
                                size="small"
                                variant="simple"
                            >
                                Field type is required
                            </Message>
                        </div>
                        <div>
                            <FloatLabel variant="on">
                                <InputText :id="'values-' + index" v-model="field.values" class="w-full" fluid />
                                <label :for="'values-' + index">Values</label>
                            </FloatLabel>
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-3 mt-3">
                        <div class="flex items-center gap-2">
                            <ToggleSwitch :inputId="'autocomplete-' + index" v-model="field.autocomplete" />
                            <label :for="'autocomplete-' + index" class="text-sm cursor-pointer">Autocomplete</label>
                        </div>
                        <div class="flex items-center gap-2">
                            <ToggleSwitch :inputId="'suggest-' + index" v-model="field.suggest" />
                            <label :for="'suggest-' + index" class="text-sm cursor-pointer">Suggest</label>
                        </div>
                        <div class="flex items-center gap-2">
                            <ToggleSwitch :inputId="'jsonstring-' + index" v-model="field.jsonstring" />
                            <label :for="'jsonstring-' + index" class="text-sm cursor-pointer"
                                >Treat as JSON String</label
                            >
                        </div>
                        <div class="flex items-center gap-2">
                            <ToggleSwitch :inputId="'group_by-' + index" v-model="field.group_by" />
                            <label :for="'group_by-' + index" class="text-sm cursor-pointer">Allow in GROUP BY</label>
                        </div>
                    </div>
                </div>
            </ContentBlock>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { Button, InputText, ToggleSwitch, Select, Message, FloatLabel } from 'primevue'
import { useToast } from 'primevue/usetoast'
import { FieldTypes } from '@/utils/constants'
import ContentBlock from '@/components/common/ContentBlock.vue'
import InlineError from '@/components/common/InlineError.vue'
import { SourceService } from '@/sdk/services/source'

const props = defineProps(['modelValue', 'connectionData'])
const emit = defineEmits(['prev', 'next', 'update:modelValue'])

const toast = useToast()
const sourceSrv = new SourceService()

const fields = ref(props.modelValue?.fields || [])
const showValidation = ref(false)
const loadingSchema = ref(false)
const autoloadError = ref('')
const nameInputs = ref({})
const fieldCollapsedStates = ref({})
const hasAutoLoaded = ref(false)

const isClickHouse = computed(() => {
    return props.connectionData?.connection?.kind === 'clickhouse'
})

const isDocker = computed(() => {
    return props.connectionData?.connection?.kind === 'docker'
})

const isValid = computed(() => {
    // If no fields are added, it's valid (fields are optional)
    if (fields.value.length === 0) {
        return true
    }
    // If fields are added, all must have a name and type
    return fields.value.every(
        (field) => field.name && field.name.trim() !== '' && field.type && field.type.trim() !== '',
    )
})

const fieldTypes = computed(() => {
    const connectionKind = props.connectionData?.connection?.kind
    if (connectionKind === 'clickhouse') {
        return FieldTypes.clickhouse || []
    } else if (connectionKind === 'docker') {
        return FieldTypes.docker || []
    }
    return []
})

const addField = async () => {
    fields.value.push({
        name: '',
        display_name: '',
        type: '',
        values: '',
        autocomplete: false,
        suggest: false,
        jsonstring: false,
        group_by: false,
    })

    await nextTick()
    const newIndex = fields.value.length - 1
    const inputElement = nameInputs.value[newIndex]
    if (inputElement) {
        inputElement.$el?.focus()
        inputElement.$el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
}

const removeField = (index) => {
    fields.value.splice(index, 1)
    showValidation.value = false
}

const allFieldsCollapsed = computed(() => {
    // Check if all fields are collapsed
    return fields.value.every((_, index) => fieldCollapsedStates.value[index] === true)
})

const toggleAllFields = () => {
    const newState = !allFieldsCollapsed.value
    // Set all fields to the new state
    fields.value.forEach((_, index) => {
        fieldCollapsedStates.value[index] = newState
    })
}

const handleNext = () => {
    if (!isValid.value) {
        showValidation.value = true

        // Expand fields that have validation errors
        fields.value.forEach((field, index) => {
            const hasError = !field.name || field.name.trim() === '' || !field.type || field.type.trim() === ''
            if (hasError) {
                fieldCollapsedStates.value[index] = false
            }
        })

        return
    }
    emit('update:modelValue', { fields: fields.value })
    emit('next')
}

const handleAutoloadFields = async () => {
    loadingSchema.value = true
    autoloadError.value = ''

    try {
        // Build request data based on connection kind
        const kind = props.connectionData.connection.kind
        const data = {
            connection_id: props.connectionData.connection.id,
        }

        // Add kind-specific params
        if (kind === 'clickhouse') {
            data.database = props.connectionData.database
            data.table = props.connectionData.table
        }

        // Call the service
        const response = await sourceSrv.getSourceSchema(kind, data)

        // Check for errors first
        if (!response.result || !response.validation.result) {
            // Show inline error instead of toast
            autoloadError.value = response.errors.join(', ') || 'Failed to load schema'
            return
        }

        // Success - process the schema fields
        const schemaFields = response.data || []
        let fieldsAdded = []

        for (const field of schemaFields) {
            // Check if field already exists
            const existingField = fields.value.find((f) => f.name === field.name)
            if (!existingField) {
                fields.value.push({
                    name: field.name,
                    display_name: field.display_name || '',
                    type: field.type,
                    values: field.values || '',
                    autocomplete: field.autocomplete || false,
                    suggest: field.suggest || false,
                    jsonstring: field.jsonstring || false,
                    group_by: field.group_by || false,
                })
                fieldsAdded.push(field.name)
            }
        }

        if (fieldsAdded.length > 0) {
            // Collapse all fields by default after autoload
            fields.value.forEach((_, index) => {
                fieldCollapsedStates.value[index] = true
            })

            toast.add({
                severity: 'success',
                summary: 'Success',
                detail: `Added ${fieldsAdded.length} field(s): ${fieldsAdded.join(', ')}`,
                life: 3000,
            })
        } else {
            toast.add({
                severity: 'warn',
                summary: 'Warning',
                detail: 'No new fields were added',
                life: 3000,
            })
        }
    } catch (error) {
        autoloadError.value = 'Failed to load schema fields'
    } finally {
        loadingSchema.value = false
    }
}

watch(
    fields,
    () => {
        emit('update:modelValue', { fields: fields.value })
    },
    { deep: true },
)

// Watch for connection data changes - only auto-load on first connection for new sources
watch(
    () => props.connectionData,
    (newVal, oldVal) => {
        // If we're getting connection data for the first time, auto-load
        // But only if we don't have initial fields (i.e., not editing)
        const hasInitialFields = props.modelValue?.fields && props.modelValue.fields.length > 0
        if (
            newVal?.connection &&
            !oldVal?.connection &&
            !hasAutoLoaded.value &&
            fields.value.length === 0 &&
            !hasInitialFields
        ) {
            hasAutoLoaded.value = true
            handleAutoloadFields()
        }
    },
    { deep: true, immediate: true },
)
</script>
