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
                    v-if="!alerts.length"
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
                        Alerts: {{ filtered.length
                        }}<span v-if="firingCount" class="ml-3 text-red-600 dark:text-red-400"
                            >{{ firingCount }} firing</span
                        >
                    </template>
                    <template #actions>
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
                        :value="filtered"
                        size="small"
                        sortField="stateRank"
                        :sortOrder="1"
                        removableSort
                        :row-hover="true"
                        :paginator="filtered.length > 50"
                        :rows="50"
                        data-testid="alerts-table"
                    >
                        <Column field="name" header="Name" class="font-medium pl-4" :sortable="true">
                            <template #body="{ data }">
                                <router-link :to="{ name: 'alert', params: { alertId: data.id } }" class="table-link">
                                    {{ data.name }}
                                </router-link>
                                <div v-if="data.tags.length" class="flex flex-wrap gap-1 mt-1">
                                    <Tag v-for="t in data.tags" :key="t" :value="t" severity="secondary" />
                                </div>
                            </template>
                        </Column>
                        <Column field="stateRank" header="State" class="w-1 text-nowrap" :sortable="true">
                            <template #body="{ data }">
                                <Tag
                                    :value="STATE_LABEL[data.state]"
                                    :severity="STATE_SEVERITY[data.state]"
                                    :data-testid="`alert-state-${data.id}`"
                                    v-tooltip.top="data.last_error || null"
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
                        <Column field="ownerName" header="Owner" class="w-1 text-nowrap" :sortable="true" />
                        <Column field="evaluatedAt" header="Evaluated" class="w-1 text-nowrap" :sortable="true">
                            <template #body="{ data }">
                                <span v-if="data.last_evaluated_at" :title="data.last_evaluated_at">{{
                                    relative(data.last_evaluated_at)
                                }}</span>
                                <span v-else class="text-surface-500">never</span>
                            </template>
                        </Column>
                    </DataTable>
                </ContentBlock>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { DateTime } from 'luxon'
import { Button, Column, DataTable, IconField, InputIcon, InputText, Tag } from 'primevue'
import { Bell } from 'lucide-vue-next'

import Content from '@/components/common/Content.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import DataView from '@/components/common/DataView.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import { AlertService } from '@/features/alerts/service.js'
import { STATE_LABEL, STATE_SEVERITY, describeCondition, describeSeries } from '@/features/alerts/useAlerts.js'

const router = useRouter()
const srv = new AlertService()
const RANK = { ALERT: 0, ERROR: 1, PENDING: 2, INSUFFICIENT_DATA: 3, OK: 4, DISABLED: 5 }

const alerts = ref([])
const loading = ref(true)
const error = ref('')
const search = ref('')

const load = async () => {
    const response = await srv.list()
    alerts.value = (response.data || []).map((a) => ({
        ...a,
        stateRank: RANK[a.state] ?? 9,
        ownerName: a.owner?.username || '',
        evaluatedAt: a.last_evaluated_at || '',
    }))
    error.value = response.errors.join(', ')
    loading.value = false
}
load()

const filtered = computed(() => {
    const q = search.value.trim().toLowerCase()
    if (!q) return alerts.value
    return alerts.value.filter((a) =>
        [a.name, a.source, a.dashboard?.name, ...a.tags].some((v) => (v || '').toLowerCase().includes(q)),
    )
})
const firingCount = computed(() => alerts.value.filter((a) => a.state === 'ALERT').length)
const relative = (iso) => DateTime.fromISO(iso).toRelative()
</script>
