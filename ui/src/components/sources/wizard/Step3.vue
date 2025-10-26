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
                <DataRow
                    v-if="connectionData.database"
                    name="Database"
                    :value="connectionData.database"
                    :copy="false"
                />
                <DataRow
                    v-if="connectionData.table"
                    name="Table"
                    :value="connectionData.table"
                    :copy="false"
                    :showBorder="!connectionData.table"
                />
            </ContentBlock>

            <ContentBlock header="Field Mapping">
                <DataRow name="Time Field" :value="fieldMappingData.time_field" :copy="false" />
                <DataRow name="Date Field" :copy="false">
                    <EmptyValue :value="fieldMappingData.date_field || ''" />
                </DataRow>
                <DataRow name="Severity Field" :copy="false">
                    <EmptyValue :value="fieldMappingData.severity_field || ''" />
                </DataRow>
                <DataRow name="Default Chosen Fields" :copy="false" :showBorder="false">
                    <span class="text-sm">{{ formatChosenFields(fieldMappingData.default_chosen_fields) }}</span>
                </DataRow>
            </ContentBlock>

            <ContentBlock :header="`Fields (${fieldsCount})`">
                <div
                    v-for="(field, index) in fieldsSetupData.fields"
                    :key="index"
                    class="py-3 px-4 border-b dark:border-neutral-600 last:border-b-0"
                >
                    <div class="flex items-center justify-between gap-4">
                        <div class="flex items-center gap-3 min-w-0 flex-shrink">
                            <span class="font-mono font-medium text-sm">{{ field.name }}</span>
                            <span class="text-xs text-cyan-600 dark:text-cyan-400">{{ field.type }}</span>
                        </div>
                        <div class="flex items-center gap-4 flex-shrink-0">
                            <div class="flex items-center gap-1.5">
                                <ToggleSwitch :modelValue="field.autocomplete" readonly class="scale-75" />
                                <span class="text-xs text-gray-600 dark:text-gray-400">Autocomplete</span>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <ToggleSwitch :modelValue="field.suggest" readonly class="scale-75" />
                                <span class="text-xs text-gray-600 dark:text-gray-400">Suggest</span>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <ToggleSwitch :modelValue="field.jsonstring" readonly class="scale-75" />
                                <span class="text-xs text-gray-600 dark:text-gray-400">JSON</span>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <ToggleSwitch :modelValue="field.group_by" readonly class="scale-75" />
                                <span class="text-xs text-gray-600 dark:text-gray-400">GROUP BY</span>
                            </div>
                        </div>
                    </div>
                </div>
            </ContentBlock>
        </div>
        <div v-else class="text-center py-8 text-gray-500 dark:text-gray-400">
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
    'fieldsSetupData',
    'fieldMappingData',
    'source',
])
const emit = defineEmits(['prev', 'create'])

const createLoading = ref(false)

const isEditing = computed(() => !!props.source)

const connectionKindOptions = [
    { label: 'ClickHouse', value: 'clickhouse' },
    { label: 'Docker', value: 'docker' },
]

const getConnectionKindLabel = (value) => {
    const option = connectionKindOptions.find((opt) => opt.value === value)
    return option ? option.label : value
}

const fieldsCount = computed(() => {
    return props.fieldsSetupData?.fields?.length || 0
})

const formatChosenFields = (fields) => {
    if (!fields) return '-'
    if (Array.isArray(fields)) return fields.join(', ')
    return fields
}

const handleCreate = () => {
    createLoading.value = true
    emit('create', () => {
        createLoading.value = false
    })
}
</script>
