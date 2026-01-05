<template>
    <div class="flex flex-row">
        <div class="text-3xl font-bold pl-6 pt-6 pb-0 text-nowrap">
            <span v-if="!view">Create new view</span><span v-else>Update view</span>
        </div>
        <div class="flex flex-row w-full justify-end">
            <i class="pi pi-times hover:cursor-pointer p-4" @click="emitClose" />
        </div>
    </div>
    <div class="flex flex-col flex-grow p-6 h-full overflow-auto">
        <div class="flex flex-col h-full">
            <div class="flex flex-col w-full">
                <div class="flex flex-col gap-2">
                    <label for="scope" class="font-medium">Scope</label>
                    <Select
                        v-model="selectedScope"
                        :options="scopes"
                        optionLabel="label"
                        placeholder="Select scope"
                        class="w-full"
                        :disabled="!source.isEditable()"
                    >
                        <template #value="slotProps">
                            <div class="flex items-center" v-if="slotProps.value">
                                <i :class="slotProps.value.icon" />
                                <div class="pl-2">{{ slotProps.value.label }}</div>
                            </div>
                        </template>
                        <template #option="slotProps">
                            <div class="flex items-center">
                                <i :class="slotProps.option.icon" />
                                <div class="pl-2">{{ slotProps.option.label }}</div>
                            </div>
                        </template>
                    </Select>
                    <HelpText text="Views with source scope are available to anyone who has access to this source." />
                </div>
            </div>
            <div class="flex flex-col w-full mt-4">
                <div class="flex flex-col gap-2">
                    <FormLabel label="Name" :invalid="validationErrors.name !== ''" />
                    <InputText id="name" v-model="name" :invalid="validationErrors.name !== ''" />
                    <ErrorText :text="validationErrors.name" />
                </div>
            </div>
            <div class="flex flex-col w-full mt-4">
                <div class="flex flex-col gap-2">
                    <FormLabel label="Description" :invalid="validationErrors.description !== ''" />
                    <Textarea
                        id="description"
                        v-model="description"
                        rows="8"
                        cols="30"
                        style="resize: none"
                        :invalid="validationErrors.description !== ''"
                    />
                    <ErrorText :text="validationErrors.description" />
                </div>
            </div>
            <div class="flex flex-row mt-4" v-if="selectedScope.value !== 'source'">
                <div class="flex flex-col">
                    <div class="flex flex-row items-center">
                        <ToggleSwitch id="shared" v-model="shared" />
                        <label for="shared" class="mr-2 ml-2 font-medium">Shared</label>
                    </div>
                    <ErrorText :text="validationErrors.shared" />
                    <HelpText text="Shared views can be used by other source users" />
                </div>
            </div>
            <Message v-if="nonFieldErrors.length !== 0" class="mt-2" severity="error"
                ><span class="font-medium">Validation failed: </span>{{ nonFieldErrors.join(' ') }}
            </Message>
            <div class="flex flex-col h-full justify-end">
                <div class="flex flex-row mt-4 w-full justify-end">
                    <Button
                        label="Cancel"
                        severity="primary"
                        class="mr-2"
                        text
                        size="small"
                        :disabled="submitButtonLoading"
                        @click="emitClose"
                    />
                    <Button
                        :label="submitButtonLabel"
                        severity="primary"
                        icon="pi pi-check"
                        size="small"
                        @click="handleFormSubmit"
                        :loading="submitButtonLoading"
                    />
                </div>
            </div>
        </div>
    </div>
</template>
<script setup>
import { ref, computed } from 'vue'
import { InputText, ToggleSwitch, Message, Textarea, Button, Select, useToast } from 'primevue'
import FormLabel from '@/components/common/FormLabel.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import HelpText from '@/components/common/HelpText.vue'

import { useSourceControlsStore } from '@/stores/sourceControls'
import { SourceService } from '@/sdk/services/source'
import { SavedView } from '@/sdk/models/savedView'

const props = defineProps(['source', 'view'])
const emit = defineEmits(['close', 'change'])
const toast = useToast()
const sourceSrv = new SourceService()
const sourceControlsStore = useSourceControlsStore()

const submitButtonLabel = computed(() => {
    if (props.view) {
        return 'Save'
    } else {
        return 'Create'
    }
})
const validationErrors = ref({
    name: '',
    description: '',
    scope: '',
    shared: '',
})
const nonFieldErrors = ref('')

const scopePersonal = { label: 'Personal', icon: 'pi pi-user', value: 'personal' }
const scopeSource = { label: 'Source', icon: 'pi pi-database', value: 'source' }

const submitButtonLoading = ref(false)
const selectedScope = ref(scopePersonal)

const scopes = computed(() => {
    let scopes = [scopePersonal]
    if (props.source.isEditable()) {
        scopes.push(scopeSource)
    }
    return scopes
})

const emitClose = () => {
    emit('close')
}

const shared = ref(false)
const name = ref('')
const description = ref('')

if (props.view) {
    console.log(props.view)
    shared.value = props.view.shared
    name.value = props.view.name
    description.value = props.view.description
    // Initialize scope from the view being edited
    selectedScope.value = props.view.scope === 'source' ? scopeSource : scopePersonal
}

const handleFormSubmit = async () => {
    submitButtonLoading.value = true
    let data = {
        scope: selectedScope.value.value,
        name: name.value,
        description: description.value,
        shared: shared.value,
        data: sourceControlsStore.viewParams,
    }
    let response
    if (props.view) {
        data.data = props.view.data
        response = await sourceSrv.updateSavedView(props.source.slug, props.view.slug, data)
    } else {
        response = await sourceSrv.createSavedView(props.source.slug, data)
    }
    response.sendToast(toast)
    submitButtonLoading.value = false
    if (response.result) {
        if (!response.validation.result) {
            nonFieldErrors.value = response.validation.non_column
            for (const column in response.validation.columns) {
                validationErrors.value[column] = response.validation.columns[column].join(', ')
            }
        } else {
            emit('change', new SavedView(response.data))
            emitClose()
        }
    }
}
</script>
