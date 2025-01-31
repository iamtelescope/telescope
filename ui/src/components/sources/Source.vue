<template>
    <div class="flex flex-row justify-center mt-10">
        <div class="flex flex-col min-w-1280 max-w-1280">
            <DataView :loading="loading" :error="error">
                <div class="flex flex-row mb-9">
                    <div class="flex flex-col justify-start text-nowrap">
                        <span class="font-bold text-3xl">
                            <i class="pi pi-database text-3xl"></i>
                            <span class="text-gray-400"> Sources: </span>
                            {{ source.slug }}</span>
                        <span class="text-gray-400">Sources define where logs are accessed for reading and searching
                            within your system
                        </span>
                    </div>
                    <div class="flex flex-row w-full justify-end items-center">
                        <div>
                            <Button class="mr-1" severity="secondary" icon="pi pi-pencil" label="Edit" size="small"
                                @click="handleSourceEdit" v-if="source.isEditable()" />
                            <ConfirmPopup />
                            <Button severity="danger" icon="pi pi-trash" label="Delete"
                                @click="sourceDeleteConfirm($event)" :loading="sourceDeleteButtonLoading" size="small"
                                v-if="source.isEditable()" />
                        </div>
                    </div>
                </div>
                <Tabs v-model:value="activeTab">
                    <TabList>
                        <Tab value="overview">OVERVIEW</Tab>
                        <Tab value="accessControl" v-if="source.isEditable()">ACCESS CONTROL</Tab>
                    </TabList>
                    <TabPanels>
                        <TabPanel value="overview">
                            <DataRow name="KIND" :value="source.kind" />
                            <DataRow name="SLUG" :value="source.slug" />
                            <DataRow name="NAME" :value="source.name" />
                            <DataRow name="DESCRIPTION" :value="source.description" />
                            <DataRow name="TIME FIELD" :value="source.timeField" />
                            <!--<DataRow name="UNIQ FIELD" :value="source.uniqField" />-->
                            <DataRow name="SEVERITY FIELD" :value="source.severityField" />
                            <DataRow name="DEFAULT CHOSEN FEILDS" :showBorder="false">
                                {{ source.defaultChosenFields.join(', ') }}
                            </DataRow>
                            <Fieldset class="text-wrap mt-5">
                                <template #legend>
                                    <span class="font-bold">Fields</span>
                                </template>
                                <DataTable :value="sourceFields">
                                    <Column field="name" sortable header="NAME" />
                                    <Column sortable header="DISPLAY NAME">
                                        <template #body="slotProps">
                                            <span v-if="slotProps.data.display_name">{{ slotProps.data.display_name
                                                }}</span>
                                            <span v-else>&ndash;</span>
                                        </template>
                                    </Column>
                                    <Column field="type" sortable header="TYPE" />
                                    <Column sortable header="AUTOCOMPLETE">
                                        <template #body="slotProps">
                                            <ToggleSwitch v-model="slotProps.data.autocomplete" readonly />
                                        </template>
                                    </Column>
                                    <Column sortable header="SUGGEST">
                                        <template #body="slotProps">
                                            <ToggleSwitch v-model="slotProps.data.suggest" readonly />
                                        </template>
                                    </Column>
                                    <Column sortable header="VALUES">
                                        <template #body="slotProps">
                                            <span v-if="slotProps.data.values.length">{{
                                                slotProps.data.values.join(', ') }}</span>
                                            <span v-else>&ndash;</span>
                                        </template>
                                    </Column>
                                </DataTable>
                            </Fieldset>
                        </TabPanel>
                        <TabPanel value="accessControl" v-if="source.isEditable()">
                            <SourceAccessControl :source="source" @roleGranted="onRoleGranted"
                                @roleRevoked="onRoleRevoked" />
                        </TabPanel>
                    </TabPanels>
                </Tabs>
            </DataView>
        </div>
    </div>
</template>
<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useConfirm } from 'primevue'
import { useToast } from 'primevue/usetoast'
import ToggleSwitch from 'primevue/toggleswitch'
import ConfirmPopup from 'primevue/confirmpopup'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import Fieldset from 'primevue/fieldset'

import { useNavStore } from '@/stores/nav'
import DataRow from '@/components/common/DataRow.vue'
import DataView from '@/components/common/DataView.vue'
import SourceAccessControl from '@/components/sources/SourceAccessControl.vue'

import { SourceService } from '@/sdk/services/Source'
import { useGetSource } from '@/composables/sources/useSourceService'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()

const navStore = useNavStore()
const sourceSrv = new SourceService()
const activeTab = ref('overview')
const sourceDeleteButtonLoading = ref(false)

navStore.updatev2([
    { label: 'Sources', url: '/sources', icon: 'pi pi-database' },
])

const { source, error, loading, load } = useGetSource(route.params.sourceSlug)

if (route.query.tab) {
    activeTab.value = route.query.tab
}

const sourceFields = computed(() => {
    const result = []
    for (const [key, value] of Object.entries(source.value.fields)) {
        let item = Object.assign({ 'name': key }, value)
        result.push(item)
    }
    return result
})

const handleSourceEdit = () => {
    router.push({ name: 'sourceEdit', params: { sourceSlug: source.value.slug } })
}

const sourceDeleteConfirm = (event) => {
    confirm.require({
        target: event.currentTarget,
        message: 'Are you sure?',
        icon: 'pi pi-info-circle',
        rejectProps: {
            label: 'Cancel',
            severity: 'secondary',
            outlined: true
        },
        acceptProps: {
            label: 'Yes, delete',
            severity: 'danger'
        },
        accept: async () => {
            sourceDeleteButtonLoading.value = true
            let response = await sourceSrv.deleteSource(source.value.slug)
            sourceDeleteButtonLoading.value = false
            response.sendToastErrors(toast)
            if (response.result) {
                router.push({ 'name': 'root' }).then(() => response.sendToastMessages(toast))
            }
        },
    });
}
const onRoleGranted = () => {
    load()
}

const onRoleRevoked = () => {
    load()
}

watch(activeTab, () => {
    const url = new URL(window.location)
    url.searchParams.set("tab", activeTab.value)
    history.pushState(null, '', url);
})

</script>
