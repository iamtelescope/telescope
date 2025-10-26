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
                            <Step value="2">Fields Setup</Step>
                            <Step value="3">Field Mapping</Step>
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
                                <FieldsSetupStep
                                    v-model="fieldsSetupData"
                                    :connectionData="connectionData"
                                    @prev="activateCallback('1')"
                                    @next="activateCallback('3')"
                                />
                            </StepPanel>

                            <StepPanel v-slot="{ activateCallback }" value="3">
                                <FieldMappingStep
                                    v-model="fieldMappingData"
                                    :fieldsSetupData="fieldsSetupData"
                                    :connectionData="connectionData"
                                    @prev="activateCallback('2')"
                                    @next="activateCallback('4')"
                                />
                            </StepPanel>

                            <StepPanel v-slot="{ activateCallback }" value="4">
                                <BasicInfoStep
                                    v-model="basicInfo"
                                    @prev="activateCallback('3')"
                                    @next="activateCallback('5')"
                                />
                            </StepPanel>

                            <StepPanel v-slot="{ activateCallback }" value="5">
                                <Step3
                                    v-model="step3Data"
                                    :basicInfo="basicInfo"
                                    :connectionData="connectionData"
                                    :fieldsSetupData="fieldsSetupData"
                                    :fieldMappingData="fieldMappingData"
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
import FieldsSetupStep from '@/components/sources/wizard/FieldsSetupStep.vue'
import FieldMappingStep from '@/components/sources/wizard/FieldMappingStep.vue'
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
        }
    }
    return {}
}

const getInitialFieldsSetupData = () => {
    if (props.source && props.source.fields) {
        // Convert fields object to array
        const fieldsArray = Object.entries(props.source.fields).map(([name, field]) => ({
            name,
            display_name: field.display_name || '',
            type: field.type,
            values: field.values || '',
            autocomplete: field.autocomplete || false,
            suggest: field.suggest || false,
            jsonstring: field.jsonstring || false,
            group_by: field.group_by || false,
        }))
        return { fields: fieldsArray }
    }
    return {}
}

const getInitialFieldMappingData = () => {
    if (props.source) {
        return {
            time_field: props.source.timeField,
            date_field: props.source.dateField || '',
            severity_field: props.source.severityField || '',
            default_chosen_fields: props.source.defaultChosenFields || [],
        }
    }
    return {}
}

const basicInfo = ref(getInitialBasicInfo())
const connectionData = ref(getInitialConnectionData())
const fieldsSetupData = ref(getInitialFieldsSetupData())
const fieldMappingData = ref(getInitialFieldMappingData())
const step3Data = ref({})

const handleCreateSource = async (onComplete) => {
    // Build the request data structure
    const data = {
        // Basic info
        slug: basicInfo.value.slug,
        name: basicInfo.value.name,
        description: basicInfo.value.description,

        // Field mapping
        time_field: fieldMappingData.value.time_field,
        date_field: fieldMappingData.value.date_field || '',
        severity_field: fieldMappingData.value.severity_field || '',
        default_chosen_fields: fieldMappingData.value.default_chosen_fields,

        // Dynamic fields - convert array to object with field names as keys
        fields: {},

        // Connection kind
        kind: connectionData.value.connection.kind,

        // Connection info - only connection_id
        connection: {
            connection_id: connectionData.value.connection.id,
        },

        // Source-specific data
        data: {},
    }

    // Add database and table to data field for ClickHouse connections
    if (connectionData.value.connection.kind === 'clickhouse') {
        data.data.database = connectionData.value.database
        data.data.table = connectionData.value.table
    }

    // Convert fields array to object
    if (fieldsSetupData.value.fields && fieldsSetupData.value.fields.length > 0) {
        fieldsSetupData.value.fields.forEach((field) => {
            data.fields[field.name] = {
                display_name: field.display_name || '',
                type: field.type,
                values: field.values || '',
                autocomplete: field.autocomplete,
                suggest: field.suggest,
                jsonstring: field.jsonstring,
                group_by: field.group_by,
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
