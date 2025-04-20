<template>
    <div class="flex flex-row justify-center mt-10">
        <DataView :loading="loading" :error="error">
            <div class="flex flex-col min-w-1000">
                <div class="mb-14">
                    <span class="font-bold text-3xl">Edit group: {{ group.name }}</span
                    ><br />
                </div>
                <div class="flex flex-row mb-5 items-start">
                    <div class="flex justify-start items-start" style="width: 190px">
                        <label class="text-lg font-bold mb-2">NAME</label>
                    </div>
                    <div class="flex justify-end w-full items-center">
                        <div class="flex flex-col w-full">
                            <InputText
                                id="name"
                                v-model="groupData.name"
                                fluid
                                :invalid="saveFieldErrors.name != ''"
                                @keyup.enter="handleSave"
                            />
                            <span v-if="saveFieldErrors.name != ''" class="text-rose-500">{{
                                saveFieldErrors.name
                            }}</span>
                        </div>
                    </div>
                </div>
                <div class="flex flex-row justify-end w-full">
                    <Button
                        class="ml-2 pl-6 pr-6"
                        severity="primary"
                        label="Save"
                        @click="handleSave"
                        :loading="saveButtonLoading"
                        size="small"
                    />
                </div>
            </div>
        </DataView>
    </div>
</template>

<script setup>
import { watch, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import DataView from '@/components/common/DataView.vue'
import { useNavStore } from '@/stores/nav'
import { useGetGroup } from '@/composables/rbac/useGroupService'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { GroupService } from '@/sdk/services/group'
import { useToast } from 'primevue/usetoast'

const navStore = useNavStore()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const saveButtonLoading = ref(false)

const navStored = ref(false)

const groupData = ref({
    name: '',
})
const saveFieldErrors = ref({
    name: '',
})
const saveNonFieldErrors = ref([])

const { group, error, loading } = useGetGroup(route.params.groupId)
const groupSrv = new GroupService()

navStore.update([{ label: 'Role-Based Access Control' }, { label: 'Groups', url: '/rbac/groups' }])

watch(group, () => {
    if (!navStored.value) {
        navStore.append({ label: group.value.name, url: `/rbac/groups/${group.value.id}` })
        navStore.append({ label: 'edit' })
        navStored.value = true
        groupData.value.name = group.value.name
    }
})

const handleSave = async () => {
    saveButtonLoading.value = true
    let response = await groupSrv.updateGroup(group.value.id, groupData.value.name)
    saveButtonLoading.value = false
    response.sendToast(toast)
    if (response.result) {
        if (!response.validation.result) {
            for (const field in response.validation.fields) {
                saveFieldErrors.value[field] = response.validation.fields[field].join(', ')
            }
        } else {
            router.push({ name: 'rbacGroup', params: { groupId: group.value.id } })
        }
    }
}
</script>
