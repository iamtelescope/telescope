<template>
    <DataView :loadings="[loading]" :errors="[error]">
        <AccessDenied
            v-if="!connection?.canGrant()"
            message="You don't have permission to manage access control for this connection."
        />
        <ContentBlock v-else header="Grant role">
            <div class="p-4">
                <SelectButton
                    v-model="grantType"
                    :allowEmpty="false"
                    :options="grantTypeOptions"
                    @change="onChangeGrantType"
                    class="mb-5"
                />
                <div class="flex flex-row">
                    <div v-if="grantType == 'User'" class="w-full flex flex-row">
                        <FloatLabel variant="on" class="w-full mr-2">
                            <Select
                                id="user_label"
                                v-model="selectedUser"
                                :loading="usersLoading"
                                :options="users"
                                optionLabel="displayFull"
                                size="small"
                                class="w-full"
                                filter
                                showClear
                                autoFilterFocus
                                :disabled="selectUserDisabled || usersLoading"
                                @change="handleUserSelect"
                            />
                            <label for="user_label">User</label>
                        </FloatLabel>
                    </div>
                    <div v-else class="w-full flex flex-row">
                        <FloatLabel variant="on" class="w-full mr-2">
                            <Select
                                id="group_label"
                                v-model="selectedGroup"
                                :loading="groupsLoading"
                                :options="groups"
                                optionLabel="name"
                                size="small"
                                class="w-full"
                                filter
                                showClear
                                autoFilterFocus
                                :disabled="selectGroupDisabled || groupsLoading"
                                @change="handleGroupSelect"
                            />
                            <label for="group_label">Group</label>
                        </FloatLabel>
                    </div>
                    <FloatLabel variant="on" class="w-full">
                        <Select
                            id="role"
                            v-model="selectedRole"
                            :options="roles"
                            optionLabel="name"
                            size="small"
                            class="w-full"
                            showClear
                            :disabled="selectRoleDisabled"
                        />
                        <label for="role">Role</label>
                    </FloatLabel>
                    <Button
                        class="ml-2 pl-6 pr-6 text-nowrap"
                        severity="primary"
                        label="Grant role"
                        :outlined="!grantButtonActive"
                        @click="handleNewGrant"
                        :disabled="!grantButtonActive"
                        :loading="grantButtonLoading"
                        size="small"
                    />
                </div>
                <div v-if="usersError" class="flex flex-row mt-2">
                    <Message severity="error">{{ usersError }}</Message>
                </div>
            </div>
        </ContentBlock>

        <ContentBlock header="User bindings" class="mt-3">
            <DataTable
                v-if="userRoleBindings.length"
                :value="userRoleBindings"
                sortField="user"
                :sortOrder="1"
                removableSort
                :paginator="userRoleBindings.length > 50"
                :rows="50"
                :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                class="w-full"
            >
                <Column field="user" sortable header="Username" headerStyle="width: 250px;">
                    <template #body="slotProps">
                        {{ slotProps.data.user.username }}
                    </template>
                </Column>
                <Column field="roles" header="Roles">
                    <template #body="slotProps">
                        <div class="flex flex-wrap gap-2">
                            <Chip
                                v-for="role in slotProps.data.roles"
                                :key="role"
                                :label="role"
                                :removable="true"
                                @remove="onUserRoleRevoke(slotProps.data.user, role)"
                            />
                        </div>
                    </template>
                </Column>
                <template #empty>
                    <div class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
                        <i class="pi pi-users text-4xl mb-4 opacity-50"></i>
                        <p class="text-lg font-medium mb-2">No user bindings</p>
                    </div>
                </template>
            </DataTable>
            <div v-else class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
                <i class="pi pi-user text-4xl mb-4 opacity-50"></i>
                <p class="text-lg font-medium mb-2">No user bindings</p>
                <p class="text-sm">Grant roles to users using the form above</p>
            </div>
        </ContentBlock>

        <ContentBlock header="Group bindings" class="mt-3">
            <DataTable
                v-if="groupRoleBindings.length"
                :value="groupRoleBindings"
                sortField="group"
                :sortOrder="1"
                removableSort
                :paginator="groupRoleBindings.length > 50"
                :rows="50"
                :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                class="w-full"
            >
                <Column field="group" sortable header="Group" headerStyle="width: 250px;">
                    <template #body="slotProps">
                        {{ slotProps.data.group.name }}
                    </template>
                </Column>
                <Column field="roles" header="Roles">
                    <template #body="slotProps">
                        <div class="flex flex-wrap gap-2">
                            <Chip
                                v-for="role in slotProps.data.roles"
                                :key="role"
                                :label="role"
                                :removable="true"
                                @remove="onGroupRoleRevoke(slotProps.data.group, role)"
                            />
                        </div>
                    </template>
                </Column>
                <template #empty>
                    <div class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
                        <i class="pi pi-users text-4xl mb-4 opacity-50"></i>
                        <p class="text-lg font-medium mb-2">No group bindings</p>
                    </div>
                </template>
            </DataTable>
            <div v-else class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
                <i class="pi pi-users text-4xl mb-4 opacity-50"></i>
                <p class="text-lg font-medium mb-2">No group bindings</p>
                <p class="text-sm">Grant roles to groups using the form above</p>
            </div>
        </ContentBlock>
    </DataView>
