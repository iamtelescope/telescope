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
                <label for="connection" class="font-medium text-lg">Connection *</label>
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

            <!-- ClickHouse specific columns -->
            <template v-if="connection?.kind === 'clickhouse'">
                <div class="pt-2">
                    <label for="database" class="font-medium text-lg">Database *</label>
                    <InputText v-model="database" id="database" class="w-full font-mono" fluid />
                    <Message v-if="errors.database" severity="error" size="small" variant="simple" class="mt-2">
                        {{ errors.database }}
                    </Message>
                </div>
                <div class="pt-2">
                    <label for="table" class="font-medium text-lg">Table *</label>
                    <InputText v-model="table" id="table" class="w-full font-mono" fluid />
                    <Message v-if="errors.table" severity="error" size="small" variant="simple" class="mt-2">
                        {{ errors.table }}
                    </Message>
                </div>
                <div class="pt-2">
                    <label for="settings" class="font-medium text-lg">Query Settings</label>
                    <Textarea
                        v-model="settings"
                        id="settings"
                        class="w-full font-mono"
                        rows="3"
                        placeholder="e.g., use_query_cache = true, max_parallel_replicas = 1"
                    />
                    <Message size="small" severity="secondary" variant="simple">
                        ClickHouse SETTINGS clause (comma-separated key=value pairs)
                    </Message>
                </div>
            </template>

            <!-- StarRocks specific columns -->
            <template v-if="connection?.kind === 'starrocks'">
                <div class="pt-2">
                    <label for="catalog" class="font-medium">Catalog *</label>
                    <InputText v-model="catalog" id="catalog" class="w-full font-mono" fluid />
                    <Message v-if="errors.catalog" severity="error" size="small" variant="simple" class="mt-2">
                        {{ errors.catalog }}
                    </Message>
                </div>
                <div class="pt-2">
                    <label for="database" class="font-medium">Database *</label>
                    <InputText v-model="database" id="database" class="w-full font-mono" fluid />
                    <Message v-if="errors.database" severity="error" size="small" variant="simple" class="mt-2">
                        {{ errors.database }}
                    </Message>
                </div>
                <div class="pt-2">
                    <label for="table" class="font-medium">Table *</label>
                    <InputText v-model="table" id="table" class="w-full font-mono" fluid />
                    <Message v-if="errors.table" severity="error" size="small" variant="simple" class="mt-2">
                        {{ errors.table }}
                    </Message>
                </div>
                <div class="pt-2">
                    <label for="settings" class="font-medium">Query Settings</label>
                    <Textarea
                        v-model="settings"
                        id="settings"
                        class="w-full font-mono"
                        rows="3"
                        placeholder="e.g., use_query_cache = true, max_parallel_replicas = 1"
                    />
                    <small class="text-gray-500 dark:text-gray-400 block mt-1">
                        StarRocks SETTINGS clause (comma-separated key=value pairs)
                    </small>
                </div>
            </template>

            <!-- Kubernetes specific columns -->
            <template v-if="connection?.kind === 'kubernetes'">
                <div class="pt-2">
                    <label for="namespace_label_selector" class="font-medium text-lg">Namespace Label Selector</label>
                    <InputText
                        v-model="namespaceLabelSelector"
                        id="namespace_label_selector"
                        class="w-full font-mono text-sm"
                        placeholder="e.g., env=prod,team=backend"
                        fluid
                    />
                    <Message size="small" severity="secondary" variant="simple">
                        Kubernetes label selector (server-side filtering)
                    </Message>
                </div>
                <div class="pt-2">
                    <label for="namespace_column_selector" class="font-medium text-lg">Namespace Field Selector</label>
                    <InputText
                        v-model="namespaceFieldSelector"
                        id="namespace_column_selector"
                        class="w-full font-mono text-sm"
                        placeholder="e.g., metadata.name=default"
                        fluid
                    />
                    <Message size="small" severity="secondary" variant="simple">
                        Kubernetes field selector (server-side filtering)
                    </Message>
                </div>
                <div class="pt-2">
                    <label for="namespace" class="font-medium text-lg">Namespace FlyQL Filter</label>
                    <InputText
                        v-model="namespace"
                        id="namespace"
                        class="w-full font-mono text-sm"
                        placeholder='e.g., name contains "prod" or name == "default"'
                        fluid
                    />
                    <Message size="small" severity="secondary" variant="simple">
                        FlyQL query for client-side filtering. Available columns: name, status
                    </Message>
                </div>
            </template>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Button, InputText, Message, Select, Textarea } from 'primevue'

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

