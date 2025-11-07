<template>
    <Content>
        <template #header>
            <Header>
                <template #title> <Database class="mr-3 w-8 h-8" /> Source </template>
            </Header>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <div class="flex flex-col max-w-[1280px]">
                    <Header>
                        <template #title>
                            <div class="flex items-center gap-3">
                                <img
                                    v-if="source.kind"
                                    :src="require(`@/assets/${source.kind}.png`)"
                                    height="32px"
                                    width="32px"
                                    :title="source.kind"
                                />
                                <span>{{ source.slug }}</span>
                            </div>
                        </template>
                        <template #actions>
                            <div class="flex flex-wrap gap-2" v-if="source.isEditable()">
                                <Button
                                    severity="primary"
                                    label="Edit"
                                    icon="pi pi-pencil"
                                    @click="handleSourceEdit"
                                    size="small"
                                    :disabled="loading"
                                />
                                <ConfirmPopup></ConfirmPopup>
                                <Button
                                    severity="primary"
                                    label="Delete"
                                    icon="pi pi-trash"
                                    @click="sourceDeleteConfirm($event)"
                                    :loading="sourceDeleteButtonLoading"
                                    size="small"
                                    :disabled="loading"
                                />
                            </div>
                        </template>
                    </Header>
                    <div class="mt-4">
                        <Tabs v-model:value="activeTab">
                            <TabList>
                                <Tab value="overview">OVERVIEW</Tab>
                                <Tab value="accessControl" v-if="source.isEditable()">ACCESS CONTROL</Tab>
                            </TabList>
                            <TabPanels class="pl-0 pr-0">
                                <TabPanel value="overview">
                                    <ContentBlock header="Common">
                                        <DataRow name="Connection" :copy="false">
                                            <div class="flex items-center gap-2">
                                                <img
                                                    :src="require(`@/assets/${connectionDisplay.kind}.png`)"
                                                    height="20px"
                                                    width="20px"
                                                    :title="connectionDisplay.kind"
                                                />
                                                <router-link
                                                    v-if="connectionDisplay.hasAccess"
                                                    :to="{
                                                        name: 'connection',
                                                        params: { connectionId: connectionDisplay.id },
                                                    }"
                                                    class="table-link"
                                                >
                                                    {{ connectionDisplay.name }}
                                                </router-link>
                                                <span v-else>Connection {{ connectionDisplay.id }}</span>
                                            </div>
                                        </DataRow>
                                        <DataRow name="Kind" :value="source.kind" :copy="false" />
                                        <DataRow name="Slug" :value="source.slug" :copy="false" />
                                        <DataRow name="Name" :value="source.name" :copy="false" />
                                        <DataRow
                                            name="Description"
                                            :value="source.description || '&ndash;'"
                                            :copy="false"
                                        />
                                        <DataRow name="Time field" :value="source.timeField" :copy="false" />
                                        <DataRow
                                            name="Date field"
                                            :value="source.dateField || '&ndash;'"
                                            :copy="false"
                                        />
                                        <DataRow
                                            name="Severity field"
                                            :value="source.severityField || '&ndash;'"
                                            :copy="false"
                                        />
                                        <DataRow name="Default chosen fields" :showBorder="false" :copy="false">
                                            {{ source.defaultChosenFields?.join(', ') || '&ndash;' }}
                                        </DataRow>
                                    </ContentBlock>

                                    <ContentBlock header="Data" class="mt-3" v-if="source.kind === 'clickhouse'">
                                        <DataRow name="Database" :copy="false">
                                            <span class="font-mono">{{ source.data?.database || '&ndash;' }}</span>
                                        </DataRow>
                                        <DataRow name="Table" :copy="false">
                                            <span class="font-mono">{{ source.data?.table || '&ndash;' }}</span>
                                        </DataRow>
                                        <DataRow name="Query Settings" :copy="false" :showBorder="false">
                                            <span class="font-mono text-sm">{{ source.data?.settings || '&ndash;' }}</span>
                                        </DataRow>
                                    </ContentBlock>

                                    <ContentBlock header="Fields" class="mt-3">
                                        <DataTable
                                            :value="sourceFields"
                                            v-if="sourceFields.length"
                                            :paginator="sourceFields.length > 50"
                                            :rows="50"
                                            :rowsPerPageOptions="[10, 25, 50, 100, 1000]"
                                            class="w-full"
                                        >
                                            <Column
                                                :sortable="true"
                                                field="name"
                                                header="Name"
                                                headerClass="text-nowrap"
                                            />
                                            <Column :sortable="true" header="Display Name" headerClass="text-nowrap">
                                                <template #body="slotProps">
                                                    <span v-if="slotProps.data.display_name">{{
                                                        slotProps.data.display_name
                                                    }}</span>
                                                    <span v-else>&ndash;</span>
                                                </template>
                                            </Column>
                                            <Column
                                                field="type"
                                                :sortable="true"
                                                header="Type"
                                                headerClass="text-nowrap"
                                            />
                                            <Column
                                                :sortable="true"
                                                header="Autocomplete"
                                                headerClass="text-nowrap"
                                                sortField="autocomplete"
                                            >
                                                <template #body="slotProps">
                                                    <ToggleSwitch v-model="slotProps.data.autocomplete" readonly />
                                                </template>
                                            </Column>
                                            <Column
                                                :sortable="true"
                                                header="Suggest"
                                                headerClass="text-nowrap"
                                                sortField="suggest"
                                            >
                                                <template #body="slotProps">
                                                    <ToggleSwitch v-model="slotProps.data.suggest" readonly />
                                                </template>
                                            </Column>
                                            <Column
                                                :sortable="true"
                                                header="JSON String"
                                                headerClass="text-nowrap"
                                                sortField="jsonstring"
                                            >
                                                <template #body="slotProps">
                                                    <ToggleSwitch v-model="slotProps.data.jsonstring" readonly />
                                                </template>
                                            </Column>
                                            <Column
                                                :sortable="true"
                                                header="Group By"
                                                headerClass="text-nowrap"
                                                sortField="group_by"
                                            >
                                                <template #body="slotProps">
                                                    <ToggleSwitch v-model="slotProps.data.group_by" readonly />
                                                </template>
                                            </Column>
                                            <Column
                                                :sortable="true"
                                                header="Values"
                                                headerClass="text-nowrap"
                                                sortField="values"
                                            >
                                                <template #body="slotProps">
                                                    <span v-if="slotProps.data.values.length">{{
                                                        slotProps.data.values.join(', ')
                                                    }}</span>
                                                    <span v-else>&ndash;</span>
                                                </template>
                                            </Column>
                                            <template #empty>
                                                <div
                                                    class="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400"
                                                >
                                                    <i class="pi pi-list text-4xl mb-4 opacity-50"></i>
                                                    <p class="text-lg font-medium mb-2">No fields found</p>
                                                </div>
                                            </template>
                                        </DataTable>
                                    </ContentBlock>
                                </TabPanel>
                                <TabPanel value="accessControl" v-if="source.isEditable()">
                                    <SourceAccessControl
                                        :source="source"
                                        @roleGranted="onRoleGranted"
                                        @roleRevoked="onRoleRevoked"
                                    />
                                </TabPanel>
                            </TabPanels>
                        </Tabs>
                    </div>
                </div>
            </DataView>
        </template>
    </Content>
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

