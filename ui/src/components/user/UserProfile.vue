<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-[1000px] w-[1000px] max-w-[1000px]">
            <div class="flex flex-row mb-14">
                <div class="flex flex-col justify-start text-nowrap">
                    <span class="font-medium text-3xl">
                        <i class="pi pi-user text-3xl mr-1"></i>
                        <span class="text-gray-400">User profile: </span>
                        {{ user.username }}
                    </span>
                </div>
            </div>
            <div class="w-full">
                <DataRow name="Username" :value="user.username" />
                <DataRow name="Login type" :value="user.type" />
                <DataRow name="First name">{{ user.firstName || '–' }}</DataRow>
                <DataRow name="Last name">{{ user.lastName || '–' }}</DataRow>
                <DataRow name="Permissions">
                    <div class="flex flex-wrap gap-2" v-if="user.permissions.length > 0">
                        <Badge
                            v-for="perm in user.permissions"
                            :key="perm"
                            :value="perm"
                            severity="secondary"
                            size="large"
                        ></Badge>
                    </div>
                    <span v-else>–</span>
                </DataRow>
                <DataRow name="Groups">
                    <div class="flex flex-wrap gap-2" v-if="user.groups.length > 0">
                        <Badge
                            v-for="group in user.groups"
                            :key="group"
                            :value="group"
                            severity="secondary"
                            size="large"
                        ></Badge>
                    </div>
                    <span v-else>–</span>
                </DataRow>
            </div>
            <div class="w-full">
                <div class="flex flex-row w-full mt-9 align-middle">
                    <div class="flex items-center font-medium text-xl text-nowrap">API Tokens</div>
                    <div class="flex items-center w-full justify-end">
                        <Button
                            severity="primary"
                            size="small"
                            icon="pi pi-plus"
                            label="New token"
                            @click="handleApiTokenCreate"
                        />
                        <Button
                            severity="danger"
                            size="small"
                            :label="deleteTokenBtnLabel"
                            :disabled="selectedTokens.length == 0"
                            :outlined="selectedTokens.length == 0"
                            @click="handleDeleteTokens"
                            :loading="deleteTokenBtnLoading"
                            class="ml-2"
                        />
                    </div>
                </div>
                <DataView :loadings="[loading]" :errors="[error]">
                    <div class="flex flex-row w-full mt-5">
                        <DataTable
                            v-if="tokens.length"
                            :value="tokens"
                            sortField="name"
                            removableSort
                            :sortOrder="1"
                            class="w-full"
                            v-model:selection="selectedTokens"
                            dataKey="token"
                        >
                            <Column selectionMode="multiple" headerStyle="width: 3rem"></Column>

                            <Column field="name" sortable header="Name" />
                            <Column sortable header="Created">
                                <template #body="slotProps">
                                    <DateTimeFormatted :value="slotProps.data.created" />
                                </template>
                            </Column>
                            <Column header="Token" bodyClass="font-mono">
                                <template #body="slotProps">
                                    {{ slotProps.data.token }}
                                    <Copy :value="slotProps.data.token" />
                                </template>
                            </Column>
                        </DataTable>
                        <div v-else>There is no API tokens</div>
                    </div>
                </DataView>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { Badge, Button, Column, DataTable, useToast } from 'primevue'
import { AuthService } from '@/sdk/services/auth'
import { useAuthStore } from '@/stores/auth'
import { useNavStore } from '@/stores/nav'
import Copy from '@/components/common/Copy.vue'
import DataRow from '@/components/common/DataRow.vue'
import { useGetCurrentUserAPITokens } from '@/composables/auth/useAuthService'
import DataView from '@/components/common/DataView.vue'
import DateTimeFormatted from '@/components/common/DateTimeFormatted.vue'

const router = useRouter()
const navStore = useNavStore()
const toast = useToast()

const { user } = useAuthStore()
const { tokens, error, loading, load: userLoad } = useGetCurrentUserAPITokens()

const authSrv = new AuthService()
const selectedTokens = ref([])
const deleteTokenBtnLoading = ref(false)
navStore.updatev2(['profile'])

const deleteTokenBtnLabel = computed(() => {
    let text = 'Delete'
    let size = selectedTokens.value.length
    let str_size = ''
    if (size > 0) {
        str_size = `${size} `
    }
    text += ' ' + str_size + 'token'
    if (size == 0 || size > 1) {
        text += 's'
    }
    return text
})

const handleApiTokenCreate = () => {
    router.push({ name: 'apiTokenNew' })
}

const handleDeleteTokens = async () => {
    deleteTokenBtnLoading.value = true

    let response = await authSrv.deleteCurrentUserAPITokens(selectedTokens.value.map((t) => t.token))
    deleteTokenBtnLoading.value = false
    selectedTokens.value = []

    response.sendToast(toast)
    if (response.result) {
        userLoad()
    }
}
</script>
