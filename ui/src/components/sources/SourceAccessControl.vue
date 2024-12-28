<template>
    <DataView :loading="loading" :error="error">
        <div class="w-full" v-if="source.isGrantable()">
            <Fieldset>
                <template #legend>
                    <span class="font-bold text-xl">Grant role </span>
                </template>
                <SelectButton v-model="grantType" :allowEmpty="false" :options="grantTypeOptions"
                    @change="onChangeGrantType" class="mb-5" />
                <div class="flex flex-row">
                    <div v-if="grantType == 'User'" class="w-full flex flex-row">
                        <FloatLabel variant="on" class="w-full mr-2">
                            <Select id="user_label" v-model="selectedUser" :loading="usersLoading" :options="users"
                                optionLabel="displayFull" size="small" class="w-full" filter showClear autoFilterFocus
                                :disabled="selectUserDisabled || usersLoading" @change="handleUserSelect" />
                            <label for="user_label">User</label>
                        </FloatLabel>
                    </div>
                    <div v-else class="w-full flex flex-row">
                        <FloatLabel variant="on" class="w-full mr-2">
                            <Select id="group_label" v-model="selectedGroup" :loading="groupsLoading" :options="groups"
                                optionLabel="name" size="small" class="w-full" filter showClear autoFilterFocus
                                :disabled="selectGroupDisabled || groupsLoading" @change="handleGroupSelect" />
                            <label for="group_label">Group</label>
                        </FloatLabel>
                    </div>
                    <FloatLabel variant="on" class="w-full">
                        <Select id="role" v-model="selectedRole" :options="roles" optionLabel="name" size="small"
                            class="w-full" showClear :disabled="selectRoleDisabled" />
                        <label for="role">Role</label>
                    </FloatLabel>
                    <Button class="ml-2 pl-6 pr-6 text-nowrap" severity="primary" label="Grant role"
                        :outlined="!grantButtonActive" @click="handleNewGrant" :disabled="!grantButtonActive"
                        :loading="grantButtonLoading" size="small" />
                        <br>
                </div>
                <div v-if="usersError" class="flex flex-row mt-2">
                    <Message severity="error">{{ usersError }}</Message>
                </div>
            </Fieldset>
            <div class="flex flex-row w-full mt-9 align-middle">
                <div class="flex items-center font-bold text-xl text-nowrap">Users bindings</div>
            </div>
        </div>
        <div class="flex flex-col mt-5">
            <DataTable v-if="userRoleBindings.length" :value="userRoleBindings" sortField="user" :sortOrder="1"
                removableSort class="w-full">
                <Column field="user" sortable header="USERNAME" headerStyle="width: 250px;">
                    <template #body="slotProps">
                        {{ slotProps.data.user.username }}
                    </template>
                </Column>
                <Column field="role" sortable header="ROLES">
                    <template #body="slotProps">
                        <div class="flex flex-wrap gap-2">
                            <Chip v-for="role in slotProps.data.roles" :key="role" :label="role" :removable="source.isGrantable()"
                                @remove="onUserRoleRevoke(slotProps.data.user, role)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
            <div v-else>There is no user bindings</div>
        </div>
        <div class="w-full">
            <div class="flex flex-row w-full mt-9 align-middle">
                <div class="flex items-center font-bold text-xl text-nowrap">Groups bindings</div>
            </div>
        </div>
        <div class="flex flex-row mt-5">
            <DataTable v-if="groupRoleBindings.length" :value="groupRoleBindings" sortField="group" :sortOrder="1"
                removableSort class="w-full">
                <Column field="group" sortable header="GROUP" headerStyle="width: 250px;">
                    <template #body="slotProps">
                        {{ slotProps.data.group.name }}
                    </template>
                </Column>
                <Column field="role" sortable header="ROLE">
                    <template #body="slotProps">
                        <div class="flex flex-wrap gap-2">
                            <Chip v-for="role in slotProps.data.roles" :key="role" :label="role" :removable="source.isGrantable()"
                                @remove="onGroupRoleRevoke(slotProps.data.group, role)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
            <div v-else>There is no group bindings</div>
        </div>
    </DataView>
</template>
<script setup>
import { ref, computed } from 'vue'

import { useToast } from 'primevue/usetoast'
import Chip from 'primevue/chip'
import Fieldset from 'primevue/fieldset'
import Select from 'primevue/select'
import DataTable from 'primevue/datatable'
import SelectButton from 'primevue/selectbutton'
import FloatLabel from 'primevue/floatlabel'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Message from 'primevue/message'

import DataView from '@/components/common/DataView.vue'
import { useGetSimpleGroups } from '@/composables/rbac/useGroupService'
import { useGetSimpleUsers } from '@/composables/rbac/useUserService'
import { useGetSourceRoleBidings } from '@/composables/sources/useSourceService'
import { SourceService } from '@/sdk/services/Source'

const props = defineProps(['source'])
const emit = defineEmits(['roleGranted', 'roleRevoked'])
const toast = useToast()
const sourceSrv = new SourceService()
const grantType = ref('User')
const grantTypeOptions = ref(['User', 'Group'])

const selectUserDisabled = ref(false)
const selectGroupDisabled = ref(false)
const selectRoleDisabled = ref(false)
const grantButtonLoading = ref(false)

const roles = ref([
    { 'name': 'owner' },
    { 'name': 'editor' },
    { 'name': 'viewer' },
    { 'name': 'user' },
    { 'name': 'sqluser' },
])

const selectedUser = ref(null)
const selectedGroup = ref(null)
const selectedRole = ref(null)

const { bindings, error, loading } = useGetSourceRoleBidings(props.source.slug)
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
            userToRoles[item.user.id] = { 'user': item.user, 'roles': [item.role] }
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
            groupToRoles[item.group.id] = { 'group': item.group, 'roles': [item.role] }
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
    let response = await sourceSrv.grantSourceRole(props.source.slug, selectedUser.value, selectedGroup.value, selectedRole.value)
    response.sendToast(toast)
    if (response.result && response.validation.result) {
        emit('roleGranted')
    }
}

const onUserRoleRevoke = (user, role) => {
    return sourceRevokeRole(props.source.slug, user, null, role)

}

const onGroupRoleRevoke = (group, role) => {
    return sourceRevokeRole(props.source.slug, null, group, role)
}

const sourceRevokeRole = async (slug, user, group, role) => {
    let response = await sourceSrv.revokeSourceRole(slug, user, group, role)
    response.sendToast(toast)
    if (response.result) {
        emit('roleRevoked')
    }
}
</script>