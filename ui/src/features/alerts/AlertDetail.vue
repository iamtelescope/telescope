<template>
    <Content>
        <template #header>
            <ListHeader>
                <template #title>
                    <div class="flex items-center gap-3 min-w-0">
                        <router-link
                            :to="{ name: 'alerts' }"
                            class="text-surface-500 hover:text-primary"
                            title="Alerts"
                        >
                            <Bell class="w-8 h-8" />
                        </router-link>
                        <span class="truncate" data-testid="alert-detail-name">{{ alert?.name || 'Alert' }}</span>
                        <Tag
                            v-if="alert"
                            :value="STATE_LABEL[alert.state]"
                            :severity="STATE_SEVERITY[alert.state]"
                            data-testid="alert-detail-state"
                        />
                    </div>
                </template>
                <template #subtitle>
                    <span v-if="alert" class="text-sm text-surface-500 font-mono">
                        {{ describeSeries(alert.series) }} {{ describeCondition(alert) }} per {{ alert.interval }}
                    </span>
                </template>
                <template #actions>
                    <template v-if="alert">
                        <SilenceButton
                            v-if="alert.can_edit"
                            :alert="alert"
                            class="mr-2"
                            @changed="(a) => (alert = a)"
                        />
                        <Button
                            v-if="alert.can_edit && alert.channels.length"
                            size="small"
                            severity="secondary"
                            outlined
                            icon="pi pi-send"
                            label="Test notification"
                            class="mr-2"
                            :loading="testing"
                            data-testid="alert-test"
                            @click="sendTest"
                        />
                        <Button
                            v-if="alert.can_edit"
                            size="small"
                            severity="secondary"
                            outlined
                            :icon="disabled ? 'pi pi-play' : 'pi pi-pause'"
                            :label="disabled ? 'Enable' : 'Disable'"
                            class="mr-2"
                            :loading="toggling"
                            data-testid="alert-toggle"
                            @click="toggle"
                        />
                        <Button
                            size="small"
                            icon="pi pi-pencil"
                            :label="alert.can_edit ? 'Edit' : 'Definition'"
                            data-testid="alert-edit"
                            @click="router.push({ name: 'alert', params: { alertId: alert.id } })"
                        />
                    </template>
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[loadError]">
                <template #loader>
                    <ContentBlock header="Alert" :collapsible="false">
                        <SkeletonList :columns="2" :rows="6" />
                    </ContentBlock>
                </template>
                <div v-if="alert" class="flex flex-col gap-4">
                    <div
                        v-if="alert.silenced"
                        class="p-3 rounded-md border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 text-amber-800 dark:text-amber-200 text-sm"
                        data-testid="alert-silenced-banner"
                    >
                        <i class="pi pi-volume-off mr-2" />Silenced until {{ fmtIso(alert.silenced.until) }} by
                        {{ alert.silenced.by?.username || 'unknown' }}. Windows are still evaluated; notifications are
                        held and sent if the alert is still firing afterwards.
                    </div>
                    <div
                        v-if="alert.last_error"
                        class="p-3 rounded-md border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 text-sm"
                    >
                        <i class="pi pi-exclamation-triangle mr-2" />{{ alert.last_error }}
                    </div>

                    <ContentBlock header="Summary" :collapsible="false">
                        <dl class="grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-3 p-4 text-sm">
                            <div>
                                <dt class="text-surface-500">On</dt>
                                <dd>
                                    <router-link
                                        v-if="alert.kind === 'tile' && alert.dashboard"
                                        :to="{ name: 'dashboard', params: { dashboardSlug: alert.dashboard.slug } }"
                                        class="table-link"
                                        ><i class="pi pi-th-large mr-1" />{{ alert.dashboard.name }}</router-link
                                    >
                                    <router-link
                                        v-else
                                        :to="{ name: 'explore', params: { sourceSlug: alert.source } }"
                                        class="table-link"
                                        ><i class="pi pi-search mr-1" />{{ alert.source }}</router-link
                                    >
                                    <div v-if="alert.query" class="font-mono text-xs text-surface-500 break-all">
                                        {{ alert.query }}
                                    </div>
                                </dd>
                            </div>
                            <div>
                                <dt class="text-surface-500">Schedule</dt>
                                <dd>
                                    Every {{ alert.interval }}
                                    <span v-if="alert.schedule_start_at"
                                        >, from {{ fmtIso(alert.schedule_start_at) }}</span
                                    >
                                    <span v-else-if="alert.schedule_offset_minutes"
                                        >, offset {{ alert.schedule_offset_minutes }} min</span
                                    >
                                    <span v-if="alert.of_windows > 1"
                                        >; fires after {{ alert.consecutive_windows }} of {{ alert.of_windows }}</span
                                    >
                                </dd>
                            </div>
                            <div>
                                <dt class="text-surface-500">Notifies</dt>
                                <dd data-testid="alert-detail-channels">
                                    <span v-if="!channelNames.length" class="text-surface-500">nobody</span>
                                    {{ channelNames.join(', ') }}
                                </dd>
                            </div>
                            <div>
                                <dt class="text-surface-500">Owner</dt>
                                <dd>{{ alert.owner?.username }}</dd>
                            </div>
                            <div>
                                <dt class="text-surface-500">Last evaluated</dt>
                                <dd>{{ alert.last_evaluated_at ? relative(alert.last_evaluated_at) : 'never' }}</dd>
                            </div>
                            <div v-if="alert.tags.length">
                                <dt class="text-surface-500">Tags</dt>
                                <dd class="flex flex-wrap gap-1">
                                    <Tag v-for="t in alert.tags" :key="t" :value="t" severity="secondary" />
                                </dd>
                            </div>
                            <div v-if="alert.note" class="md:col-span-3">
                                <dt class="text-surface-500">Note</dt>
                                <dd class="whitespace-pre-wrap">{{ alert.note }}</dd>
                            </div>
                        </dl>
                    </ContentBlock>

                    <ContentBlock :collapsible="false">
                        <template #header_text>History</template>
                        <template #actions>
                            <SelectButton
                                v-model="rangeKey"
                                :options="RANGES"
                                optionLabel="label"
                                optionValue="key"
                                :allowEmpty="false"
                                size="small"
                                data-testid="alert-history-range"
                            />
                        </template>
                        <div class="p-4 flex flex-col gap-3">
                            <div class="text-xs text-surface-500">
                                {{ fmtMs(range.from) }} – {{ fmtMs(range.to) }}
                                <span v-if="truncated" class="text-amber-600"> (first {{ rows.length }} rows)</span>
                            </div>
                            <div
                                class="flex h-5 w-full rounded overflow-hidden bg-surface-100 dark:bg-surface-800"
                                data-testid="alert-timeline"
                            >
                                <div
                                    v-for="(seg, i) in timeline"
                                    :key="i"
                                    :style="{ flexGrow: seg.count, background: STATE_COLOR[seg.state] }"
                                    :title="`${seg.state ? STATE_LABEL[seg.state] : 'Not evaluated'}: ${fmtMs(seg.from)} – ${fmtMs(seg.to)}`"
                                    :data-state="seg.state || 'NONE'"
                                />
                            </div>
                            <div class="flex flex-wrap gap-3 text-xs text-surface-500">
                                <span v-for="s in LEGEND" :key="s"
                                    ><span
                                        class="inline-block w-3 h-3 rounded-sm align-middle mr-1"
                                        :style="{ background: STATE_COLOR[s] }"
                                    />{{ STATE_LABEL[s] }}</span
                                >
                            </div>
                            <div v-if="historyLoading" class="h-64 flex items-center justify-center text-surface-500">
                                <i class="pi pi-spin pi-spinner mr-2" />Loading
                            </div>
                            <div
                                v-else-if="!rows.length"
                                class="h-24 flex items-center justify-center text-surface-500 text-sm"
                                data-testid="alert-history-empty"
                            >
                                No evaluations in this range.
                            </div>
                            <PreviewChart v-else :data="chartData" :alert="alert" bandLabel="firing" />
                        </div>
                    </ContentBlock>

                    <ContentBlock :collapsible="false">
                        <template #header_text>Evaluations</template>
                        <DataTable
                            :value="evaluations"
                            v-model:expandedRows="expanded"
                            dataKey="window_start"
                            size="small"
                            data-testid="alert-evaluations"
                        >
                            <template #empty>
                                <div class="p-2 text-surface-500">
                                    Not evaluated yet; the scheduler runs every few seconds.
                                </div>
                            </template>
                            <Column v-if="grouped" expander class="w-1" />
                            <Column header="Window" class="text-nowrap pl-4">
                                <template #body="{ data }">{{ windowText(data) }}</template>
                            </Column>
                            <Column header="State" class="w-1 text-nowrap">
                                <template #body="{ data }">
                                    <Tag :value="STATE_LABEL[data.state]" :severity="STATE_SEVERITY[data.state]" />
                                </template>
                            </Column>
                            <Column :header="grouped ? 'Groups' : 'Value'" class="text-right w-1 text-nowrap">
                                <template #body="{ data }">
                                    <template v-if="grouped"
                                        >{{ data.groups.length
                                        }}<span v-if="firingIn(data)" class="text-red-600 dark:text-red-400">
                                            · {{ firingIn(data) }} firing</span
                                        ></template
                                    >
                                    <template v-else>{{ formatValue(data.groups[0]?.value) }}</template>
                                </template>
                            </Column>
                            <Column header="Notified" class="w-1 text-nowrap text-center">
                                <template #body="{ data }">
                                    <i
                                        v-if="data.groups.some((g) => g.notified_at)"
                                        class="pi pi-send text-primary"
                                        title="A notification was sent"
                                    />
                                </template>
                            </Column>
                            <Column header="Error" bodyClass="text-sm text-red-600 dark:text-red-400">
                                <template #body="{ data }">{{
                                    data.groups
                                        .map((g) => g.error)
                                        .filter(Boolean)
                                        .join('; ')
                                }}</template>
                            </Column>
                            <template #expansion="{ data }">
                                <DataTable :value="data.groups" size="small" class="ml-8">
                                    <Column field="group_key" header="Group">
                                        <template #body="{ data: g }">{{ g.group_key || '(none)' }}</template>
                                    </Column>
                                    <Column header="State" class="w-1 text-nowrap">
                                        <template #body="{ data: g }">
                                            <Tag :value="STATE_LABEL[g.state]" :severity="STATE_SEVERITY[g.state]" />
                                        </template>
                                    </Column>
                                    <Column header="Value" class="w-1 text-right">
                                        <template #body="{ data: g }">{{ formatValue(g.value) }}</template>
                                    </Column>
                                </DataTable>
                            </template>
                        </DataTable>
                        <div v-if="hasMore" class="p-3 flex justify-center">
                            <Button
                                size="small"
                                text
                                icon="pi pi-angle-down"
                                label="Load older"
                                :loading="evaluationsLoading"
                                data-testid="alert-evaluations-more"
                                @click="loadEvaluations()"
                            />
                        </div>
                    </ContentBlock>
                </div>
            </DataView>
        </template>
    </Content>
