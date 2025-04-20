<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-[1000px] w-[1000px] max-w-[1000px]">
            <div class="mb-14">
                <span class="font-bold text-3xl">
                    <i class="pi pi-user text-3xl mr-1"></i>
                    <span class="text-gray-400">User profile: </span>
                    Create new API Token</span
                >
            </div>
            <div class="flex flex-row mb-5 items-start">
                <div class="flex justify-end w-full items-center">
                    <div class="flex flex-col w-full">
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
                </div>
            </div>
            <div class="flex flex-row justify-end w-full">
                <Button
                    class="ml-2 pl-6 pr-6"
                    severity="primary"
                    label="Create"
                    @click="handleCreate"
                    :loading="createButtonLoading"
                />
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'

import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

import { useNavStore } from '@/stores/nav'
import ErrorText from '@/components/common/ErrorText.vue'
import { AuthService } from '@/sdk/services/auth'

const router = useRouter()
const toast = useToast()
const navStore = useNavStore()
const tokenData = ref({
    name: '',
})
const createFieldErrors = ref({
    name: '',
})
const createButtonLoading = ref(false)

const authSrv = new AuthService()

navStore.updatev2(['rbac', 'groups', 'New'])

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
