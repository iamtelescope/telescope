<template>
    <Content>
        <template #header>
            <ListHeader>
                <template #title>
                    <div class="flex items-center gap-3">
                        <router-link
                            :to="{ name: 'alerts' }"
                            class="text-surface-500 hover:text-primary"
                            title="Alerts"
                        >
                            <Bell class="w-8 h-8" />
                        </router-link>
                        Alert channels
                    </div>
                </template>
                <template #actions>
                    <Button
                        v-if="manager"
                        size="small"
                        icon="pi pi-plus"
                        label="New channel"
                        data-testid="channels-new-btn"
                        @click="openEditor(null)"
                    />
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <template #loader>
                    <ContentBlock header="Channels" :collapsible="false">
                        <SkeletonList :columns="4" :rows="5" />
                    </ContentBlock>
                </template>
                <div
                    v-if="!manager"
                    class="mb-4 p-3 rounded-md text-sm bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700"
                >
                    Adding and editing channels needs the
                    <span class="font-mono">manage_alert_channels</span> permission (Admin role). You can attach these
                    channels to your alerts.
                </div>
                <div
                    v-if="!rows.length"
                    class="flex flex-col items-center justify-center text-center py-16 px-4 border border-dashed rounded-lg border-surface-300 dark:border-surface-600"
                    data-testid="channels-empty"
                >
                    <i class="pi pi-send text-3xl mb-4 text-surface-500" />
                    <div class="text-xl font-medium mb-2">No channels yet</div>
                    <p class="max-w-md text-surface-500 dark:text-surface-400">
                        A channel is where alerts are delivered: a Slack incoming webhook, a PagerDuty service, email
                        addresses or any HTTP endpoint.
                    </p>
                </div>
                <ContentBlock v-else :collapsible="false" :header="`Channels: ${rows.length}`">
                    <DataTable :value="rows" size="small" :row-hover="true" data-testid="channels-table">
                        <Column field="name" header="Name" class="font-medium pl-4" />
                        <Column header="Kind" class="w-1 text-nowrap">
                            <template #body="{ data }">
                                <i :class="kind(data.kind).icon" class="mr-2 text-surface-500" />{{
                                    kind(data.kind).label
                                }}
                            </template>
                        </Column>
                        <Column v-if="manager" header="Target">
                            <template #body="{ data }">
                                <span class="font-mono text-sm text-surface-600 dark:text-surface-300">{{
                                    target(data)
                                }}</span>
                            </template>
                        </Column>
                        <Column v-if="manager" class="w-1 text-nowrap text-right pr-2">
                            <template #body="{ data }">
                                <Button
                                    icon="pi pi-send"
                                    text
                                    rounded
                                    size="small"
                                    severity="secondary"
                                    v-tooltip.top="'Send test'"
                                    aria-label="Send test"
                                    :loading="testing === data.id"
                                    :data-testid="`channel-test-${data.id}`"
                                    @click="sendTest(data)"
                                />
                                <Button
                                    icon="pi pi-pencil"
                                    text
                                    rounded
                                    size="small"
                                    severity="secondary"
                                    v-tooltip.top="'Edit'"
                                    aria-label="Edit"
                                    @click="openEditor(data)"
                                />
                                <Button
                                    icon="pi pi-trash"
                                    text
                                    rounded
                                    size="small"
                                    severity="danger"
                                    v-tooltip.top="'Delete'"
                                    aria-label="Delete"
                                    @click="askDelete(data)"
                                />
                            </template>
                        </Column>
                    </DataTable>
                </ContentBlock>
            </DataView>
        </template>
    </Content>

    <Dialog
        v-model:visible="editorVisible"
        modal
        :header="editing ? 'Edit channel' : 'New channel'"
        :style="{ width: '38rem' }"
        :breakpoints="{ '640px': '95vw' }"
        data-testid="channel-editor"
    >
        <div class="flex flex-col gap-4">
            <div class="grid grid-cols-4 gap-2" role="radiogroup">
                <button
                    v-for="k in CHANNEL_KINDS"
                    :key="k.value"
                    type="button"
                    role="radio"
                    :aria-checked="draft.kind === k.value"
                    :data-testid="`channel-kind-${k.value}`"
                    class="flex flex-col items-center gap-1 p-3 rounded-md border text-sm transition-colors"
                    :class="
                        draft.kind === k.value
                            ? 'border-primary bg-highlight'
                            : 'border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-800'
                    "
                    @click="draft.kind = k.value"
                >
                    <i :class="k.icon" />{{ k.label }}
                </button>
            </div>
            <div class="flex flex-col gap-1">
                <label for="channel_name" class="font-medium text-sm">Name</label>
                <InputText
                    id="channel_name"
                    v-model="draft.name"
                    size="small"
                    maxlength="128"
                    data-testid="channel-name"
                />
            </div>
            <template v-if="draft.kind === 'slack' || draft.kind === 'webhook'">
                <div class="flex flex-col gap-1">
                    <label for="channel_url" class="font-medium text-sm">{{
                        draft.kind === 'slack' ? 'Incoming webhook URL' : 'URL'
                    }}</label>
                    <InputText
                        id="channel_url"
                        v-model="draft.url"
                        size="small"
                        class="font-mono"
                        :placeholder="draft.kind === 'slack' ? 'https://hooks.slack.com/services/…' : 'https://'"
                        data-testid="channel-url"
                    />
                    <span class="text-xs text-surface-500"
                        >Stored secret; shown masked after saving. Redirects are not followed.</span
                    >
                </div>
            </template>
            <template v-if="draft.kind === 'webhook'">
                <div class="flex flex-col gap-1">
                    <label for="channel_headers" class="font-medium text-sm">Headers</label>
                    <Textarea
                        id="channel_headers"
                        v-model="draft.headers"
                        rows="2"
                        autoResize
                        class="font-mono text-sm"
                        placeholder="Authorization: Bearer …"
                    />
                    <span class="text-xs text-surface-500"
                        >One <span class="font-mono">Name: value</span> per line.</span
                    >
                </div>
                <div class="flex flex-col gap-1">
                    <label for="channel_body" class="font-medium text-sm">Body template</label>
                    <Textarea
                        id="channel_body"
                        v-model="draft.body"
                        rows="5"
                        autoResize
                        class="font-mono text-sm"
                        :placeholder="BODY_PLACEHOLDER"
                        data-testid="channel-body"
                    />
                    <span class="text-xs text-surface-500">
                        Django template; empty sends every variable as JSON. Variables: title, body, link, state,
                        status, alertId, eventId, startTime, endTime, startTimeISO, endTimeISO, comparator, threshold,
                        thresholdMax, value, groupKey, var, sourceQuery, note, tags. Use
                        <span class="font-mono">|json</span> to quote a value.
                    </span>
                </div>
            </template>
            <template v-if="draft.kind === 'pagerduty'">
                <div class="flex flex-col gap-1">
                    <label for="channel_key" class="font-medium text-sm">Integration (routing) key</label>
                    <InputText
                        id="channel_key"
                        v-model="draft.routing_key"
                        size="small"
                        class="font-mono"
                        data-testid="channel-routing-key"
                    />
                    <span class="text-xs text-surface-500"
                        >Events API v2. Firing triggers an incident, recovery resolves it.</span
                    >
                </div>
                <div class="flex flex-col gap-1">
                    <label for="channel_severity" class="font-medium text-sm">Severity</label>
                    <Select inputId="channel_severity" v-model="draft.severity" :options="SEVERITIES" size="small" />
                </div>
            </template>
            <template v-if="draft.kind === 'email'">
                <div class="flex flex-col gap-1">
                    <label for="channel_recipients" class="font-medium text-sm">Recipients</label>
                    <InputText
                        id="channel_recipients"
                        v-model="draft.recipients"
                        size="small"
                        placeholder="oncall@example.com, team@example.com"
                        data-testid="channel-recipients"
                    />
                </div>
            </template>
            <ErrorText v-if="problem" :text="problem" data-testid="channel-problem" />
        </div>
        <template #footer>
            <Button label="Cancel" severity="secondary" outlined size="small" @click="editorVisible = false" />
            <Button
                :label="editing ? 'Save' : 'Create'"
                size="small"
                :loading="saving"
                data-testid="channel-save"
                @click="saveChannel"
            />
        </template>
    </Dialog>
    <ConfirmDialog group="alert-channels" />
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { storeToRefs } from 'pinia'
import {
    Button,
    Column,
    ConfirmDialog,
    DataTable,
    Dialog,
    InputText,
    Select,
    Textarea,
    useConfirm,
    useToast,
} from 'primevue'
import { Bell } from 'lucide-vue-next'

