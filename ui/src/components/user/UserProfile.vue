<template>
    <Content>
        <template #header>
            <Header>
                <template #title> <User class="mr-3 w-8 h-8" aria-hidden="true" /> Profile </template>
                <template #actions>
                    <Button
                        severity="secondary"
                        outlined
                        label="Log out"
                        icon="pi pi-sign-out"
                        @click="handleLogout"
                        size="small"
                        data-testid="profile-logout"
                    />
                </template>
            </Header>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <div class="flex flex-col max-w-[1000px]">
                    <div class="flex items-center gap-3">
                        <Avatar
                            :image="user.avatarUrl || null"
                            :icon="user.avatarUrl ? null : 'pi pi-user'"
                            size="large"
                            class="avaimg"
                            style="color: rgb(209 213 219); background-color: var(--p-primary-700)"
                        />
                        <div>
                            <div class="text-2xl font-medium">{{ user.username }}</div>
                            <div class="text-surface-500 dark:text-surface-400">
                                {{ fullName || 'No name set' }} · {{ user.type }} account
                            </div>
                        </div>
                    </div>
                    <div class="mt-4">
                        <ContentBlock header="Account">
                            <DataRow name="Username" :value="user.username" :copy="false" />
                            <DataRow name="Login type" :value="user.type" :copy="false" />
                            <DataRow name="First name">{{ user.firstName || '—' }}</DataRow>
                            <DataRow name="Last name">{{ user.lastName || '—' }}</DataRow>
                            <DataRow name="Permissions" class="pr-2">
                                <div class="flex flex-wrap gap-2 py-1" v-if="permissions.length > 0">
                                    <Tag
                                        v-for="perm in permissions"
                                        :key="perm.code"
                                        :value="perm.label"
                                        severity="secondary"
                                        v-tooltip.top="perm.code"
                                        data-testid="profile-permission"
                                    />
                                </div>
                                <span v-else class="text-surface-500">No global permissions</span>
                            </DataRow>
                            <DataRow name="Groups" :showBorder="false">
                                <div class="flex flex-wrap gap-2" v-if="user.groups.length > 0">
                                    <Tag
                                        v-for="group in user.groups"
                                        :key="group.name || group"
                                        :value="group.name || group"
                                        severity="secondary"
                                    />
                                </div>
                                <span v-else class="text-surface-500">Not in any group</span>
                            </DataRow>
                        </ContentBlock>

                        <ContentBlock header="API tokens" class="mt-3">
                            <template #actions>
                                <div class="flex flex-wrap gap-2">
                                    <Button
                                        severity="danger"
                                        outlined
                                        size="small"
                                        icon="pi pi-trash"
                                        :label="deleteTokenBtnLabel"
                                        v-if="selectedTokens.length"
                                        @click="handleDeleteTokens"
                                        :loading="deleteTokenBtnLoading"
                                        class="max-h-[28px]"
                                        data-testid="profile-delete-tokens"
                                    />
                                    <Button
                                        severity="primary"
                                        size="small"
                                        icon="pi pi-plus"
                                        label="New token"
                                        @click="handleApiTokenCreate"
                                        class="max-h-[28px]"
                                    />
                                </div>
                            </template>
                            <DataTable
                                v-if="tokens && tokens.length"
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
                                <Column field="created" sortable header="Created">
                                    <template #body="slotProps">
                                        <DateTimeFormatted :value="slotProps.data.created" relative />
                                    </template>
                                </Column>
                                <Column header="Token" bodyClass="font-mono">
                                    <template #body="slotProps">
                                        <div class="flex items-center gap-1">
                                            <span v-if="visibleTokens[slotProps.data.token]" class="break-all">
                                                {{ slotProps.data.token }}
                                            </span>
                                            <span v-else class="text-surface-400"> •••••••••••••••••••••••• </span>
                                            <Button
                                                :icon="
                                                    visibleTokens[slotProps.data.token]
                                                        ? 'pi pi-eye-slash'
                                                        : 'pi pi-eye'
                                                "
                                                text
                                                rounded
                                                size="small"
                                                :aria-label="
                                                    visibleTokens[slotProps.data.token] ? 'Hide token' : 'Show token'
                                                "
                                                v-tooltip.top="
                                                    visibleTokens[slotProps.data.token] ? 'Hide token' : 'Show token'
                                                "
                                                @click="toggleTokenVisibility(slotProps.data.token)"
                                                class="h-8 w-8"
                                            />
                                            <Copy :value="slotProps.data.token" label="Copy token" />
                                        </div>
                                    </template>
                                </Column>
                            </DataTable>
                            <EmptyState
                                v-else
                                compact
                                :icon="KeyRound"
                                title="No API tokens yet"
                                description="Tokens let scripts and the MCP server call the Telescope API as you."
                            >
                                <Button
                                    label="New token"
                                    icon="pi pi-plus"
                                    size="small"
                                    @click="handleApiTokenCreate"
                                />
                            </EmptyState>
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

