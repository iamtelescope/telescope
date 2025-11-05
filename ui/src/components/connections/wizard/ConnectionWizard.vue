<template>
    <Content>
        <template #header>
            <Header>
                <template #title>
                    <Cable class="mr-3 w-8 h-8" />
                    {{ connection ? 'Connections / Edit' : 'Connections' }}
                </template>
            </Header>
        </template>
        <template #content>
            <div class="max-w-7xl">
                <Header v-if="connection">
                    <template #title>
                        <div class="flex items-center">
                            <img
                                :src="require(`@/assets/${connection.kind}.png`)"
                                height="24px"
                                width="24px"
                                class="mr-2"
                                :title="connection.kind"
                            />
                            {{ connection.name }}
                        </div>
                    </template>
                </Header>
                <Header v-else>
                    <template #title>New</template>
                </Header>
                <div class="border radius-lg p-4 dark:border-neutral-600 mt-4">
                    <Stepper v-model:value="activeStep" linear>
                        <StepList>
                            <Step value="1">Target</Step>
                            <Step value="2">Naming</Step>
                            <Step value="3">{{ connection ? 'Review & Save' : 'Review & Create' }}</Step>
                        </StepList>
                        <StepPanels pt:root:class="pb-0 pr-0 pl-0 pt-6">
                            <StepPanel v-slot="{ activateCallback }" value="1">
                                <TargetStep
                                    v-model="targetData"
                                    :connection="connection"
                                    :showBack="false"
                                    @next="activateCallback('2')"
                                />
                            </StepPanel>

                            <StepPanel v-slot="{ activateCallback }" value="2">
                                <NamingStep
                                    v-model="namingData"
                                    @prev="activateCallback('1')"
                                    @next="activateCallback('3')"
                                />
                            </StepPanel>

                            <StepPanel v-slot="{ activateCallback }" value="3">
                                <ReviewStep
                                    :targetData="targetData"
                                    :namingData="namingData"
                                    :connection="connection"
                                    @prev="activateCallback('2')"
                                    @create="handleCreateConnection"
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
import { Cable } from 'lucide-vue-next'
import Content from '@/components/common/Content.vue'
import Header from '@/components/common/Header.vue'
import Stepper from 'primevue/stepper'
import StepList from 'primevue/steplist'
import Step from 'primevue/step'
import StepPanels from 'primevue/steppanels'
import StepPanel from 'primevue/steppanel'
import TargetStep from '@/components/connections/wizard/TargetStep.vue'
import NamingStep from '@/components/connections/wizard/NamingStep.vue'
import ReviewStep from '@/components/connections/wizard/ReviewStep.vue'
import { ConnectionService } from '@/sdk/services/connection'

const props = defineProps(['connection'])

const router = useRouter()
const toast = useToast()
const connectionSrv = new ConnectionService()

const activeStep = ref('1')

// Initialize from connection if editing
const getInitialTargetData = () => {
    if (props.connection) {
        return {
            kind: props.connection.kind,
            data: props.connection.data,
        }
    }
    return {}
}

const getInitialNamingData = () => {
    if (props.connection) {
        return {
            name: props.connection.name,
            description: props.connection.description || '',
        }
    }
    return {}
}

const targetData = ref(getInitialTargetData())
const namingData = ref(getInitialNamingData())

const handleCreateConnection = async (onComplete) => {
    // Build the request data structure
    const data = {
        kind: targetData.value.kind,
        name: namingData.value.name,
        description: namingData.value.description,
        data: targetData.value.data,
    }

    try {
        let response
        if (props.connection) {
            response = await connectionSrv.update(props.connection.id, data)
        } else {
            response = await connectionSrv.create(data)
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
                    detail: props.connection ? 'Connection updated successfully' : 'Connection created successfully',
                    life: 3000,
                })
                if (props.connection) {
                    router.push(`/connections/${props.connection.id}`)
                } else {
                    router.push('/connections')
                }
            }
        } else {
            toast.add({
                severity: 'error',
                summary: 'Error',
                detail: response.errors.join(', ') || 'Failed to save connection',
                life: 5000,
            })
        }
    } catch (error) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to save connection',
            life: 5000,
        })
    } finally {
        if (onComplete) {
            onComplete()
        }
    }
}
</script>
