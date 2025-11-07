<template>
    <Content>
        <template #header>
            <Header>
                <template #title> <User class="mr-3 w-8 h-8" /> User </template>
            </Header>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <div class="flex flex-col max-w-[800px]">
                    <Header>
                        <template #title>{{ user.username }} </template>
                        <template #actions>
                            <Button
                                severity="primary"
                                label="Logout"
                                icon="pi pi-sign-out"
                                @click="handleLogout"
                                size="small"
                            />
                        </template>
                    </Header>
                    <div class="mt-4">
                        <ContentBlock header="Profile">
                            <DataRow name="Username" :value="user.username" :copy="false" />
                            <DataRow name="Login type" :value="user.type" :copy="false" />
                            <DataRow name="First name">{{ user.firstName || '–' }}</DataRow>
                            <DataRow name="Last name">{{ user.lastName || '–' }}</DataRow>
                            <DataRow name="Permissions" class="pr-2">
                                <div class="flex flex-wrap gap-2" v-if="user.permissions.length > 0">
                                    <Tag
                                        v-for="perm in user.permissions"
                                        :key="perm"
                                        :value="perm"
                                        severity="secondary"
                                    />
                                </div>
                                <span v-else>&ndash;</span>
                            </DataRow>
                            <DataRow name="Groups" :showBorder="false">
                                <div class="flex flex-wrap gap-2" v-if="user.groups.length > 0">
                                    <Tag
                                        v-for="group in user.groups"
                                        :key="group"
                                        :value="group"
                                        severity="secondary"
                                    />
                                </div>
                                <span v-else>&ndash;</span>
                            </DataRow>
                        </ContentBlock>

                        <ContentBlock header="API Tokens" class="mt-3">
                            <template #actions>
                                <div class="flex flex-wrap gap-2">
                                    <Button
                                        severity="primary"
                                        size="small"
                                        icon="pi pi-plus"
                                        label="New token"
                                        @click="handleApiTokenCreate"
                                        class="max-h-[25px]"
                                    />
                                    <Button
                                        severity="danger"
                                        size="small"
                                        :label="deleteTokenBtnLabel"
                                        :disabled="selectedTokens.length == 0"
                                        :outlined="selectedTokens.length == 0"
                                        @click="handleDeleteTokens"
                                        :loading="deleteTokenBtnLoading"
                                        class="max-h-[25px]"
                                    />
                                </div>
                            </template>
                            <DataTable
                                v-if="tokens.length"
                                :value="tokens"
                                sortField="name"
                                removableSort
                                size="small"
                                :sortOrder="1"
                                :paginator="tokens.length > 50"
                                :rows="50"
                                :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                                :row-hover="true"
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
                                        <div class="flex items-center gap-2">
                                            <span v-if="visibleTokens[slotProps.data.token]">
                                                {{ slotProps.data.token }}
                                            </span>
                                            <span v-else class="text-gray-400"> •••••••••••••••••••••••••••••••• </span>
                                            <Button
                                                :icon="
                                                    visibleTokens[slotProps.data.token]
                                                        ? 'pi pi-eye-slash'
                                                        : 'pi pi-eye'
                                                "
                                                text
                                                rounded
                                                size="small"
                                                @click="toggleTokenVisibility(slotProps.data.token)"
                                                class="h-8 w-8"
                                            />
                                        </div>
                                    </template>
                                </Column>
                                <template #empty>
                                    <div
                                        class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400"
                                    >
                                        <KeyRound class="w-10 h-10 mb-4 opacity-50" />
                                        <p class="text-lg font-medium mb-2">No API tokens found</p>
                                    </div>
                                </template>
                            </DataTable>
                            <div
                                v-else
                                class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400"
                            >
                                <KeyRound class="w-10 h-10 mb-4 opacity-50" />
                                <p class="text-lg font-medium mb-2">No API tokens found</p>
                            </div>
                        </ContentBlock>
                    </div>
                </div>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { KeyRound, User } from 'lucide-vue-next'

import { Button, Column, DataTable, useToast } from 'primevue'
import { AuthService } from '@/sdk/services/auth'
import { useAuthStore } from '@/stores/auth'
import Content from '@/components/common/Content.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import DataRow from '@/components/common/DataRow.vue'
import DataView from '@/components/common/DataView.vue'
import DateTimeFormatted from '@/components/common/DateTimeFormatted.vue'
import Header from '@/components/common/Header.vue'
import Tag from '@/components/common/Tag.vue'
import { useGetCurrentUserAPITokens } from '@/composables/auth/useAuthService'

const router = useRouter()
const toast = useToast()

const { user } = useAuthStore()
const { tokens, error, loading, load: userLoad } = useGetCurrentUserAPITokens()

const authSrv = new AuthService()
const selectedTokens = ref([])
const deleteTokenBtnLoading = ref(false)
const visibleTokens = ref({})

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

const toggleTokenVisibility = (token) => {
    visibleTokens.value[token] = !visibleTokens.value[token]
}

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

const handleLogout = () => {
    window.location.href = '/logout'
}
</script>
