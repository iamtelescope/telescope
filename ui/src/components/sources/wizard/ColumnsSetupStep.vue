<template>
    <div class="flex flex-col">
        <div class="flex justify-between mb-4">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button label="Next" icon="pi pi-arrow-right" size="small" iconPos="right" @click="handleNext" />
        </div>
        <div class="flex flex-col gap-1">
            <div class="flex justify-between items-center mb-3 gap-2">
                <Button
                    v-if="columns.length > 0"
                    :label="allColumnsCollapsed ? 'Expand all' : 'Collapse all'"
                    :icon="allColumnsCollapsed ? 'pi pi-chevron-down' : 'pi pi-chevron-up'"
                    size="small"
                    text
                    @click="toggleAllColumns"
                />
                <div v-else></div>
                <div class="flex gap-2">
                    <Button
                        label="Autoload columns"
                        icon="pi pi-download"
                        size="small"
                        severity="secondary"
                        @click="handleAutoloadColumns"
                        :loading="loadingSchema"
                    />
                    <Button
                        v-if="!isDocker && !isKubernetes"
                        label="Add Column"
                        icon="pi pi-plus"
                        size="small"
                        outlined
                        @click="addColumn"
                    />
                </div>
            </div>

            <InlineError v-model="autoloadError" :dismissable="true" class="mb-3" />

            <div v-if="columns.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-300">
                <p>No columns configured yet. Click "Add Column" to start.</p>
            </div>

            <ContentBlock
                v-for="(column, index) in columns"
                :key="index"
                :collapsible="true"
                :collapsed="columnCollapsedStates[index]"
                headerClass="font-mono"
                class="mb-3"
            >
                <template #header_text>
                    <span>{{ column.name || 'New column' }}</span>
                    <span v-if="column.type" class="text-sm text-cyan-600 dark:text-cyan-400 ml-2">
                        {{ column.type }}
                    </span>
                </template>
                <template #actions>
                    <Button
                        v-if="!isDocker && !isKubernetes"
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
                                    v-model="column.name"
                                    class="w-full"
                                    fluid
                                    :invalid="!column.name && showValidation"
                                    :disabled="isDocker || isKubernetes"
                                />
                                <label :for="'name-' + index">Name *</label>
                            </FloatLabel>
                            <Message
                                v-if="!column.name && showValidation"
                                severity="error"
                                size="small"
                                variant="simple"
                            >
                                Column name is required
                            </Message>
                        </div>
                        <div>
                            <FloatLabel variant="on">
                                <InputText
                                    :id="'displayName-' + index"
                                    v-model="column.display_name"
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
                                    v-model="column.type"
                                    :options="columnTypes"
                                    editable
                                    :filter="isClickHouse"
                                    class="w-full"
                                    :invalid="!column.type && showValidation"
                                />
                                <label :for="'type-' + index">Type *</label>
                            </FloatLabel>
                            <FloatLabel variant="on">
                                <Select
                                    :inputId="'type-' + index"
                                    v-model="column.type"
                                    :options="columnTypes"
                                    editable
                                    :filter="isStarRocks"
                                    class="w-full"
                                    :invalid="!column.type && showValidation"
                                />
                                <label :for="'type-' + index">Type *</label>
                            </FloatLabel>
                            <Message
                                v-if="!column.type && showValidation"
                                severity="error"
                                size="small"
                                variant="simple"
                            >
                                Column type is required
                            </Message>
                        </div>
                        <div>
                            <FloatLabel variant="on">
                                <InputText :id="'values-' + index" v-model="column.values" class="w-full" fluid />
                                <label :for="'values-' + index">Values</label>
                            </FloatLabel>
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-3 mt-3">
                        <div class="flex items-center gap-2">
                            <ToggleSwitch :inputId="'autocomplete-' + index" v-model="column.autocomplete" />
                            <label :for="'autocomplete-' + index" class="text-sm cursor-pointer">Autocomplete</label>
                        </div>
                        <div class="flex items-center gap-2">
                            <ToggleSwitch :inputId="'suggest-' + index" v-model="column.suggest" />
                            <label :for="'suggest-' + index" class="text-sm cursor-pointer">Suggest</label>
                        </div>
                        <div class="flex items-center gap-2">
                            <ToggleSwitch :inputId="'jsonstring-' + index" v-model="column.jsonstring" />
                            <label :for="'jsonstring-' + index" class="text-sm cursor-pointer"
                                >Treat as JSON String</label
                            >
                        </div>
                        <div class="flex items-center gap-2">
                            <ToggleSwitch :inputId="'group_by-' + index" v-model="column.group_by" />
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

const columns = ref(props.modelValue?.columns || [])
const showValidation = ref(false)
const loadingSchema = ref(false)
const autoloadError = ref('')
const nameInputs = ref({})
const columnCollapsedStates = ref({})
const hasAutoLoaded = ref(false)

const isClickHouse = computed(() => {
    return props.connectionData?.connection?.kind === 'clickhouse'
})

