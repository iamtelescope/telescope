<template>
    <Content>
        <template #header>
            <Header>
                <template #title> <Users class="mr-3 w-8 h-8" /> Group </template>
            </Header>
        </template>
        <template #content>
            <DataView :loadings="[groupLoading]" :errors="[groupError]">
                <div class="flex flex-col max-w-[800px]">
                    <Header>
                        <template #title>{{ group.name }} </template>
                        <template #actions>
                            <div class="flex flex-wrap gap-2">
                                <Button
                                    severity="primary"
                                    label="Edit"
                                    icon="pi pi-pencil"
                                    @click="handleGroupEdit"
                                    size="small"
                                    :disabled="groupLoading"
                                />
                                <ConfirmPopup></ConfirmPopup>
                                <Button
                                    severity="primary"
                                    label="Delete"
                                    icon="pi pi-trash"
                                    @click="groupDeleteConfirm($event)"
                                    :loading="deleteButtonLoading"
                                    size="small"
                                    :disabled="groupLoading"
                                />
                            </div>
                        </template>
                    </Header>
                    <div class="mt-4">
                        <ContentBlock header="Common">
                            <DataRow name="Id" :value="group.id" :copy="false" />
                            <DataRow name="Name" :value="group.name" :copy="false" />
                            <DataRow name="Role bindings (global)" :showBorder="false" :copy="false">
                                <div class="flex flex-wrap gap-2" v-if="group.roles.length > 0">
                                    <Chip
                                        v-for="role in group.roles"
                                        :key="role"
                                        :label="role"
                                        removable
                                        @remove="handleRevokeGlobalRole(role)"
                                    />
                                </div>
                                <div v-else class="text-gray-400">&ndash;</div>
                            </DataRow>
                        </ContentBlock>

                        <ContentBlock header="Grant role (global)" class="mt-3">
                            <div class="p-4">
                                <div class="flex flex-row">
                                    <Select
                                        v-model="selectedGlobalRole"
                                        :options="addableRoles"
                                        optionLabel="name"
                                        size="small"
                                        placeholder="&#8211;"
                                        class="w-full"
                                        filter
                                        showClear
                                        autoFilterFocus
                                        @change="handleGlobalRoleSelect"
                                        :disabled="selectGlobalRoleDisabled"
                                    />
                                    <Button
                                        class="ml-2 pl-6 pr-6"
                                        severity="primary"
                                        label="Grant"
                                        :outlined="!grantButtonActive"
                                        @click="handleGrantGlobalRole"
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

                        <ContentBlock header="Group members" class="mt-3">
                            <template #actions>
                                <Button
                                    severity="danger"
                                    :label="removeBtnLabel"
                                    @click="handleRemoveUsers"
                                    :disabled="selectedUsers.length == 0"
                                    :outlined="selectedUsers.length == 0"
                                    :loading="removeButtonLoading"
                                    size="small"
                                    class="max-h-[25px]"
                                />
                            </template>
                            <div class="p-4 border-b dark:border-neutral-600">
                                <div class="flex flex-row">
                                    <Select
                                        v-model="selectedUser"
                                        :loading="usersLoading"
                                        :options="addableUsers"
                                        optionLabel="displayFull"
                                        size="small"
                                        placeholder="Select user to add..."
                                        class="w-full"
                                        filter
                                        showClear
                                        autoFilterFocus
                                        :disabled="selectUserDisabled || usersLoading"
                                        @change="handleUserSelect"
                                    />
                                    <Button
                                        class="ml-2 pl-6 pr-6"
                                        severity="primary"
                                        label="Add"
                                        :outlined="!addButtonActive"
                                        @click="handleAddUser"
                                        :disabled="!addButtonActive"
                                        :loading="addButtonLoading"
                                        size="small"
                                    />
                                </div>
                                <div v-if="usersError" class="flex flex-row mt-2">
                                    <Message severity="error">{{ usersError }}</Message>
                                </div>
                            </div>
                            <DataTable
                                v-if="group.users.length"
                                v-model:selection="selectedUsers"
                                sortField="username"
                                :sortOrder="1"
                                removableSort
                                dataKey="id"
                                :value="group.users"
                                :paginator="group.users.length > 50"
                                :rows="50"
                                :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                                :row-hover="true"
                                size="small"
                                class="w-full"
                            >
                                <Column selectionMode="multiple" headerStyle="width: 3rem" />
                                <Column field="username" header="Username" class="font-medium" :sortable="true" />
                                <Column field="displayFirstName" header="First Name" :sortable="true" />
                                <Column field="displayLastName" header="Last Name" :sortable="true" />
                            </DataTable>
                            <div
                                v-else
                                class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400"
                            >
                                <Users class="w-10 h-10 mb-4 opacity-50" />
                                <p class="text-lg font-medium mb-2">No users in this group</p>
                                <p class="text-sm">Add users to this group using the form above</p>
                            </div>
                        </ContentBlock>
                    </div>
                </div>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