import Content from '@/components/common/Content.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import DataView from '@/components/common/DataView.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import ErrorText from '@/components/common/ErrorText.vue'
import { AlertService } from '@/features/alerts/service.js'
import { CHANNEL_KINDS, responseProblem } from '@/features/alerts/useAlerts.js'
import { useAuthStore } from '@/stores/auth'

const SEVERITIES = ['critical', 'error', 'warning', 'info']
const BODY_PLACEHOLDER = '{"text": {{ title|json }}, "status": "{{ status }}", "value": {{ value|json }}}'

const srv = new AlertService()
const toast = useToast()
const confirm = useConfirm()
const { user } = storeToRefs(useAuthStore())
const manager = computed(() => (user.value?.permissions || []).includes('manage_alert_channels'))

const rows = ref([])
const loading = ref(true)
const error = ref('')
const testing = ref(null)

const load = async () => {
    const response = await srv.channels()
    rows.value = response.data || []
    error.value = response.errors.join(', ')
    loading.value = false
}
load()

const kind = (value) => CHANNEL_KINDS.find((k) => k.value === value) || { label: value, icon: 'pi pi-send' }
const target = (c) => {
    const config = c.config || {}
    if (c.kind === 'email') return (config.recipients || []).join(', ')
    if (c.kind === 'pagerduty') return `routing key ${config.routing_key}, ${config.severity}`
    return config.url
}

const editorVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const problem = ref('')
const draft = reactive({})

const openEditor = (channel) => {
    const config = channel?.config || {}
    editing.value = channel
    problem.value = ''
    Object.assign(draft, {
        name: channel?.name || '',
        kind: channel?.kind || 'slack',
        url: config.url || '',
        headers: Object.entries(config.headers || {})
            .map(([k, v]) => `${k}: ${v}`)
            .join('\n'),
        body: config.body || '',
        routing_key: config.routing_key || '',
        severity: config.severity || 'error',
        recipients: (config.recipients || []).join(', '),
    })
    editorVisible.value = true
}

const draftConfig = () => {
    if (draft.kind === 'slack') return { url: draft.url.trim() }
    if (draft.kind === 'webhook') {
        const headers = {}
        for (const line of draft.headers.split('\n')) {
            const at = line.indexOf(':')
            if (at > 0) headers[line.slice(0, at).trim()] = line.slice(at + 1).trim()
        }
        return { url: draft.url.trim(), headers, body: draft.body }
    }
    if (draft.kind === 'pagerduty') return { routing_key: draft.routing_key.trim(), severity: draft.severity }
    return {
        recipients: draft.recipients
            .split(',')
            .map((r) => r.trim())
            .filter(Boolean),
    }
}

const saveChannel = async () => {
    saving.value = true
    problem.value = ''
    const body = { name: draft.name.trim() || kind(draft.kind).label, kind: draft.kind, config: draftConfig() }
    const response = editing.value ? await srv.updateChannel(editing.value.id, body) : await srv.createChannel(body)
    saving.value = false
    if (!response.result) {
        problem.value = responseProblem(response)
        return
    }
    response.sendToastMessages(toast)
    editorVisible.value = false
    load()
}

const sendTest = async (channel) => {
    testing.value = channel.id
    const response = await srv.testChannel(channel.id)
    testing.value = null
    response.sendToast(toast)
}

const askDelete = (channel) =>
    confirm.require({
        group: 'alert-channels',
        header: 'Delete channel',
        message: `Delete "${channel.name}"? Alerts using it stop notifying there.`,
        acceptProps: { label: 'Delete', severity: 'danger', size: 'small' },
        rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true, size: 'small' },
        accept: async () => {
            const response = await srv.removeChannel(channel.id)
            response.sendToast(toast)
            load()
        },
    })
</script>