const isStarRocks = computed(() => {
    return props.connectionData?.connection?.kind === 'starrocks'
})

const isDocker = computed(() => {
    return props.connectionData?.connection?.kind === 'docker'
})

const isKubernetes = computed(() => {
    return props.connectionData?.connection?.kind === 'kubernetes'
})

const isValid = computed(() => {
    // If no columns are added, it's valid (columns are optional)
    if (columns.value.length === 0) {
        return true
    }
    // If columns are added, all must have a name and type
    return columns.value.every(
        (column) => column.name && column.name.trim() !== '' && column.type && column.type.trim() !== '',
    )
})

const columnTypes = computed(() => {
    const connectionKind = props.connectionData?.connection?.kind
    if (connectionKind === 'clickhouse') {
        return FieldTypes.clickhouse || []
    } else if (connectionKind === 'starrocks') {
        return FieldTypes.starrocks || []
    } else if (connectionKind === 'docker') {
        return FieldTypes.docker || []
    } else if (connectionKind === 'kubernetes') {
        return FieldTypes.kubernetes || []
    }
    return []
})

const addColumn = async () => {
    columns.value.push({
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
    const newIndex = columns.value.length - 1
    const inputElement = nameInputs.value[newIndex]
    if (inputElement) {
        inputElement.$el?.focus()
        inputElement.$el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
}

const removeField = (index) => {
    columns.value.splice(index, 1)
    showValidation.value = false
}

const allColumnsCollapsed = computed(() => {
    // Check if all columns are collapsed
    return columns.value.every((_, index) => columnCollapsedStates.value[index] === true)
})

const toggleAllColumns = () => {
    const newState = !allColumnsCollapsed.value
    // Set all columns to the new state
    columns.value.forEach((_, index) => {
        columnCollapsedStates.value[index] = newState
    })
}

const handleNext = () => {
    if (!isValid.value) {
        showValidation.value = true

        // Expand columns that have validation errors
        columns.value.forEach((column, index) => {
            const hasError = !column.name || column.name.trim() === '' || !column.type || column.type.trim() === ''
            if (hasError) {
                columnCollapsedStates.value[index] = false
            }
        })

        return
    }
    emit('update:modelValue', { columns: columns.value })
    emit('next')
}

const handleAutoloadColumns = async () => {
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
        if (kind === 'starrocks') {
            data.catalog = props.connectionData.catalog
            data.database = props.connectionData.database
            data.table = props.connectionData.table
        }
        if (kind === 'kubernetes') {
            data.namespace = props.connectionData.namespace
        }

        // Call the service
        const response = await sourceSrv.getSourceSchema(kind, data)

        // Check for errors first
        if (!response.result || !response.validation.result) {
            // Show inline error instead of toast
            autoloadError.value = response.errors.join(', ') || 'Failed to load schema'
            return
        }

        // Success - process the schema columns
        const schemaColumns = response.data || []
        let columnsAdded = []

        for (const column of schemaColumns) {
            // Check if column already exists
            const existingColumn = columns.value.find((c) => c.name === column.name)
            if (!existingColumn) {
                columns.value.push({
                    name: column.name,
                    display_name: column.display_name || '',
                    type: column.type,
                    values: column.values || '',
                    autocomplete: column.autocomplete || false,
                    suggest: column.suggest || false,
                    jsonstring: column.jsonstring || false,
                    group_by: column.group_by || false,
                })
                columnsAdded.push(column.name)
            }
        }

        if (columnsAdded.length > 0) {
            // Collapse all columns by default after autoload
            columns.value.forEach((_, index) => {
                columnCollapsedStates.value[index] = true
            })

            toast.add({
                severity: 'success',
                summary: 'Success',
                detail: `Added ${columnsAdded.length} column(s): ${columnsAdded.join(', ')}`,
                life: 3000,
            })
        } else {
            toast.add({
                severity: 'warn',
                summary: 'Warning',
                detail: 'No new columns were added',
                life: 3000,
            })
        }
    } catch (error) {
        autoloadError.value = 'Failed to load schema columns'
    } finally {
        loadingSchema.value = false
    }
}

watch(
    columns,
    () => {
        emit('update:modelValue', { columns: columns.value })
    },
    { deep: true },
)

// Watch for connection data changes - only auto-load on first connection for new sources
watch(
    () => props.connectionData,
    (newVal, oldVal) => {
        // If we're getting connection data for the first time, auto-load
        // But only if we don't have initial columns (i.e., not editing)
        const hasInitialColumns = props.modelValue?.columns && props.modelValue.columns.length > 0
        if (
            newVal?.connection &&
            !oldVal?.connection &&
            !hasAutoLoaded.value &&
            columns.value.length === 0 &&
            !hasInitialColumns
        ) {
            hasAutoLoaded.value = true
            handleAutoloadColumns()
        }
    },
    { deep: true, immediate: true },
)
</script>