// Initialize form columns from props
const connection = ref(preselectedConnection.value || null)
const catalog = ref(props.modelValue?.catalog || 'default_catalog')
const database = ref(props.modelValue?.database || '')
const table = ref(props.modelValue?.table || '')
const settings = ref(props.modelValue?.settings || '')
const namespaceLabelSelector = ref(props.modelValue?.namespace_label_selector || '')
const namespaceFieldSelector = ref(props.modelValue?.namespace_column_selector || '')
const namespace = ref(props.modelValue?.namespace || '')
const errors = ref({})

// Cache for storing column values per connection ID
const connectionCache = ref({})

// Initialize cache with current values if editing
if (preselectedConnection.value) {
    connectionCache.value[preselectedConnection.value.id] = {
        catalog: props.modelValue?.catalog || 'default_catalog',
        database: props.modelValue?.database || '',
        table: props.modelValue?.table || '',
        settings: props.modelValue?.settings || '',
        namespace_label_selector: props.modelValue?.namespace_label_selector || '',
        namespace_column_selector: props.modelValue?.namespace_column_selector || '',
        namespace: props.modelValue?.namespace || '',
    }
}

const hasNoConnections = computed(() => {
    return !filteredConnections.value || filteredConnections.value.length === 0
})

const handleConnectionChange = () => {
    if (!connection.value) return

    // Check if we have cached values for the new connection
    const cached = connectionCache.value[connection.value.id]

    if (cached) {
        // Restore cached values
        catalog.value = cached.catalog || 'default_catalog'
        database.value = cached.database || ''
        table.value = cached.table || ''
        settings.value = cached.settings || ''
        namespaceLabelSelector.value = cached.namespace_label_selector || ''
        namespaceFieldSelector.value = cached.namespace_column_selector || ''
        namespace.value = cached.namespace || ''
    } else {
        // Clear columns for new connection
        catalog.value = 'default_catalog'
        database.value = ''
        table.value = ''
        settings.value = ''
        namespaceLabelSelector.value = ''
        namespaceFieldSelector.value = ''
        namespace.value = ''
    }

    // Clear errors
    errors.value = {}
}

// Watch column changes to update cache
watch([database, table, settings, namespaceLabelSelector, namespaceFieldSelector, namespace], () => {
    if (connection.value) {
        connectionCache.value[connection.value.id] = {
            catalog: catalog.value,
            database: database.value,
            table: table.value,
            settings: settings.value,
            namespace_label_selector: namespaceLabelSelector.value,
            namespace_column_selector: namespaceFieldSelector.value,
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

    // StarRocks specific validation
    if (connection.value?.kind === 'starrocks') {
        if (!catalog.value) {
            errors.value.catalog = 'Catalog is required for StarRocks connections'
        }
        if (!database.value) {
            errors.value.database = 'Database is required for StarRocks connections'
        }
        if (!table.value) {
            errors.value.table = 'Table is required for StarRocks connections'
        }
    }

    // Kubernetes specific validation - all columns are optional now
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
            catalog: catalog.value,
            database: database.value,
            table: table.value,
            settings: settings.value,
            namespace_label_selector: namespaceLabelSelector.value,
            namespace_column_selector: namespaceFieldSelector.value,
            namespace: namespace.value,
        }
        emit('update:modelValue', values)
        emit('next')
    }
}
</script>
