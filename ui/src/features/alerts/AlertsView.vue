<template>
    <Content>
        <template #header>
            <ListHeader>
                <template #title>
                    <div class="flex items-center">
                        <Bell class="mr-3 w-8 h-8" />
                        Alerts
                    </div>
                </template>
                <template #actions>
                    <Button
                        size="small"
                        severity="secondary"
                        outlined
                        icon="pi pi-send"
                        label="Channels"
                        class="mr-2"
                        data-testid="alerts-channels-btn"
                        @click="router.push({ name: 'alertChannels' })"
                    />
                    <Button
                        size="small"
                        icon="pi pi-plus"
                        label="New alert"
                        data-testid="alerts-new-btn"
                        @click="router.push({ name: 'alertNew' })"
                    />
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[error]">
                <template #loader>
                    <ContentBlock header="Alerts" :collapsible="false">
                        <SkeletonList :columns="5" :rows="8" />
                    </ContentBlock>
                </template>
                <div
                    v-if="!total && !filtering"
                    class="flex flex-col items-center justify-center text-center py-20 px-4 border border-dashed rounded-lg border-surface-300 dark:border-surface-600"
                    data-testid="alerts-empty"
                >
                    <div class="flex items-center justify-center w-16 h-16 mb-5 rounded-full bg-highlight">
                        <Bell class="w-8 h-8" :stroke-width="1.5" />
                    </div>
                    <div class="text-xl font-medium mb-2">No alerts yet</div>
                    <p class="max-w-md mb-6 text-surface-500 dark:text-surface-400">
                        Get notified in Slack, PagerDuty, email or any webhook when a search or a dashboard chart
                        crosses a threshold.
                    </p>
                    <Button
                        size="small"
                        icon="pi pi-plus"
                        label="New alert"
                        @click="router.push({ name: 'alertNew' })"
                    />
                </div>
                <ContentBlock v-else :collapsible="false">
                    <template #header_text>
                        Alerts: {{ total
                        }}<span v-if="firingCount" class="ml-3 text-red-600 dark:text-red-400"
                            >{{ firingCount }} firing</span
                        >
                    </template>
                    <template #actions>
                        <MultiSelect
                            v-model="tags"
                            :options="allTags"
                            placeholder="Tags"
                            display="chip"
                            size="small"
                            class="w-56 mr-2"
                            :showToggleAll="false"
                            emptyMessage="No tags yet"
                            data-testid="alerts-tags-filter"
                        />
                        <IconField>
                            <InputIcon class="pi pi-search" />
                            <InputText
                                v-model="search"
                                placeholder="Search alerts"
                                size="small"
                                class="w-64"
                                data-testid="alerts-search"
                            />
                        </IconField>
                    </template>
                    <DataTable
                        :value="alerts"
                        size="small"
                        lazy
                        :loading="pageLoading"
                        :row-hover="true"
                        :paginator="total > PAGE_SIZE"
                        :rows="PAGE_SIZE"
                        :totalRecords="total"
                        :first="(page - 1) * PAGE_SIZE"
                        @page="(e) => (page = e.page + 1)"
                        data-testid="alerts-table"
                    >
                        <template #empty>
                            <div class="p-2 text-surface-500">No alerts match the filter.</div>
                        </template>
                        <Column field="name" header="Name" class="font-medium pl-4">
                            <template #body="{ data }">
                                <router-link
                                    :to="{ name: 'alertDetail', params: { alertId: data.id } }"
                                    class="table-link"
                                >
                                    {{ data.name }}
                                </router-link>
                                <div v-if="data.tags.length" class="flex flex-wrap gap-1 mt-1">
                                    <Tag v-for="t in data.tags" :key="t" :value="t" severity="secondary" />
                                </div>
                            </template>
                        </Column>
                        <Column header="State" class="w-1 text-nowrap">
                            <template #body="{ data }">
                                <Tag
                                    :value="STATE_LABEL[data.state]"
                                    :severity="STATE_SEVERITY[data.state]"
                                    :data-testid="`alert-state-${data.id}`"
                                    v-tooltip.top="data.last_error || null"
                                />
                                <i
                                    v-if="data.silenced"
                                    class="pi pi-volume-off ml-2 text-amber-600"
                                    v-tooltip.top="`Silenced until ${data.silenced.until}`"
                                    :data-testid="`alert-silenced-${data.id}`"
                                />
                            </template>
                        </Column>
                        <Column header="Condition">
                            <template #body="{ data }">
                                <span class="font-mono text-sm">
                                    {{ describeSeries(data.series) }} {{ describeCondition(data) }}
                                </span>
                                <span class="text-surface-500 text-sm"> per {{ data.interval }}</span>
                                <span v-if="data.of_windows > 1" class="text-surface-500 text-sm">
                                    , {{ data.consecutive_windows }} of {{ data.of_windows }}</span
                                >
                                <div v-if="data.group_by" class="text-sm text-surface-500">by {{ data.group_by }}</div>
                            </template>
                        </Column>
                        <Column header="On" class="text-nowrap">
                            <template #body="{ data }">
                                <template v-if="data.kind === 'tile' && data.dashboard">
                                    <i class="pi pi-th-large mr-1 text-surface-500" />
                                    <router-link
                                        :to="{ name: 'dashboard', params: { dashboardSlug: data.dashboard.slug } }"
                                        class="table-link"
                                        >{{ data.dashboard.name }}</router-link
                                    >
                                </template>
                                <template v-else>
                                    <i class="pi pi-search mr-1 text-surface-500" />
                                    <router-link
                                        :to="{ name: 'explore', params: { sourceSlug: data.source } }"
                                        class="table-link"
                                        >{{ data.source }}</router-link
                                    >
                                </template>
                            </template>
                        </Column>
                        <Column field="owner.username" header="Owner" class="w-1 text-nowrap" />
                        <Column header="Evaluated" class="w-1 text-nowrap">
                            <template #body="{ data }">
                                <span v-if="data.last_evaluated_at" :title="data.last_evaluated_at">{{
                                    relative(data.last_evaluated_at)
                                }}</span>
                                <span v-else class="text-surface-500">never</span>
                            </template>
                        </Column>
                        <Column class="w-1 text-nowrap pr-4">
                            <template #body="{ data }">
                                <div class="flex items-center gap-2 justify-end">
                                    <SilenceButton v-if="data.can_edit" :alert="data" compact @changed="replace" />
                                    <ToggleSwitch
                                        v-if="data.can_edit"
                                        :key="`${data.id}:${toggleResets}`"
                                        :modelValue="data.state !== 'DISABLED'"
                                        v-tooltip.top="data.state === 'DISABLED' ? 'Enable' : 'Disable'"
                                        :data-testid="`alert-enabled-${data.id}`"
                                        @update:modelValue="(on) => setEnabled(data, on)"
                                    />
                                </div>
                            </template>
                        </Column>
                    </DataTable>
                </ContentBlock>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
