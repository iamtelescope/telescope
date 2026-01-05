<template>
    <Content>
        <template #header>
            <Header>
                <template #title>
                    <Database class="mr-3 w-8 h-8" />
                    {{ source ? 'Sources / Edit' : 'Sources' }}
                </template>
            </Header>
        </template>
        <template #content>
            <div class="max-w-7xl">
                <Header v-if="source">
                    <template #title>{{ source.slug }}</template>
                </Header>
                <Header v-else>
                    <template #title>New</template>
                </Header>
                <div class="border radius-lg p-4 dark:border-neutral-600 mt-4">
                    <Stepper v-model:value="activeStep" linear>
                        <StepList>
                            <Step value="1">Connection</Step>
                            <Step value="2">Columns Setup</Step>
                            <Step value="3">Column Mapping</Step>
                            <Step value="4">Naming</Step>
                            <Step value="5">{{ source ? 'Review & Save' : 'Review & Create' }}</Step>
                        </StepList>
                        <StepPanels pt:root:class="pb-0 pr-0 pl-0 pt-6">
                            <StepPanel v-slot="{ activateCallback }" value="1">
                                <ConnectionStep
                                    v-model="connectionData"
                                    :connections="connections"
                                    :showBack="false"
                                    @next="activateCallback('2')"
                                />
                            </StepPanel>

                            <StepPanel v-slot="{ activateCallback }" value="2">
                                <ColumnsSetupStep
                                    v-model="columnsSetupData"
                                    :connectionData="connectionData"
                                    @prev="activateCallback('1')"
                                    @next="activateCallback('3')"
                                />
                            </StepPanel>

                            <StepPanel v-slot="{ activateCallback }" value="3">
                                <ColumnMappingStep
                                    v-model="columnMappingData"
                                    :columnsSetupData="columnsSetupData"
                                    :connectionData="connectionData"
                                    @prev="activateCallback('2')"
                                    @next="activateCallback('4')"
                                />
                            </StepPanel>

                            <StepPanel v-slot="{ activateCallback }" value="4">
                                <BasicInfoStep
                                    v-model="basicInfo"
                                    :isEditing="!!source"
                                    @prev="activateCallback('3')"
                                    @next="activateCallback('5')"
                                />
                            </StepPanel>

                            <StepPanel v-slot="{ activateCallback }" value="5">
                                <Step3
                                    v-model="step3Data"
                                    :basicInfo="basicInfo"
                                    :connectionData="connectionData"
                                    :columnsSetupData="columnsSetupData"
                                    :columnMappingData="columnMappingData"
                                    :source="source"
                                    @prev="activateCallback('4')"
                                    @create="handleCreateSource"
                                />
                            </StepPanel>
                        </StepPanels>
                    </Stepper>
                </div>
            </div>
        </template>
    </Content>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { Database } from 'lucide-vue-next'
import Content from '@/components/common/Content.vue'
import Header from '@/components/common/Header.vue'
import Stepper from 'primevue/stepper'
import StepList from 'primevue/steplist'
import Step from 'primevue/step'
import StepPanels from 'primevue/steppanels'
import StepPanel from 'primevue/steppanel'
import BasicInfoStep from '@/components/sources/wizard/BasicInfoStep.vue'
import ConnectionStep from '@/components/sources/wizard/ConnectionStep.vue'
import ColumnsSetupStep from '@/components/sources/wizard/ColumnsSetupStep.vue'
import ColumnMappingStep from '@/components/sources/wizard/ColumnMappingStep.vue'
import Step3 from '@/components/sources/wizard/Step3.vue'
import { SourceService } from '@/sdk/services/source'

const props = defineProps(['source', 'connections'])

const router = useRouter()
const toast = useToast()
const sourceSrv = new SourceService()

const activeStep = ref('1')

// Initialize from source if editing
const getInitialBasicInfo = () => {
    if (props.source) {
        return {
            slug: props.source.slug,
            name: props.source.name,
            description: props.source.description || '',
        }
    }
    return {}
}

