<template>
    <div class="flex flex-col">
        <div class="flex mb-4" :class="showBack ? 'justify-between' : 'justify-end'">
            <Button
                v-if="showBack"
                label="Back"
                severity="secondary"
                size="small"
                icon="pi pi-arrow-left"
                @click="emit('prev')"
            />
            <Button label="Next" icon="pi pi-arrow-right" size="small" iconPos="right" @click="handleNext" />
        </div>
        <div class="flex flex-col gap-1">
            <div>
                <label for="connection" class="font-medium">Connection *</label>
                <Select
                    v-model="connection"
                    inputId="connection"
                    :options="filteredConnections"
                    optionLabel="name"
                    dataKey="id"
                    :disabled="hasNoConnections"
                    placeholder="Select a connection..."
                    filter
                    filterPlaceholder="Search..."
                    class="w-full"
                    @change="handleConnectionChange"
                >
                    <template #value="{ value, placeholder }">
                        <div v-if="value && value.kind" class="flex items-center">
                            <img
                                :src="require(`@/assets/${value.kind}.png`)"
                                height="20px"
                                width="20px"
                                class="mr-2"
                                :title="value.kind"
                            />
                            <span>{{ value.name }}</span>
                        </div>
                        <span v-else>{{ placeholder }}</span>
                    </template>
                    <template #option="{ option }">
                        <div class="flex items-center">
                            <img
                                :src="require(`@/assets/${option.kind}.png`)"
                                height="20px"
                                width="20px"
                                class="mr-2"
                                :title="option.kind"
                            />
                            <span>{{ option.name }}</span>
                        </div>
                    </template>
                </Select>
                <Message v-if="hasNoConnections" severity="warn" size="small" class="mt-2">
                    <div class="font-semibold mb-2">No connections available</div>
                    <div class="mb-1">You may need to:</div>
                    <ul class="list-disc ml-4 space-y-1">
                        <li>
                            <router-link to="/connections/new" class="text-blue-600 dark:text-blue-400 hover:underline">
                                Create a new connection
                            </router-link>
                        </li>
                        <li>
                            Request access to an
                            <router-link to="/connections" class="text-blue-600 dark:text-blue-400 hover:underline">
                                existing connection
                            </router-link>
                        </li>
                    </ul>
                </Message>
                <Message v-if="errors.connection" severity="error" size="small" variant="simple" class="mt-2">
                    {{ errors.connection }}
                </Message>
            </div>

            <!-- ClickHouse specific fields -->
            <template v-if="connection?.kind === 'clickhouse'">
                <div class="pt-2">
                    <label for="database" class="font-medium">Database *</label>
                    <InputText v-model="database" id="database" class="w-full" fluid />
                    <Message v-if="errors.database" severity="error" size="small" variant="simple" class="mt-2">
                        {{ errors.database }}
                    </Message>
                </div>
                <div class="pt-2">
                    <label for="table" class="font-medium">Table *</label>
                    <InputText v-model="table" id="table" class="w-full" fluid />
                    <Message v-if="errors.table" severity="error" size="small" variant="simple" class="mt-2">
                        {{ errors.table }}
                    </Message>
                </div>
            </template>

            <!-- Kubernetes specific fields -->
            <template v-if="connection?.kind === 'kubernetes'">
                <div class="pt-2">
                    <label for="namespace" class="font-medium">Namespace *</label>
                    <InputText v-model="namespace" id="namespace" class="w-full" fluid />
                    <Message v-if="errors.namespace" severity="error" size="small" variant="simple" class="mt-2">
                        {{ errors.namespace }}
                    </Message>
                </div>
            </template>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Button, InputText, Message, Select } from 'primevue'

const props = defineProps({
    modelValue: Object,
    connections: Array,
    showBack: {
        type: Boolean,
        default: true,
    },
})
const emit = defineEmits(['prev', 'next', 'update:modelValue'])

// Find the preselected connection by ID from the loaded connections
const preselectedConnection = computed(() => {
    if (!props.modelValue?.connection?.id || !props.connections) {
        return null
    }
    return props.connections.find((c) => c.id === props.modelValue.connection.id) || null
})

// Check if we're editing (have a preselected connection)
const isEditing = computed(() => !!preselectedConnection.value)

// Filter connections by kind when editing - only show connections of the same kind
const filteredConnections = computed(() => {
    if (!props.connections) return []

    // If editing, only show connections of the same kind as the current one
    if (isEditing.value && preselectedConnection.value) {
        return props.connections.filter((c) => c.kind === preselectedConnection.value.kind)
    }

    // If creating new, show all connections
    return props.connections
})

// Initialize form fields from props
const connection = ref(preselectedConnection.value || null)
const database = ref(props.modelValue?.database || '')
const table = ref(props.modelValue?.table || '')
const namespace = ref(props.modelValue?.namespace || '')
const errors = ref({})

// Cache for storing field values per connection ID
const connectionCache = ref({})

// Initialize cache with current values if editing
if (preselectedConnection.value) {
    connectionCache.value[preselectedConnection.value.id] = {
        database: props.modelValue?.database || '',
        table: props.modelValue?.table || '',
        namespace: props.modelValue?.namespace || '',
    }
}

const hasNoConnections = computed(() => {
    return !filteredConnections.value || filteredConnections.value.length === 0
})

const handleConnectionChange = () => {
    if (!connection.value) return

    // Save current values to cache for the previous connection
    const previousConnectionId = Object.keys(connectionCache.value).find(
        (id) => connectionCache.value[id] && (database.value !== '' || table.value !== '' || namespace.value !== ''),
    )

    // Check if we have cached values for the new connection
    const cached = connectionCache.value[connection.value.id]

    if (cached) {
        // Restore cached values
        database.value = cached.database || ''
        table.value = cached.table || ''
        namespace.value = cached.namespace || ''
    } else {
        // Clear fields for new connection
        database.value = ''
        table.value = ''
        namespace.value = ''
    }

    // Clear errors
    errors.value = {}
}

// Watch field changes to update cache
watch([database, table], () => {
    if (connection.value) {
        connectionCache.value[connection.value.id] = {
            database: database.value,
            table: table.value,
            namespace: namespace.value,
        }
    }
})

const validate = () => {
    errors.value = {}

    if (!connection.value) {
        errors.value.connection = 'Connection is required'
        return false
    }

    // When editing, ensure connection kind hasn't changed
    if (isEditing.value && preselectedConnection.value) {
        if (connection.value.kind !== preselectedConnection.value.kind) {
            errors.value.connection = 'Cannot change connection to a different type when editing a source'
            return false
        }
    }

    // ClickHouse specific validation
    if (connection.value?.kind === 'clickhouse') {
        if (!database.value) {
            errors.value.database = 'Database is required for ClickHouse connections'
        }
        if (!table.value) {
            errors.value.table = 'Table is required for ClickHouse connections'
        }
    }

    // Kubernetes specific validation
    if (connection.value?.kind === 'kubernetes') {
        if (!namespace.value) {
            errors.value.namespace = 'Namespace is required for Kubernetes sources'
        }
    }

    return Object.keys(errors.value).length === 0
}

const handleNext = () => {
    if (validate()) {
        const values = {
            connection: connection.value,
            database: database.value,
            table: table.value,
            namespace: namespace.value,
        }
        emit('update:modelValue', values)
        emit('next')
    }
}
</script>
