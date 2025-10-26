<template>
    <Content>
        <template #header>
            <Header>
                <template #title>
                    <i class="pi pi-key mr-3 text-3xl"></i>
                    API Tokens
                </template>
            </Header>
        </template>
        <template #content>
            <div class="max-w-7xl">
                <Header>
                    <template #title>New</template>
                </Header>
                <div class="border radius-lg p-6 dark:border-neutral-600 mt-4">
                    <div class="flex flex-col gap-6">
                        <div class="flex flex-col">
                            <FloatLabel variant="on">
                                <InputText
                                    id="name"
                                    v-model="tokenData.name"
                                    fluid
                                    :invalid="createFieldErrors.name != ''"
                                    @keyup.enter="handleCreate"
                                />
                                <label for="name">Name</label>
                            </FloatLabel>
                            <ErrorText :text="createFieldErrors.name" />
                        </div>

                        <div class="flex justify-end gap-2">
                            <Button
                                severity="secondary"
                                label="Cancel"
                                icon="pi pi-times"
                                @click="router.push({ name: 'userProfile' })"
                                size="small"
                            />
                            <Button
                                severity="primary"
                                label="Create"
                                icon="pi pi-check"
                                @click="handleCreate"
                                :loading="createButtonLoading"
                                size="small"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </Content>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'

import FloatLabel from 'primevue/floatlabel'
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
    createButtonLoading.value = true
    let response = await authSrv.createAPIToken({ name: tokenData.value.name })
    createButtonLoading.value = false
    response.sendToast(toast)
    if (response.result) {
        if (!response.validation.result) {
            for (const field in response.validation.fields) {
                createFieldErrors.value[field] = response.validation.fields[field].join(', ')
            }
        } else {
            router.push({ name: 'userProfile' })
        }
    }
}
</script>
