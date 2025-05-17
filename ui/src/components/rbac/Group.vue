<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280">
            <DataView :loadings="[groupLoading]" :errors="[groupError]">
                <div class="flex flex-row mb-14">
                    <div class="flex flex-col justify-start text-nowrap">
                        <span class="font-medium text-3xl">
                            <i class="pi pi-users text-3xl mr-1"></i>
                            <span class="text-gray-400">Groups: </span>
                            {{ group.name }}</span
                        >
                        <span class="text-gray-400">{{ group.userCount }} members</span>
                    </div>
                    <div class="flex flex-row w-full justify-end items-center">
                        <div>
                            <Button
                                class="mr-1"
                                severity="secondary"
                                label="Edit"
                                @click="handleGroupEdit"
                                size="small"
                            />
                            <ConfirmPopup></ConfirmPopup>
                            <Button
                                severity="danger"
                                label="Delete"
                                @click="groupDeleteConfirm($event)"
                                :loading="deleteButtonLoading"
                                size="small"
                            />
                        </div>
                    </div>
                </div>
                <div class="w-full">
                    <DataRow name="ID" :value="group.id" />
                    <DataRow name="NAME" :value="group.name" />
                    <DataRow name="ROLE BINDINGS (GLOBAL)" :showBorder="false">
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
                    <br />
                    <Fieldset>
                        <template #legend>
                            <span class="font-medium text-xl">Grant role (global)</span>
                        </template>
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
                    </Fieldset>
                    <Fieldset>
                        <template #legend>
                            <span class="font-medium text-xl">Add group members</span>
                        </template>
                        <div class="flex flex-row">
                            <Select
                                v-model="selectedUser"
                                :loading="usersLoading"
                                :options="addableUsers"
                                optionLabel="displayFull"
                                size="small"
                                placeholder="&#8211;"
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
                    </Fieldset>
                </div>
                <div class="w-full">
                    <div class="flex flex-row w-full mt-9 align-middle">
                        <div class="flex items-center font-medium text-xl text-nowrap">Group members</div>
                        <div class="flex items-center w-full justify-end">
                            <Button
                                severity="danger"
                                :label="removeBtnLabel"
                                @click="handleRemoveUsers"
                                :disabled="selectedUsers.length == 0"
                                :outlined="selectedUsers.length == 0"
                                :loading="removeButtonLoading"
                            />
                        </div>
                    </div>
                </div>
                <div class="flex flex-row mt-5">
                    <DataTable
                        v-if="group.users.length"
                        v-model:selection="selectedUsers"
                        sortField="username"
                        :sortOrder="1"
                        removableSort
                        dataKey="id"
                        :value="group.users"
                        class="w-full"
                    >
                        <Column selectionMode="multiple" headerStyle="width: 3rem"></Column>
                        <Column field="username" sortable header="USERNAME" class="font-medium"></Column>
                        <Column field="displayFirstName" sortable header="FIRST NAME"></Column>
                        <Column field="displayLastName" sortable header="LAST NAME"></Column>
                    </DataTable>
                    <div v-else>Group is empty</div>
                </div>
            </DataView>
        </div>
    </div>
</template>

<script setup>
import { watch, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue'
import Chip from 'primevue/chip'
import ConfirmPopup from 'primevue/confirmpopup'
import Fieldset from 'primevue/fieldset'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Message from 'primevue/message'

import { useNavStore } from '@/stores/nav'
import DataRow from '@/components/common/DataRow.vue'
import DataView from '@/components/common/DataView.vue'
import { useGetGroup } from '@/composables/rbac/useGroupService'
import { useGetUsers } from '@/composables/rbac/useUserService'
import { GroupService } from '@/sdk/services/group'

const router = useRouter()
const toast = useToast()
const navStore = useNavStore()
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
const navStored = ref(false)
const globalRoles = [{ name: 'admin' }]
const selectedGlobalRole = ref(null)
const selectGlobalRoleDisabled = ref(false)

const groupSrv = new GroupService()

navStore.update([
    { label: 'Role-Based Access Control', url: '/rbac' },
    { label: 'Groups', url: '/rbac/groups' },
])

const { users, error: usersError, loading: usersLoading } = useGetUsers()
const { group, error: groupError, loading: groupLoading, load: groupLoad } = useGetGroup(route.params.groupId)

watch(group, () => {
    if (!navStored.value) {
        navStore.append({ label: group.value.name, url: `/rbac/groups/${group.value.id}` })
        navStored.value = true
    }
})

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
            response.sendToast(toast)
            if (response.result) {
                router.push({ name: 'rbacGroups' })
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