// Server-side pages with a tags filter, as HyperDX AlertsPage.tsx (MIT); silence and enable per row.
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { DateTime } from 'luxon'
import {
    Button,
    Column,
    DataTable,
    IconField,
    InputIcon,
    InputText,
    MultiSelect,
    Tag,
    ToggleSwitch,
    useToast,
} from 'primevue'
import { Bell } from 'lucide-vue-next'

import Content from '@/components/common/Content.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import DataView from '@/components/common/DataView.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import SilenceButton from '@/features/alerts/SilenceButton.vue'
import { AlertService } from '@/features/alerts/service.js'
import { STATE_LABEL, STATE_SEVERITY, describeCondition, describeSeries } from '@/features/alerts/useAlerts.js'

const PAGE_SIZE = 50
const router = useRouter()
const toast = useToast()
const srv = new AlertService()

const alerts = ref([])
const total = ref(0)
const allTags = ref([])
const firingCount = ref(0)
const loading = ref(true)
const pageLoading = ref(false)
const error = ref('')
const search = ref('')
const tags = ref([])
const page = ref(1)
const toggleResets = ref(0)
const filtering = computed(() => !!search.value.trim() || tags.value.length > 0)

let seq = 0
const load = async () => {
    const mine = ++seq
    pageLoading.value = true
    const params = { page: page.value, page_size: PAGE_SIZE, q: search.value.trim(), tags: tags.value.join(',') }
    const [response, firing] = await Promise.all([
        srv.list(params),
        srv.list({ page: 1, page_size: 1, state: 'ALERT' }),
    ])
    if (mine !== seq) return
    if (response.result) {
        alerts.value = response.data.items
        total.value = response.data.total
        allTags.value = response.data.tags
    }
    firingCount.value = firing.result ? firing.data.total : 0
    error.value = response.errors.join(', ')
    loading.value = false
    pageLoading.value = false
}
load()

let searchTimer = null
watch(search, () => {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => (page.value === 1 ? load() : (page.value = 1)), 300)
})
onBeforeUnmount(() => clearTimeout(searchTimer))
watch(tags, () => (page.value === 1 ? load() : (page.value = 1)))
watch(page, load)

const replace = (updated) => {
    alerts.value = alerts.value.map((a) => (a.id === updated.id ? updated : a))
}
const setEnabled = async (alert, enabled) => {
    const response = await srv.setEnabled(alert.id, enabled)
    response.sendToast(toast)
    // A failed request re-mounts the switch, which flipped itself before emitting.
    if (response.result) replace(response.data)
    else toggleResets.value++
}
const relative = (iso) => DateTime.fromISO(iso).toRelative()
</script>