const getInitialConnectionData = () => {
    if (props.source && props.source.connectionId) {
        // conn object doesn't have id, so we always need to add it
        const connectionObj = {
            id: props.source.connectionId,
            kind: props.source.kind,
        }

        return {
            connection: connectionObj,
            database: props.source.data?.database || '',
            table: props.source.data?.table || '',
            settings: props.source.data?.settings || '',
            namespace_label_selector: props.source.data?.namespace_label_selector || '',
            namespace_field_selector: props.source.data?.namespace_field_selector || '',
            namespace: props.source.data?.namespace || '',
        }
    }
    return {}
}

const getInitialColumnsSetupData = () => {
    if (props.source && props.source.columns) {
        // Convert columns object to array
        const columnsArray = Object.entries(props.source.columns).map(([name, column]) => ({
            name,
            display_name: column.display_name || '',
            type: column.type,
            values: column.values || '',
            autocomplete: column.autocomplete || false,
            suggest: column.suggest || false,
            jsonstring: column.jsonstring || false,
            group_by: column.group_by || false,
        }))
        return { columns: columnsArray }
    }
    return { columns: [] }
}

const getInitialColumnMappingData = () => {
    if (props.source) {
        return {
            time_column: props.source.timeColumn,
            date_column: props.source.dateColumn || '',
            severity_column: props.source.severityColumn || '',
            default_chosen_columns: props.source.defaultChosenColumns || [],
            execute_query_on_open: props.source.executeQueryOnOpen ?? true,
        }
    }
    return {}
}

const basicInfo = ref(getInitialBasicInfo())
const connectionData = ref(getInitialConnectionData())
const columnsSetupData = ref(getInitialColumnsSetupData())
const columnMappingData = ref(getInitialColumnMappingData())
const step3Data = ref({})

const handleCreateSource = async (onComplete) => {
    const data = {
        slug: basicInfo.value.slug,
        name: basicInfo.value.name,
        description: basicInfo.value.description,
        time_column: columnMappingData.value.time_column,
        date_column: columnMappingData.value.date_column || '',
        severity_column: columnMappingData.value.severity_column || '',
        default_chosen_columns: columnMappingData.value.default_chosen_columns,
        execute_query_on_open: columnMappingData.value.execute_query_on_open ?? true,
        columns: {},
        kind: connectionData.value.connection.kind,
        connection: {
            connection_id: connectionData.value.connection.id,
        },
        data: {},
    }

    if (connectionData.value.connection.kind === 'clickhouse') {
        data.data.database = connectionData.value.database
        data.data.table = connectionData.value.table
        if (connectionData.value.settings) {
            data.data.settings = connectionData.value.settings
        }
    }

    if (connectionData.value.connection.kind === 'kubernetes') {
        data.data.namespace_label_selector = connectionData.value.namespace_label_selector || ''
        data.data.namespace_field_selector = connectionData.value.namespace_field_selector || ''
        data.data.namespace = connectionData.value.namespace || ''
    }

    if (columnsSetupData.value.columns && columnsSetupData.value.columns.length > 0) {
        columnsSetupData.value.columns.forEach((column) => {
            data.columns[column.name] = {
                display_name: column.display_name || '',
                type: column.type,
                values: column.values || '',
                autocomplete: column.autocomplete,
                suggest: column.suggest,
                jsonstring: column.jsonstring,
                group_by: column.group_by,
            }
        })
    }

    // Make the API call - create or update
    let response
    if (props.source) {
        response = await sourceSrv.updateSource(props.source.slug, data)
    } else {
        response = await sourceSrv.createSource(data)
    }

    if (onComplete) {
        onComplete()
    }

    if (response.result) {
        if (response.validation && !response.validation.result) {
            toast.add({
                severity: 'error',
                summary: 'Validation Error',
                detail: 'Please check the form for errors',
                life: 5000,
            })
        } else {
            toast.add({
                severity: 'success',
                summary: 'Success',
                detail: props.source ? 'Source updated successfully' : 'Source created successfully',
                life: 3000,
            })
            router.push({ name: 'source', params: { sourceSlug: response.data.slug } })
        }
    } else {
        response.sendToast(toast)
    }
}
</script>
