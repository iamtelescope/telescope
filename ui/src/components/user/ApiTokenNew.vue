<template>
    <Content>
        <template #header>
            <Header>
                <template #title>
                    <KeyRound class="mr-3 w-8 h-8" aria-hidden="true" />
                    New API token
                </template>
            </Header>
        </template>
        <template #content>
            <form class="max-w-[640px]" @submit.prevent="handleCreate" novalidate>
                <div class="border rounded-lg p-6 dark:border-neutral-600 flex flex-col gap-6">
                    <div class="flex flex-col gap-1">
                        <label for="name" class="font-medium">Name</label>
                        <InputText
                            id="name"
                            ref="nameInput"
                            v-model="tokenData.name"
                            fluid
                            autofocus
                            maxlength="255"
                            :invalid="!!createFieldErrors.name"
                            aria-describedby="name-help name-error"
                            @input="createFieldErrors.name = ''"
                        />
                        <ErrorText id="name-error" role="alert" :text="createFieldErrors.name" />
                        <span id="name-help" class="text-sm text-surface-500 dark:text-surface-400">
                            A name you will recognise later, e.g. the script or host that uses it.
                        </span>
                    </div>

                    <div class="flex justify-end gap-2">
                        <Button
                            type="button"
                            severity="secondary"
                            outlined
                            label="Cancel"
                            @click="router.push({ name: 'userProfile' })"
                            size="small"
                        />
                        <Button
                            type="submit"
                            severity="primary"
                            label="Create token"
                            icon="pi pi-check"
                            :loading="createButtonLoading"
                            size="small"
                            data-testid="token-create"
                        />
                    </div>
                </div>
            </form>
        </template>
    </Content>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { KeyRound } from 'lucide-vue-next'

import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

import Content from '@/components/common/Content.vue'
import Header from '@/components/common/Header.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import { AuthService } from '@/sdk/services/auth'

const router = useRouter()
const toast = useToast()
const tokenData = ref({
    name: '',
})
const createFieldErrors = ref({
    name: '',
})
const createButtonLoading = ref(false)

const authSrv = new AuthService()

const handleCreate = async () => {
    if (!tokenData.value.name.trim()) {
        createFieldErrors.value.name = 'Enter a name for the token.'
        return
    }
    createButtonLoading.value = true
    let response = await authSrv.createAPIToken({ name: tokenData.value.name.trim() })
    createButtonLoading.value = false
    // Field errors go under the field, not into a toast as raw serializer output.
    const columns = response.validation?.columns
    if (columns && Object.keys(columns).length) {
        for (const column in columns) {
            createFieldErrors.value[column] = [].concat(columns[column]).join(', ')
        }
        return
    }
    response.sendToast(toast)
    if (response.result) {
        router.push({ name: 'userProfile' })
    }
}
</script>
