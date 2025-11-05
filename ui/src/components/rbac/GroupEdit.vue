<template>
    <Content>
        <template #header>
            <Header>
                <template #title>
                    <i class="pi pi-user-plus mr-3 text-3xl"></i>
                    Groups / Edit
                </template>
            </Header>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <div class="max-w-7xl">
                    <Header>
                        <template #title>{{ group.name }} </template>
                    </Header>
                    <div class="border radius-lg p-6 dark:border-neutral-600 mt-4">
                        <div class="flex flex-col gap-6">
                            <div class="flex flex-col">
                                <FloatLabel variant="on">
                                    <InputText
                                        id="name"
                                        v-model="groupData.name"
                                        fluid
                                        :invalid="saveFieldErrors.name != ''"
                                        @keyup.enter="handleSave"
                                    />
                                    <label for="name">Name</label>
                                </FloatLabel>
                                <ErrorText :text="saveFieldErrors.name" />
                            </div>

                            <div class="flex justify-end gap-2">
                                <Button
                                    severity="secondary"
                                    label="Cancel"
                                    icon="pi pi-times"
                                    @click="router.push({ name: 'rbacGroup', params: { groupId: group.id } })"
                                    size="small"
                                />
                                <Button
                                    severity="primary"
                                    label="Save"
                                    icon="pi pi-check"
                                    @click="handleSave"
                                    :loading="saveButtonLoading"
                                    size="small"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
import { watch, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Content from '@/components/common/Content.vue'
import Header from '@/components/common/Header.vue'
import DataView from '@/components/common/DataView.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import { useGetGroup } from '@/composables/rbac/useGroupService'
import FloatLabel from 'primevue/floatlabel'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { GroupService } from '@/sdk/services/group'
import { useToast } from 'primevue/usetoast'

const toast = useToast()
const route = useRoute()
const router = useRouter()
const saveButtonLoading = ref(false)

const groupData = ref({
    name: '',
})
const saveFieldErrors = ref({
    name: '',
})

const { group, error, loading } = useGetGroup(route.params.groupId)
const groupSrv = new GroupService()

watch(group, (newGroup) => {
    if (newGroup) {
        groupData.value.name = newGroup.name
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