import { Avatar, Button, Column, DataTable, useToast } from 'primevue'
import { AuthService } from '@/sdk/services/auth'
import { useAuthStore } from '@/stores/auth'
import Content from '@/components/common/Content.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import Copy from '@/components/common/Copy.vue'
import DataRow from '@/components/common/DataRow.vue'
import DataView from '@/components/common/DataView.vue'
import DateTimeFormatted from '@/components/common/DateTimeFormatted.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import Header from '@/components/common/Header.vue'
import Tag from '@/components/common/Tag.vue'
import { useConfirmDestructive } from '@/components/common/confirm'
import { useGetCurrentUserAPITokens } from '@/composables/auth/useAuthService'

const router = useRouter()
const toast = useToast()
const confirmDestructive = useConfirmDestructive()

const { user } = useAuthStore()
const { tokens, error, loading, load: userLoad } = useGetCurrentUserAPITokens()

const authSrv = new AuthService()
const selectedTokens = ref([])
const deleteTokenBtnLoading = ref(false)
const visibleTokens = ref({})

const fullName = computed(() => [user.firstName, user.lastName].filter(Boolean).join(' '))

const VERBS = {
    create: 'Create',
    read: 'View',
    edit: 'Edit',
    delete: 'Delete',
    use: 'Use',
    grant: 'Grant access to',
    raw_query: 'Run raw queries on',
}
const NAMED = { manage_rbac: 'Manage users, groups and roles', manage_alert_channels: 'Manage alert channels' }

// "global_raw_query_source" -> "Run raw queries on sources"; the raw code stays in the tooltip.
const permissionLabel = (code) => {
    if (NAMED[code]) return NAMED[code]
    const m = /^global_(.+)_(source|connection)$/.exec(code)
    if (m && VERBS[m[1]]) return `${VERBS[m[1]]} ${m[2]}s`
    return code.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
}
const permissions = computed(() =>
    user.permissions
        .map((code) => ({ code, label: permissionLabel(code) }))
        .sort((a, b) => a.label.localeCompare(b.label)),
)

const deleteTokenBtnLabel = computed(() => {
    const size = selectedTokens.value.length
    return `Delete ${size} token${size === 1 ? '' : 's'}`
})

const toggleTokenVisibility = (token) => {
    visibleTokens.value[token] = !visibleTokens.value[token]
}

const handleApiTokenCreate = () => {
    router.push({ name: 'apiTokenNew' })
}

const deleteTokens = async () => {
    deleteTokenBtnLoading.value = true
    let response = await authSrv.deleteCurrentUserAPITokens(selectedTokens.value.map((t) => t.token))
    deleteTokenBtnLoading.value = false
    selectedTokens.value = []

    response.sendToast(toast)
    if (response.result) {
        userLoad()
    }
}

const handleDeleteTokens = () => {
    const names = selectedTokens.value.map((t) => t.name).join(', ')
    confirmDestructive({
        header: `Delete ${deleteTokenBtnLabel.value.replace('Delete ', '')}?`,
        message: `Scripts using ${names} will stop working at once. This cannot be undone.`,
        acceptLabel: 'Delete',
        accept: deleteTokens,
    })
}

const handleLogout = () => {
    window.location.href = '/logout'
}
</script>