</template>

<script setup>
// Adapted from HyperDX AlertDetailPage.tsx (MIT): summary, history chart, state timeline, evaluations.
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DateTime } from 'luxon'
import { Button, Column, DataTable, SelectButton, Tag, useToast } from 'primevue'
import { Bell } from 'lucide-vue-next'

import Content from '@/components/common/Content.vue'
import ListHeader from '@/components/common/ListHeader.vue'
import DataView from '@/components/common/DataView.vue'
import ContentBlock from '@/components/common/ContentBlock.vue'
import SkeletonList from '@/components/common/SkeletonList.vue'
import PreviewChart from '@/features/alerts/PreviewChart.vue'
import SilenceButton from '@/features/alerts/SilenceButton.vue'
import { AlertService } from '@/features/alerts/service.js'
import { STATE_LABEL, STATE_SEVERITY, describeCondition, describeSeries } from '@/features/alerts/useAlerts.js'

const RANGES = [
    { key: '6h', label: '6h', ms: 6 * 3600_000 },
    { key: '24h', label: '24h', ms: 24 * 3600_000 },
    { key: '7d', label: '7d', ms: 7 * 86400_000 },
    { key: '30d', label: '30d', ms: 30 * 86400_000 },
]
const RANK = ['ERROR', 'ALERT', 'PENDING', 'OK', 'INSUFFICIENT_DATA', 'DISABLED']
const STATE_COLOR = {
    OK: 'rgba(34, 197, 94, 0.75)',
    ALERT: 'rgba(239, 68, 68, 0.9)',
    PENDING: 'rgba(245, 158, 11, 0.85)',
    INSUFFICIENT_DATA: 'rgba(148, 163, 184, 0.7)',
    ERROR: 'rgba(126, 34, 206, 0.85)',
    DISABLED: 'rgba(148, 163, 184, 0.4)',
    '': 'transparent',
}
const LEGEND = ['OK', 'PENDING', 'ALERT', 'INSUFFICIENT_DATA', 'ERROR']