import { Database } from 'lucide-vue-next'

import Content from '@/components/common/Content.vue'
import DataView from '@/components/common/DataView.vue'
import DataRow from '@/components/common/DataRow.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import Header from '@/components/common/Header.vue'
import SourceAccessControl from '@/components/sources/SourceAccessControl.vue'

import { SourceService } from '@/sdk/services/source'
import { useGetSource } from '@/composables/sources/useSourceService'
import { useGetUsableConnections } from '@/composables/connections/useConnectionService'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()

const sourceSrv = new SourceService()
const activeTab = ref('overview')
const sourceDeleteButtonLoading = ref(false)

const { source, error, loading, load } = useGetSource(route.params.sourceSlug)
const { connections } = useGetUsableConnections()

if (route.query.tab) {
    activeTab.value = route.query.tab
}

const sourceFields = computed(() => {
    const result = []
    for (const [key, value] of Object.entries(source.value.fields)) {
        let item = Object.assign({ name: key }, value)
        result.push(item)
    }
    return result
})

// Find the connection in usable connections
const sourceConnection = computed(() => {
    if (!source.value.connectionId || !connections.value) {
        return null
    }
    return connections.value.find((c) => c.id === source.value.connectionId)
})

// Check if user has access to the connection
const hasConnectionAccess = computed(() => !!sourceConnection.value)

const connectionDisplay = computed(() => {
    if (sourceConnection.value) {
        return {
            name: sourceConnection.value.name,
            kind: sourceConnection.value.kind,
            id: sourceConnection.value.id,
            hasAccess: true,
        }
    }
    // No access - just show ID
    return {
        name: null,
        kind: source.value.kind, // Use source kind as fallback
        id: source.value.connectionId,
        hasAccess: false,
    }
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
            outlined: true,
        },
        acceptProps: {
            label: 'Yes, delete',
            severity: 'danger',
        },
        accept: async () => {
            sourceDeleteButtonLoading.value = true
            let response = await sourceSrv.deleteSource(source.value.slug)
            sourceDeleteButtonLoading.value = false
            response.sendToastErrors(toast)
            if (response.result) {
                router.push({ name: 'sources' }).then(() => response.sendToastMessages(toast))
            }
        },
    })
}
const onRoleGranted = () => {
    load()
}

const onRoleRevoked = () => {
    load()
}

watch(activeTab, () => {
    const url = new URL(window.location)
    url.searchParams.set('tab', activeTab.value)
    history.pushState(null, '', url)
})
</script>