import { watch, ref, computed } from 'vue'
import { Users } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'

import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue'
import Chip from 'primevue/chip'
import ConfirmPopup from 'primevue/confirmpopup'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Message from 'primevue/message'

import Content from '@/components/common/Content.vue'
import DataRow from '@/components/common/DataRow.vue'
import DataView from '@/components/common/DataView.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import { useGetGroup } from '@/composables/rbac/useGroupService'
import { useGetUsers } from '@/composables/rbac/useUserService'
import { GroupService } from '@/sdk/services/group'
import Header from '@/components/common/Header.vue'

const router = useRouter()
const toast = useToast()
const route = useRoute()
const selectedUser = ref(null)
const selectUserDisabled = ref(false)
const selectedUsers = ref([])
const addButtonActive = ref(false)
const addButtonLoading = ref(false)
const deleteButtonLoading = ref(false)
const removeButtonLoading = ref(false)
const grantButtonActive = ref(false)
const grantButtonLoading = ref(false)
const confirm = useConfirm()
const globalRoles = [{ name: 'admin' }, { name: 'connection_manager' }, { name: 'source_manager' }]
const selectedGlobalRole = ref(null)
const selectGlobalRoleDisabled = ref(false)

const groupSrv = new GroupService()

const { users, error: usersError, loading: usersLoading } = useGetUsers()
const { group, error: groupError, loading: groupLoading, load: groupLoad } = useGetGroup(route.params.groupId)

const addableUsers = computed(() => {
    if (users.value != null) {
        let groupUsers = group.value.users.map((u) => u.id)
        return users.value.filter((u) => !groupUsers.includes(u.id))
    }
})

const addableRoles = computed(() => {
    if (group.value != null) {
        return globalRoles.filter((r) => !group.value.roles.includes(r.name))
    }
})

const removeBtnLabel = computed(() => {
    let text = 'Remove'
    let size = selectedUsers.value.length
    let str_size = ''
    if (size > 0) {
        str_size = `${size} `
    }
    text += ' ' + str_size + 'user'
    if (size == 0 || size > 1) {
        text += 's'
    }
    return text
})

const handleUserSelect = () => {
    if (selectedUser.value) {
        addButtonActive.value = true
    } else {
        addButtonActive.value = false
    }
}

const handleGlobalRoleSelect = () => {
    if (selectedGlobalRole.value) {
        grantButtonActive.value = true
    } else {
        grantButtonActive.value = false
    }
}

const handleGroupEdit = () => {
    router.push({ name: 'rbacGroupEdit' })
}

const handleGrantGlobalRole = async () => {
    grantButtonLoading.value = true
    selectGlobalRoleDisabled.value = true
    grantButtonActive.value = false

    let response = await groupSrv.grantRole(group.value.id, selectedGlobalRole.value.name)
    grantButtonLoading.value = false
    selectGlobalRoleDisabled.value = false
    response.sendToast(toast)
    if (response.result) {
        groupLoad()
    }
}

const handleRevokeGlobalRole = async (roleName) => {
    grantButtonLoading.value = true
    selectGlobalRoleDisabled.value = true
    grantButtonActive.value = false

    let response = await groupSrv.revokeRole(group.value.id, roleName)
    grantButtonLoading.value = false
    selectGlobalRoleDisabled.value = false
    response.sendToast(toast)
    if (response.result) {
        groupLoad()
    }
}

const groupDeleteConfirm = (event) => {
    confirm.require({
        target: event.currentTarget,
        message: 'Are you sure?',
        icon: 'pi pi-info-circle',
        rejectProps: {
            label: 'Cancel',
            severity: 'secondary',
            outlined: true,
        },
        acceptProps: {
            label: 'Yes, delete',
            severity: 'danger',
        },
        accept: async () => {
            deleteButtonLoading.value = true
            let response = await groupSrv.deleteGroup(group.value.id)
            deleteButtonLoading.value = false
            response.sendToastErrors(toast)
            if (response.result) {
                router.push({ name: 'rbacGroups' }).then(() => response.sendToastMessages(toast))
            }
        },
    })
}

const handleAddUser = async () => {
    addButtonLoading.value = true
    selectUserDisabled.value = true
    addButtonActive.value = false

    let response = await groupSrv.addUsers(group.value.id, [selectedUser.value.id])
    addButtonLoading.value = false
    selectUserDisabled.value = false
    response.sendToast(toast)
    if (response.result) {
        groupLoad()
    }
}

const handleRemoveUsers = async () => {
    removeButtonLoading.value = true

    let response = await groupSrv.removeUsers(
        group.value.id,
        selectedUsers.value.map((u) => u.id),
    )
    removeButtonLoading.value = false
    selectedUsers.value = []

    response.sendToast(toast)
    if (response.result) {
        groupLoad()
    }
}
</script>
