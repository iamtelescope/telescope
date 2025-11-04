<template>
    <Content>
        <template #header>
            <Header>
                <template #title> <Cable class="mr-3 w-8 h-8" /> Connections </template>
            </Header>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <template #loader>
                    <div class="flex flex-col max-w-[1000px]">
                        <Header>
                            <template #title>
                                <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-48"></div>
                            </template>
                            <template #actions>
                                <div class="flex flex-wrap gap-2">
                                    <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-16"></div>
                                    <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-20"></div>
                                </div>
                            </template>
                        </Header>
                        <div class="mt-4">
                            <ObjectSkeleton
                                :tabs="['OVERVIEW', 'ACCESS CONTROL']"
                                :sections="{
                                    General: ['Id', 'Kind', 'Name', 'Description', 'Created', 'Updated'],
                                }"
                            />
                        </div>
                    </div>
                </template>
                <div class="flex flex-col max-w-[1000px]">
                    <Header>
                        <template #title>
                            <div class="flex items-center">
                                <img
                                    v-if="connection?.kind"
                                    :src="require(`@/assets/${connection.kind}.png`)"
                                    height="24px"
                                    width="24px"
                                    class="mr-2"
                                    :title="connection.kind"
                                />
                                {{ connection?.name || 'Connection' }}
                            </div>
                        </template>
                        <template #actions>
                            <div class="flex flex-wrap gap-2">
                                <Button
                                    v-if="connection?.canEdit()"
                                    severity="primary"
                                    label="Edit"
                                    icon="pi pi-pencil"
                                    @click="handleConnectionEdit"
                                    :disabled="!connection || loading"
                                    size="small"
                                />
                                <ConfirmPopup></ConfirmPopup>
                                <Button
                                    v-if="connection?.canDelete()"
                                    severity="primary"
                                    label="Delete"
                                    icon="pi pi-trash"
                                    @click="connectionDeleteConfirm($event)"
                                    :loading="connectionDeleteButtonLoading"
                                    :disabled="!connection || loading"
                                    size="small"
                                />
                            </div>
                        </template>
                    </Header>
                    <div class="mt-4">
                        <Tabs v-model:value="activeTab">
                            <TabList>
                                <Tab value="overview">OVERVIEW</Tab>
                                <Tab value="accessControl">ACCESS CONTROL</Tab>
                            </TabList>
                            <TabPanels class="pl-0 pr-0">
                                <TabPanel value="overview">
                                    <ContentBlock header="General">
                                        <DataRow name="Id" :value="connection?.id" :copy="false" />
                                        <DataRow name="Kind" :value="connection?.kind" :copy="false" />
                                        <DataRow name="Name" :value="connection?.name" :copy="false" />
                                        <DataRow name="Description" :copy="false">
                                            <EmptyValue :value="connection?.description" />
                                        </DataRow>
                                        <DataRow
                                            name="Created"
                                            :value="formatDate(connection?.createdAt)"
                                            :copy="false"
                                        />
                                        <DataRow
                                            name="Updated"
                                            :value="formatDate(connection?.updatedAt)"
                                            :showBorder="false"
                                            :copy="false"
                                        />
                                    </ContentBlock>

                                    <ContentBlock header="Target" class="mt-6" v-if="connection?.data">
                                        <template v-if="connection?.kind === 'clickhouse'">
                                            <DataRow name="Host" :value="connection.data.host" :copy="false" />
                                            <DataRow name="Port" :value="connection.data.port" :copy="false" />
                                            <DataRow name="User" :value="connection.data.user" :copy="false" />
                                            <DataRow name="HTTPS" :copy="false">
                                                <span
                                                    :class="
                                                        connection.data.ssl
                                                            ? 'text-green-600 dark:text-green-400'
                                                            : 'text-red-600 dark:text-red-400'
                                                    "
                                                >
                                                    {{ connection.data.ssl ? 'Enabled' : 'Disabled' }}
                                                </span>
                                            </DataRow>
                                            <template v-if="connection.data.ssl">
                                                <DataRow name="Verify" :copy="false">
                                                    <span
                                                        :class="
                                                            connection.data.verify
                                                                ? 'text-green-600 dark:text-green-400'
                                                                : 'text-red-600 dark:text-red-400'
                                                        "
                                                    >
                                                        {{ connection.data.verify ? 'Enabled' : 'Disabled' }}
                                                    </span>
                                                </DataRow>
                                                <DataRow name="CA Certificate" :copy="false">
                                                    <pre
                                                        v-if="connection.data.ca_cert"
                                                        class="text-xs whitespace-pre-wrap break-words"
                                                        >{{ connection.data.ca_cert }}</pre
                                                    >
                                                    <EmptyValue
                                                        v-else
                                                        :value="connection.data.ca_cert"
                                                        :isDark="isDark"
                                                    />
                                                </DataRow>
                                                <DataRow name="Client Certificate" :copy="false">
                                                    <pre
                                                        v-if="connection.data.client_cert"
                                                        class="text-xs whitespace-pre-wrap break-words"
                                                        >{{ connection.data.client_cert }}</pre
                                                    >
                                                    <EmptyValue
                                                        v-else
                                                        :value="connection.data.client_cert"
                                                        :isDark="isDark"
                                                    />
                                                </DataRow>
                                                <DataRow name="Client Certificate Key" :copy="false">
                                                    <pre
                                                        v-if="connection.data.client_cert_key"
                                                        class="text-xs whitespace-pre-wrap break-words"
                                                        >{{ connection.data.client_cert_key }}</pre
                                                    >
                                                    <EmptyValue
                                                        v-else
                                                        :value="connection.data.client_cert_key"
                                                        :isDark="isDark"
                                                    />
                                                </DataRow>
                                                <DataRow name="Server Host Name" :copy="false">
                                                    <EmptyValue
                                                        :value="connection.data.server_host_name"
                                                        :isDark="isDark"
                                                    />
                                                </DataRow>
                                                <DataRow name="TLS Mode" :copy="false" :showBorder="false">
                                                    <EmptyValue :value="connection.data.tls_mode" :isDark="isDark" />
                                                </DataRow>
                                            </template>
                                        </template>

                                        <template v-else-if="connection?.kind === 'docker'">
                                            <DataRow
                                                name="Address"
                                                :value="connection.data.address"
                                                :copy="false"
                                                :showBorder="false"
                                            />
                                        </template>

                                        <template v-else>
                                            <DataRow
                                                v-for="(value, key) in connection.data"
                                                :key="key"
                                                :name="formatKey(key)"
                                                :copy="false"
                                                :showBorder="false"
                                            >
                                                <EmptyValue :value="value" :isDark="isDark" />
                                            </DataRow>
                                        </template>
                                    </ContentBlock>
                                </TabPanel>
                                <TabPanel value="accessControl">
                                    <ConnectionAccessControl
                                        :connection="connection"
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
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Cable } from 'lucide-vue-next'
import { useDark } from '@vueuse/core'
import { useConfirm } from 'primevue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import ConfirmPopup from 'primevue/confirmpopup'
import { Tabs, TabList, Tab, TabPanels, TabPanel } from 'primevue'