const route = useRoute()
const router = useRouter()
const toast = useToast()
const srv = new AlertService()

const alert = ref(null)
const channels = ref([])
const loading = ref(true)
const loadError = ref('')
const testing = ref(false)
const toggling = ref(false)
const rangeKey = ref(route.query.from && route.query.to ? 'custom' : '24h')
const rows = ref([])
const historyLoading = ref(false)
const evaluations = ref([])
const expanded = ref({})
const hasMore = ref(false)
const nextBefore = ref(null)
const evaluationsLoading = ref(false)

const alertId = computed(() => route.params.alertId)
const disabled = computed(() => alert.value?.state === 'DISABLED')
const step = computed(
    () =>
        ({ '1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '6h': 360, '12h': 720, '1d': 1440 })[
            alert.value?.interval
        ] * 60_000,
)
const grouped = computed(() => evaluations.value.some((e) => e.groups.length > 1 || e.groups[0]?.group_key))
const channelNames = computed(() =>
    (alert.value?.channels || []).map((id) => channels.value.find((c) => c.id === id)?.name || `#${id}`),
)
const truncated = computed(() => rows.value.length >= 10_000)

// Anchored at the last evaluated window, so paused alerts still show their history; ?from&to (ms) override.
const range = computed(() => {
    if (rangeKey.value === 'custom') return { from: Number(route.query.from), to: Number(route.query.to) }
    const a = alert.value
    const ms = RANGES.find((r) => r.key === rangeKey.value).ms
    const to = a?.last_evaluated_window != null ? a.last_evaluated_window + step.value : Date.now()
    return { from: to - ms, to }
})

const windowState = (states) => RANK.find((s) => states.has(s)) || ''
const byWindow = computed(() => {
    const map = new Map()
    for (const r of rows.value) {
        if (!map.has(r.window_start)) map.set(r.window_start, new Set())
        map.get(r.window_start).add(r.state)
    }
    return map
})
// Every scheduled window in the range, so the timeline and the chart span all of it.
const grid = computed(() => {
    const { from, to } = range.value
    const s = step.value
    const a = alert.value
    const origin = a.schedule_start_at
        ? DateTime.fromISO(a.schedule_start_at).toMillis()
        : a.schedule_offset_minutes * 60_000
    const windows = []
    for (let t = origin + Math.ceil((from - origin) / s) * s; t < to; t += s) windows.push(t)
    return windows
})
const timeline = computed(() => {
    const s = step.value
    const segments = []
    for (const t of grid.value) {
        const states = byWindow.value.get(t)
        const state = states ? windowState(states) : ''
        const last = segments[segments.length - 1]
        if (last && last.state === state) {
            last.count++
            last.to = t + s
        } else segments.push({ state, count: 1, from: t, to: t + s })
    }
    return segments
})
const chartData = computed(() => {
    const windows = [...new Set([...grid.value, ...byWindow.value.keys()])].sort((a, b) => a - b)
    const index = new Map(windows.map((t, i) => [t, i]))
    const groups = new Map()
    for (const r of rows.value) {
        if (!groups.has(r.group_key))
            groups.set(r.group_key, { values: windows.map(() => null), fired: windows.map(() => false) })
        const g = groups.get(r.group_key)
        g.values[index.get(r.window_start)] = r.value
        g.fired[index.get(r.window_start)] = r.state === 'ALERT'
    }
    return {
        windows,
        step_ms: step.value,
        series: [...groups].map(([group, g]) => ({ group, values: g.values, would_fire: g.fired })),
    }
})

let historySeq = 0
const loadHistory = async () => {
    if (!alert.value) return
    const mine = ++historySeq
    historyLoading.value = true
    const response = await srv.history(alertId.value, range.value)
    if (mine !== historySeq) return
    historyLoading.value = false
    rows.value = response.result ? response.data : []
}
const loadEvaluations = async (reset = false) => {
    evaluationsLoading.value = true
    const response = await srv.evaluations(alertId.value, { limit: 50, before: reset ? null : nextBefore.value })
    evaluationsLoading.value = false
    if (!response.result) return
    evaluations.value = reset ? response.data.items : [...evaluations.value, ...response.data.items]
    hasMore.value = response.data.has_more
    nextBefore.value = response.data.next_before
}
const load = async () => {
    loading.value = true
    const response = await srv.get(alertId.value)
    alert.value = response.result ? response.data : null
    loadError.value = response.errors.join(', ')
    loading.value = false
    if (alert.value) await Promise.all([loadHistory(), loadEvaluations(true)])
}
srv.channels().then((r) => (channels.value = r.data || []))
watch(alertId, (id) => id && load(), { immediate: true })
watch(rangeKey, loadHistory)

const toggle = async () => {
    toggling.value = true
    const response = await srv.setEnabled(alert.value.id, disabled.value)
    toggling.value = false
    response.sendToast(toast)
    if (response.result) alert.value = response.data
}
const sendTest = async () => {
    testing.value = true
    const response = await srv.test(alert.value.id)
    testing.value = false
    response.sendToast(toast)
}

const firingIn = (e) => e.groups.filter((g) => g.state === 'ALERT').length
const relative = (iso) => DateTime.fromISO(iso).toRelative()
const fmtIso = (iso) => DateTime.fromISO(iso).toFormat('yyyy-MM-dd HH:mm')
const fmtMs = (ms) => DateTime.fromMillis(ms).toFormat('yyyy-MM-dd HH:mm')
const windowText = (row) => `${fmtMs(row.window_start)} – ${DateTime.fromMillis(row.window_end).toFormat('HH:mm')}`
const formatValue = (v) =>
    v === null || v === undefined ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 4 })
</script>