</template>
<script setup>
import { ref, computed } from 'vue'

import { useToast } from 'primevue/usetoast'
import Chip from 'primevue/chip'
import Select from 'primevue/select'
import DataTable from 'primevue/datatable'
import SelectButton from 'primevue/selectbutton'
import FloatLabel from 'primevue/floatlabel'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Message from 'primevue/message'

import DataView from '@/components/common/DataView.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import AccessDenied from '@/components/common/AccessDenied.vue'
import { useGetSimpleGroups } from '@/composables/rbac/useGroupService'
import { useGetSimpleUsers } from '@/composables/rbac/useUserService'
import { useGetConnectionRoleBindings } from '@/composables/connections/useConnectionService'
import { ConnectionService } from '@/sdk/services/connection'

const props = defineProps(['connection'])
const emit = defineEmits(['roleGranted', 'roleRevoked'])
const toast = useToast()
const connectionSrv = new ConnectionService()
const grantType = ref('User')
const grantTypeOptions = ref(['User', 'Group'])

const selectUserDisabled = ref(false)
const selectGroupDisabled = ref(false)
const selectRoleDisabled = ref(false)
const grantButtonLoading = ref(false)

const roles = ref([{ name: 'owner' }, { name: 'editor' }, { name: 'viewer' }, { name: 'user' }])

const selectedUser = ref(null)
const selectedGroup = ref(null)
const selectedRole = ref(null)

const { bindings, error, loading } = useGetConnectionRoleBindings(props.connection.id)
const { users, error: usersError, loading: usersLoading } = useGetSimpleUsers()
const { groups, error: groupsError, loading: groupsLoading } = useGetSimpleGroups()

const grantButtonActive = computed(() => {
    if ((selectedUser.value || selectedGroup.value) && selectedRole.value) {
        return true
    }
    return false
})

const userRoleBindings = computed(() => {
    let userToRoles = {}
    for (const item of bindings.value.filter((item) => item.user !== null)) {
        if (!(item.user.id in userToRoles)) {
            userToRoles[item.user.id] = { user: item.user, roles: [item.role] }
        } else {
            userToRoles[item.user.id]['roles'].push(item.role)
        }
    }
    let result = []
    for (const [_, value] of Object.entries(userToRoles)) {
        result.push(value)
    }
    return result
})

const groupRoleBindings = computed(() => {
    let groupToRoles = {}
    for (const item of bindings.value.filter((item) => item.group !== null)) {
        if (!(item.group.id in groupToRoles)) {
            groupToRoles[item.group.id] = { group: item.group, roles: [item.role] }
        } else {
            groupToRoles[item.group.id]['roles'].push(item.role)
        }
    }
    let result = []
    for (const [_, value] of Object.entries(groupToRoles)) {
        result.push(value)
    }
    return result
})

const handleUserSelect = () => {
    selectedGroup.value = null
}
const handleGroupSelect = () => {
    selectedUser.value = null
}
const onChangeGrantType = () => {
    selectedGroup.value = null
    selectedUser.value = null
}

const handleNewGrant = async () => {
    let response = await connectionSrv.grantConnectionRole(
        props.connection.id,
        selectedUser.value,
        selectedGroup.value,
        selectedRole.value,
    )
    response.sendToast(toast)
    if (response.result && response.validation.result) {
        emit('roleGranted')
    }
}

const onUserRoleRevoke = (user, role) => {
    return connectionRevokeRole(props.connection.id, user, null, role)
}

const onGroupRoleRevoke = (group, role) => {
    return connectionRevokeRole(props.connection.id, null, group, role)
}

const connectionRevokeRole = async (pk, user, group, role) => {
    let response = await connectionSrv.revokeConnectionRole(pk, user, group, role)
    response.sendToast(toast)
    if (response.result) {
        emit('roleRevoked')
    }
}
</script>
