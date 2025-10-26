<template>
    <div class="flex flex-col">
        <div class="flex justify-between mb-4">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button
                :label="isEditing ? 'Save' : 'Create'"
                icon="pi pi-check"
                size="small"
                @click="handleCreate"
                :loading="createLoading"
            />
        </div>
        <div v-if="targetData?.kind && namingData?.name" class="flex flex-col gap-4">
            <ContentBlock header="General">
                <DataRow name="Kind" :copy="false">
                    <div class="flex items-center">
                        <img
                            :src="require(`@/assets/${targetData.kind}.png`)"
                            height="20px"
                            width="20px"
                            class="mr-2"
                            :title="targetData.kind"
                        />
                        {{ getConnectionTypeLabel(targetData.kind) }}
                    </div>
                </DataRow>
                <DataRow name="Name" :value="namingData.name" :copy="false" />
                <DataRow name="Description" :copy="false" :showBorder="false">
                    <EmptyValue :value="namingData.description" />
                </DataRow>
            </ContentBlock>

            <ContentBlock v-if="targetData.data" header="Connection">
                <template v-if="targetData.kind === 'clickhouse'">
                    <DataRow name="Host" :value="targetData.data.host" :copy="false" />
                    <DataRow name="Port" :value="targetData.data.port" :copy="false" />
                    <DataRow name="User" :value="targetData.data.user" :copy="false" />
                    <DataRow name="HTTPS" :copy="false">
                        <span
                            :class="
                                targetData.data.ssl
                                    ? 'text-green-600 dark:text-green-400'
                                    : 'text-red-600 dark:text-red-400'
                            "
                        >
                            {{ targetData.data.ssl ? 'Enabled' : 'Disabled' }}
                        </span>
                    </DataRow>
                    <DataRow v-if="targetData.data.ssl" name="Verify" :copy="false">
                        <span
                            :class="
                                targetData.data.verify
                                    ? 'text-green-600 dark:text-green-400'
                                    : 'text-red-600 dark:text-red-400'
                            "
                        >
                            {{ targetData.data.verify ? 'Yes' : 'No' }}
                        </span>
                    </DataRow>
                    <DataRow v-if="targetData.data.ssl" name="CA Certificate" :copy="false">
                        <pre v-if="targetData.data.ca_cert" class="text-xs whitespace-pre-wrap break-words">{{
                            targetData.data.ca_cert
                        }}</pre>
                        <EmptyValue v-else value="" />
                    </DataRow>
                    <DataRow v-if="targetData.data.ssl" name="Client Certificate" :copy="false">
                        <pre v-if="targetData.data.client_cert" class="text-xs whitespace-pre-wrap break-words">{{
                            targetData.data.client_cert
                        }}</pre>
                        <EmptyValue v-else value="" />
                    </DataRow>
                    <DataRow v-if="targetData.data.ssl" name="Client Certificate Key" :copy="false">
                        <pre v-if="targetData.data.client_cert_key" class="text-xs whitespace-pre-wrap break-words">{{
                            targetData.data.client_cert_key
                        }}</pre>
                        <EmptyValue v-else value="" />
                    </DataRow>
                    <DataRow v-if="targetData.data.ssl" name="Server Host Name" :copy="false">
                        <EmptyValue :value="targetData.data.server_host_name || ''" />
                    </DataRow>
                    <DataRow v-if="targetData.data.ssl" name="TLS Mode" :copy="false" :showBorder="false">
                        <EmptyValue :value="targetData.data.tls_mode || ''" />
                    </DataRow>
                </template>
                <template v-else-if="targetData.kind === 'docker'">
                    <DataRow name="Address" :value="targetData.data.address" :copy="false" :showBorder="false" />
                </template>
            </ContentBlock>
        </div>
        <div v-else class="text-center py-8 text-gray-500 dark:text-gray-400">
            <p>Please complete the previous steps first.</p>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Button } from 'primevue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import DataRow from '@/components/common/DataRow.vue'
import EmptyValue from '@/components/common/EmptyValue.vue'

const props = defineProps(['targetData', 'namingData', 'connection'])
const emit = defineEmits(['prev', 'create'])

const createLoading = ref(false)

const isEditing = computed(() => !!props.connection)

const connectionKindOptions = [
    { label: 'ClickHouse', value: 'clickhouse' },
    { label: 'Docker', value: 'docker' },
]

const getConnectionTypeLabel = (value) => {
    const option = connectionKindOptions.find((opt) => opt.value === value)
    return option ? option.label : value
}

const handleCreate = () => {
    createLoading.value = true
    emit('create', () => {
        createLoading.value = false
    })
}
</script>
