<template>
    <FloatLabel variant="on">
        <MultiSelect
            id="deployment"
            v-model="selectedDeployments"
            :initialValues="initialValuesDeployment"
            optionLabel="name"
            display="chip"
            :options="deploymentData"
            :loading="loadingDeployment"
            class="mr-2 min-w-80"
            :maxSelectedLabels="5"
            filter
            autoFilterFocus 
            @change="onDeploymentsChange"
        >
            <template #option="slotProps">
                <div class="flex flex-col">
                    <div class="flex flex-fow items-center">
                        <i
                            class="pi pi-circle-fill text-gray-300"
                            :class="{
                                'text-green-500': slotProps.option.status == 'Available',
                                'text-orange-500': slotProps.option.status == 'Progressing',
                                'text-red-500': slotProps.option.status == 'Failed',
                            }"
                        ></i>
                        <div class="pl-2">[{{ slotProps.option.status }}]</div>
                        <div class="pl-3 text-sm text-gray-500">
                        ({{ slotProps.option.replicas_ready ?? '-' }} /
                        {{ slotProps.option.replicas_desired ?? '-' }})
                        </div>
                        <div class="pl-2 font-medium">{{ slotProps.option.name }}</div>
                    </div>
                </div>
            </template>
            <template #dropdownicon>
                <i class="pi pi-box" />
            </template>
        </MultiSelect>
        <label for="deployment">Deployment</label>
    </FloatLabel>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { MultiSelect, FloatLabel } from 'primevue'

import { useGetSourceContextFieldData } from '@/composables/sources/useSourceService'

const props = defineProps(['source', 'Deployments'])
const emit = defineEmits(['fieldChanged'])

const {
    data: deploymentData,
    error: errorDeployment,
    loading: loadingDeployment,
    validation: validationDeployment,
    load: loadDeployment,
} = useGetSourceContextFieldData()

const initialValuesDeployment = ref([])

const selectedDeployments = ref([])

const onDeploymentsChange = () => {
    const names = selectedDeployments.value.map((deployment) => deployment.name)
    emit('fieldChanged', {
        name: 'deployment',
        value: names,
    })
}

onMounted(() => {
    loadDeployment(props.source.slug, { field: 'deployment' })
})


watch(deploymentData, () => {
    if (props.deployments) {
        for (const deployment of deploymentData.value) {
            if (props.deployments.includes(deployment.name)) {
                selectedDeployments.value.push(deployment)
            }
        }
    }
})
watch(
    () => props.deployments,
    (newVal) => {
        selectedDeployments.value = []
        if (newVal && deploymentData.value) {
            for (const cont of deploymentData.value) {
                if (newVal.includes(cont.name)) {
                    selectedDeployments.value.push(cont)
                }
            }
        }
    },
    { deep: true },
)

watch(
    () => props.source,
    () => {
        selectedDeployments.value = []
        
        loadDeployment(props.source.slug, { field: 'deployment' })
    },
    { deep: true }
)
</script>