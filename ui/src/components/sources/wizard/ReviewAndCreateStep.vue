<template>
    <div class="flex flex-col">
        <div class="flex justify-between mb-4">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button
                :label="isEditing ? 'Save' : 'Create'"
                icon="pi pi-check"
                size="small"
                @click="handleCreate"
                :loading="createLoading"
            />
        </div>
        <div v-if="basicInfo?.name && connectionData?.connection" class="flex flex-col gap-4">
            <ContentBlock header="Basic Information">
                <DataRow name="Name" :value="basicInfo.name" :copy="false" />
                <DataRow name="Slug" :value="basicInfo.slug" :copy="false" />
                <DataRow name="Description" :copy="false" :showBorder="false">
                    <EmptyValue :value="basicInfo.description || ''" />
                </DataRow>
            </ContentBlock>

            <ContentBlock header="Connection">
                <DataRow name="Connection" :copy="false">
                    <div class="flex items-center">
                        <img
                            :src="require(`@/assets/${connectionData.connection.kind}.png`)"
                            height="20px"
                            width="20px"
                            class="mr-2"
                            :title="connectionData.connection.kind"
                        />
                        {{ connectionData.connection.name }} ({{
                            getConnectionKindLabel(connectionData.connection.kind)
                        }})
                    </div>
                </DataRow>
                <DataRow v-if="connectionData.database" name="Database" :copy="false">
                    <span class="font-mono">{{ connectionData.database }}</span>
                </DataRow>
                <DataRow v-if="connectionData.table" name="Table" :copy="false">
                    <span class="font-mono">{{ connectionData.table }}</span>
                </DataRow>
                <DataRow v-if="connectionData.settings" name="Query Settings" :copy="false" :showBorder="false">
                    <span class="font-mono text-sm">
                        <EmptyValue :value="connectionData.settings || ''" />
                    </span>
                </DataRow>
            </ContentBlock>

            <ContentBlock v-if="connectionData.connection?.kind === 'kubernetes'" header="Kubernetes Configuration">
                <DataRow name="Namespace Label Selector" :copy="false">
                    <span class="font-mono text-sm">
                        <EmptyValue :value="connectionData.namespace_label_selector || ''" />
                    </span>
                </DataRow>
                <DataRow name="Namespace Field Selector" :copy="false">
                    <span class="font-mono text-sm">
                        <EmptyValue :value="connectionData.namespace_column_selector || ''" />
                    </span>
                </DataRow>
                <DataRow name="Namespace FlyQL Filter" :copy="false" :showBorder="false">
                    <span class="font-mono text-sm">
                        <EmptyValue :value="connectionData.namespace || ''" />
                    </span>
                </DataRow>
            </ContentBlock>

            <ContentBlock header="Settings">
                <DataRow name="Time Column" :value="columnMappingData.time_column" :copy="false" />
                <DataRow name="Date Column" :copy="false">
                    <EmptyValue :value="columnMappingData.date_column || ''" />
                </DataRow>
                <DataRow name="Severity Column" :copy="false">
                    <EmptyValue :value="columnMappingData.severity_column || ''" />
                </DataRow>
                <DataRow name="Default Chosen Columns" :copy="false">
                    <span class="text-sm">{{ formatChosenColumns(columnMappingData.default_chosen_columns) }}</span>
                </DataRow>
                <DataRow name="Execute Query On Open" :copy="false" :showBorder="false">
                    {{ (columnMappingData.execute_query_on_open ?? true) ? 'Yes' : 'No' }}
                </DataRow>
            </ContentBlock>

            <ContentBlock :header="`Columns (${columnsCount})`">
                <div
                    v-for="(column, index) in columnsSetupData.columns"
                    :key="index"
                    class="py-3 px-4 border-b dark:border-neutral-600 last:border-b-0"
                >
                    <div class="flex items-center justify-between gap-4">
                        <div class="flex items-center gap-3 min-w-0 flex-shrink">
                            <span class="font-mono font-medium text-sm">{{ column.name }}</span>
                            <span class="text-xs text-cyan-600 dark:text-cyan-400">{{ column.type }}</span>
                        </div>
                        <div class="flex items-center gap-4 flex-shrink-0">
                            <div class="flex items-center gap-1.5">
                                <ToggleSwitch :modelValue="column.autocomplete" readonly class="scale-75" />
                                <span class="text-gray-600 dark:text-gray-300">Autocomplete</span>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <ToggleSwitch :modelValue="column.suggest" readonly class="scale-75" />
                                <span class="text-gray-600 dark:text-gray-300">Suggest</span>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <ToggleSwitch :modelValue="column.jsonstring" readonly class="scale-75" />
                                <span class="text-gray-600 dark:text-gray-300">JSON</span>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <ToggleSwitch :modelValue="column.group_by" readonly class="scale-75" />
                                <span class="text-gray-600 dark:text-gray-300">GROUP BY</span>
                            </div>
                        </div>
                    </div>
                </div>
            </ContentBlock>
        </div>
        <div v-else class="text-center py-8 text-gray-500 dark:text-gray-300">
            <p>Please complete the previous steps first.</p>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Button, ToggleSwitch } from 'primevue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import DataRow from '@/components/common/DataRow.vue'
import EmptyValue from '@/components/common/EmptyValue.vue'

const props = defineProps([
    'modelValue',
    'basicInfo',
    'connectionData',
    'columnsSetupData',
    'columnMappingData',
    'source',
])
const emit = defineEmits(['prev', 'create'])

const createLoading = ref(false)

const isEditing = computed(() => !!props.source)

const connectionKindOptions = [
    { label: 'ClickHouse', value: 'clickhouse' },
    { label: 'StarRocks', value: 'starrocks' },
    { label: 'Docker', value: 'docker' },
    { label: 'Kubernetes', value: 'kubernetes' },
]

const getConnectionKindLabel = (value) => {
    const option = connectionKindOptions.find((opt) => opt.value === value)
    return option ? option.label : value
}

const columnsCount = computed(() => {
    return props.columnsSetupData?.columns?.length || 0
})

const formatChosenColumns = (columns) => {
    if (!columns) return '-'
    if (Array.isArray(columns)) return columns.join(', ')
    return columns
}

const handleCreate = () => {
    createLoading.value = true
    emit('create', () => {
        createLoading.value = false
    })
}
</script>