import { useGetConnection } from '@/composables/connections/useConnectionService'
import { ConnectionService } from '@/sdk/services/connection'

import Content from '@/components/common/Content.vue'
import DataView from '@/components/common/DataView'
import DataRow from '@/components/common/DataRow.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import EmptyValue from '@/components/common/EmptyValue.vue'
import Header from '@/components/common/Header.vue'
import ObjectSkeleton from '@/components/common/ObjectSkeleton.vue'
import ConnectionAccessControl from '@/components/connections/ConnectionAccessControl.vue'

const route = useRoute()
const router = useRouter()
const isDark = useDark()
const toast = useToast()
const confirm = useConfirm()

const connectionSrv = new ConnectionService()
const connectionDeleteButtonLoading = ref(false)
const activeTab = ref('overview')

const connectionId = route.params.connectionId

const { connection, error, loading, load } = useGetConnection(connectionId)

if (route.query.tab) {
    activeTab.value = route.query.tab
}

const formatDate = (dateString) => {
    if (!dateString) return '—'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    })
}

const formatKey = (key) => {
    return key
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
}

const handleConnectionEdit = () => {
    router.push({ name: 'connectionEdit', params: { connectionId: connectionId } })
}

const connectionDeleteConfirm = (event) => {
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
            connectionDeleteButtonLoading.value = true
            let response = await connectionSrv.deleteConnection(connection.value.id)
            connectionDeleteButtonLoading.value = false
            response.sendToastErrors(toast)
            if (response.result) {
                router.push({ name: 'connections' }).then(() => response.sendToastMessages(toast))
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
