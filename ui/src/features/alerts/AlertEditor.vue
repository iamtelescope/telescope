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
                        <span class="truncate">{{ isNew ? 'New alert' : form.name || 'Alert' }}</span>
                        <Tag
                            v-if="stored"
                            :value="STATE_LABEL[stored.state]"
                            :severity="STATE_SEVERITY[stored.state]"
                            data-testid="alert-state"
                        />
                    </div>
                </template>
                <template #subtitle>
                    <span v-if="stored" class="text-sm text-surface-500">
                        Owner {{ stored.owner?.username }}
                        <template v-if="stored.last_evaluated_at">
                            · evaluated {{ relative(stored.last_evaluated_at) }}</template
                        >
                    </span>
                </template>
                <template #actions>
                    <Button
                        v-if="stored"
                        size="small"
                        severity="secondary"
                        outlined
                        icon="pi pi-chart-line"
                        label="History"
                        class="mr-2"
                        data-testid="alert-open-detail"
                        @click="router.push({ name: 'alertDetail', params: { alertId: stored.id } })"
                    />
                    <Button
                        v-if="stored && canEdit"
                        size="small"
                        severity="danger"
                        outlined
                        icon="pi pi-trash"
                        label="Delete"
                        class="mr-2"
                        data-testid="alert-delete"
                        @click="askDelete"
                    />
                    <Button
                        v-if="canEdit"
                        size="small"
                        icon="pi pi-check"
                        :label="isNew ? 'Create alert' : 'Save'"
                        :loading="saving"
                        data-testid="alert-save"
                        @click="save"
                    />
                </template>
            </ListHeader>
        </template>
        <template #content>
            <DataView :loadings="[loading]" :errors="[loadError]">
                <template #loader>
                    <ContentBlock header="Alert" :collapsible="false">
                        <SkeletonList :columns="2" :rows="8" />
                    </ContentBlock>
                </template>
                <div class="flex flex-col gap-4">
                    <div
                        v-if="stored?.last_error"
                        class="p-3 rounded-md border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 text-sm"
                        data-testid="alert-last-error"
                    >
                        <i class="pi pi-exclamation-triangle mr-2" />{{ stored.last_error }}
                    </div>
                    <ErrorText v-if="problem" :text="problem" data-testid="alert-problem" />

                    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
                        <div class="flex flex-col gap-4 min-w-0">
                            <ContentBlock :collapsible="false">
                                <template #header_text><span class="step-badge">1</span>What to watch</template>
                                <fieldset :disabled="!canEdit" class="flex flex-col gap-4 p-4">
                                    <div class="grid grid-cols-2 gap-2" role="radiogroup">
                                        <button
                                            v-for="k in KINDS"
                                            :key="k.value"
                                            type="button"
                                            role="radio"
                                            :aria-checked="form.kind === k.value"
                                            :data-testid="`alert-kind-${k.value}`"
                                            class="flex items-start gap-2 p-3 rounded-md border text-left transition-colors"
                                            :class="
                                                form.kind === k.value
                                                    ? 'border-primary bg-highlight'
                                                    : 'border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-800'
                                            "
                                            @click="form.kind = k.value"
                                        >
                                            <i :class="k.icon" class="mt-1" />
                                            <span class="flex flex-col">
                                                <span class="font-medium">{{ k.label }}</span>
                                                <span class="text-xs text-surface-500 dark:text-surface-400">{{
                                                    k.hint
                                                }}</span>
                                            </span>
                                        </button>
                                    </div>

                                    <template v-if="form.kind === 'search'">
                                        <Field label="Source" for="alert_source" :error="errors.source">
                                            <Select
                                                inputId="alert_source"
                                                :invalid="!!errors.source"
                                                v-model="form.source"
                                                :options="sources || []"
                                                optionLabel="name"
                                                optionValue="slug"
                                                filter
                                                size="small"
                                                placeholder="Choose a source"
                                                data-testid="alert-source"
                                            />
                                        </Field>
                                        <Field
                                            label="Query"
                                            for="alert_query"
                                            hint="FlyQL filter; empty matches every row"
                                        >
                                            <InputText
                                                id="alert_query"
                                                v-model="form.query"
                                                size="small"
                                                class="font-mono"
                                                placeholder="service='checkout' and level='ERROR'"
                                                data-testid="alert-query"
                                            />
                                        </Field>
                                        <Field
                                            v-if="contextText"
                                            label="Context columns"
                                            hint="Kept from the search this alert was made from"
                                        >
                                            <span
                                                class="font-mono text-sm break-all"
                                                data-testid="alert-context-columns"
                                            >
                                                {{ contextText }}
                                            </span>
                                        </Field>
                                        <Field v-if="source?.supportRawQuery" label="Raw SQL WHERE" for="alert_raw">
                                            <InputText
                                                id="alert_raw"
                                                v-model="form.raw_query"
                                                size="small"
                                                class="font-mono"
                                                data-testid="alert-raw-query"
                                            />
                                        </Field>
                                        <div class="grid grid-cols-3 gap-2">
                                            <Field label="Value" for="alert_agg">
                                                <Select
                                                    inputId="alert_agg"
                                                    v-model="form.agg"
                                                    :options="aggOptions"
                                                    optionLabel="label"
                                                    optionValue="value"
                                                    optionDisabled="disabled"
                                                    size="small"
                                                    data-testid="alert-agg"
                                                />
                                            </Field>
                                            <Field
                                                v-if="form.agg !== 'count'"
                                                label="Column"
                                                for="alert_column"
                                                :error="errors.column"
                                            >
                                                <Select
                                                    inputId="alert_column"
                                                    :invalid="!!errors.column"
                                                    v-model="form.column"
                                                    :options="columnOptions"
                                                    filter
                                                    size="small"
                                                    data-testid="alert-column"
                                                />
                                            </Field>
                                            <Field v-if="form.agg === 'quantile'" label="Level" for="alert_level">
                                                <Select
                                                    inputId="alert_level"
                                                    v-model="form.level"
                                                    :options="QUANTILE_LEVELS"
                                                    size="small"
                                                />
                                            </Field>
                                        </div>
                                        <Field label="Group by" for="alert_group" hint="One alert per value, top 100">
                                            <Select
                                                inputId="alert_group"
                                                v-model="form.group_by"
                                                :options="groupOptions"
                                                filter
                                                showClear
                                                size="small"
                                                placeholder="No grouping"
                                                data-testid="alert-group-by"
                                            />
                                        </Field>
                                    </template>

                                    <template v-else>
                                        <Field label="Dashboard" for="alert_dashboard" :error="errors.dashboard">
                                            <Select
                                                inputId="alert_dashboard"
                                                :invalid="!!errors.dashboard"
                                                v-model="form.dashboard"
                                                :options="dashboards"
                                                optionLabel="name"
                                                optionValue="slug"
                                                filter
                                                size="small"
                                                placeholder="Choose a dashboard"
                                                data-testid="alert-dashboard"
                                            />
                                        </Field>
                                        <Field label="Chart" for="alert_tile" :error="errors.tile_id">
                                            <Select
                                                inputId="alert_tile"
                                                :invalid="!!errors.tile_id"
                                                v-model="form.tile_id"
                                                :options="tileOptions"
                                                optionLabel="label"
                                                optionValue="id"
                                                size="small"
                                                placeholder="Choose a chart"
                                                emptyMessage="This dashboard has no query tiles"
                                                data-testid="alert-tile"
                                            />
                                        </Field>
                                        <Field v-if="tileSeries.length > 1" label="Series" for="alert_series_index">
                                            <Select
                                                inputId="alert_series_index"
                                                v-model="form.series_index"
                                                :options="tileSeries"
                                                optionLabel="label"
                                                optionValue="index"
                                                size="small"
                                            />
                                        </Field>
                                        <div v-if="tile" class="text-sm text-surface-500 font-mono break-all">
                                            {{ tile.chart.source
                                            }}<span v-if="tile.chart.query">: {{ tile.chart.query }}</span
                                            ><span v-if="tile.chart.group_by"> by {{ tile.chart.group_by }}</span>
                                        </div>
                                    </template>
                                </fieldset>
                            </ContentBlock>

                            <ContentBlock :collapsible="false">
                                <template #header_text>Preview: last 24 windows</template>
                                <template #actions>
                                    <span
                                        v-if="previewSummary"
                                        class="text-sm text-surface-500 mr-2"
                                        data-testid="alert-preview-summary"
                                        >{{ previewSummary }}</span
                                    >
                                </template>
                                <div class="p-4" data-testid="alert-preview">
                                    <ErrorText v-if="previewError" :text="previewError" />
                                    <div
                                        v-else-if="previewLoading && !previewData"
                                        class="h-64 flex items-center justify-center text-surface-500"
                                    >
                                        <i class="pi pi-spin pi-spinner mr-2" />Evaluating
                                    </div>
                                    <PreviewChart v-else-if="previewData" :data="previewData" :alert="form" />
                                    <div v-else class="h-24 flex items-center justify-center text-surface-500 text-sm">
                                        Choose what to watch to see how the alert would have behaved.
                                    </div>
                                </div>
                            </ContentBlock>
                        </div>
                        <div class="flex flex-col gap-4 min-w-0">
                            <ContentBlock :collapsible="false">
                                <template #header_text><span class="step-badge">2</span>When to fire</template>
                                <fieldset :disabled="!canEdit" class="flex flex-col gap-4 p-4">
                                    <div class="flex flex-wrap items-end gap-3">
                                        <Field label="Fire when the value is" for="alert_threshold_type">
                                            <Select
                                                inputId="alert_threshold_type"
                                                v-model="form.threshold_type"
                                                :options="THRESHOLD_TYPES"
                                                optionLabel="label"
                                                optionValue="value"
                                                size="small"
                                                data-testid="alert-threshold-type"
                                            />
                                        </Field>
                                        <Field label="Threshold" for="alert_threshold" :error="errors.threshold">
                                            <InputNumber
                                                inputId="alert_threshold"
                                                :invalid="!!errors.threshold"
                                                v-model="form.threshold"
                                                size="small"
                                                :maxFractionDigits="6"
                                                :useGrouping="false"
                                                inputClass="w-32"
                                                data-testid="alert-threshold"
                                            />
                                        </Field>
                                        <Field
                                            v-if="isRange(form.threshold_type)"
                                            label="and"
                                            for="alert_threshold_max"
                                            :error="errors.threshold_max"
                                        >
                                            <InputNumber
                                                inputId="alert_threshold_max"
                                                :invalid="!!errors.threshold_max"
                                                v-model="form.threshold_max"
                                                size="small"
                                                :maxFractionDigits="6"
                                                :useGrouping="false"
                                                inputClass="w-32"
                                                data-testid="alert-threshold-max"
                                            />
                                        </Field>
                                        <Field label="Every" for="alert_interval">
                                            <Select
                                                inputId="alert_interval"
                                                v-model="form.interval"
                                                :options="INTERVALS"
                                                size="small"
                                                data-testid="alert-interval"
                                            />
                                        </Field>
                                    </div>
                                    <div class="flex flex-wrap items-center gap-2 text-sm">
                                        <span>Fire after</span>
                                        <InputNumber
                                            v-model="form.consecutive_windows"
                                            :min="1"
                                            :max="10"
                                            size="small"
                                            inputClass="w-14"
                                            aria-label="Breaching windows"
                                        />
                                        <span>breaching windows out of the last</span>
                                        <InputNumber
                                            v-model="form.of_windows"
                                            :min="1"
                                            :max="10"
                                            size="small"
                                            inputClass="w-14"
                                            aria-label="Out of windows"
                                        />
                                    </div>
                                    <div class="flex flex-wrap items-center gap-2 text-sm">
                                        <span>Windows start</span>
                                        <InputNumber
                                            v-model="form.schedule_offset_minutes"
                                            :min="0"
                                            :max="1439"
                                            :disabled="!!form.schedule_start_at"
                                            size="small"
                                            inputClass="w-16"
                                            aria-label="Schedule offset in minutes"
                                            data-testid="alert-schedule-offset"
                                        />
                                        <span>minutes past the interval, or from</span>
                                        <DatePicker
                                            v-model="form.schedule_start_at"
                                            showTime
                                            hourFormat="24"
                                            showButtonBar
                                            size="small"
                                            placeholder="any time"
                                            inputClass="w-40"
                                            aria-label="Schedule start"
                                            data-testid="alert-schedule-start"
                                        />
                                    </div>
                                </fieldset>
                            </ContentBlock>
                            <ContentBlock :collapsible="false">
                                <template #header_text><span class="step-badge">3</span>Name and notify</template>
                                <fieldset :disabled="!canEdit" class="flex flex-col gap-4 p-4">
                                    <Field label="Name" for="alert_name" :error="errors.name">
                                        <InputText
                                            id="alert_name"
                                            :invalid="!!errors.name"
                                            v-model="form.name"
                                            size="small"
                                            maxlength="255"
                                            placeholder="e.g. Checkout errors"
                                            data-testid="alert-name"
                                        />
                                    </Field>
                                    <Field label="Notify" for="alert_channels">
                                        <MultiSelect
                                            inputId="alert_channels"
                                            v-model="form.channels"
                                            :options="channels"
                                            optionLabel="name"
                                            optionValue="id"
                                            display="chip"
                                            :selectionLimit="10"
                                            size="small"
                                            placeholder="No channels"
                                            emptyMessage="No channels yet"
                                            data-testid="alert-channels"
                                        >
                                            <template #option="{ option }">
                                                <i :class="kindIcon(option.kind)" class="mr-2 text-surface-500" />{{
                                                    option.name
                                                }}
                                            </template>
                                        </MultiSelect>
                                        <router-link :to="{ name: 'alertChannels' }" class="text-sm table-link mt-1"
                                            >Manage channels</router-link
                                        >
                                    </Field>
                                    <Field
                                        label="Note"
                                        for="alert_note"
                                        hint="Sent with every notification, e.g. a runbook link"
                                    >
                                        <Textarea
                                            id="alert_note"
                                            v-model="form.note"
                                            rows="2"
                                            autoResize
                                            maxlength="4096"
                                        />
                                    </Field>
                                    <Field label="Tags" for="alert_tags" hint="Comma separated">
                                        <InputText
                                            id="alert_tags"
                                            v-model="form.tags"
                                            size="small"
                                            placeholder="team-payments, prod"
                                        />
                                    </Field>
                                </fieldset>
                            </ContentBlock>
                        </div>
                    </div>

                    <ContentBlock v-if="stored" :collapsible="false">
                        <template #header_text>History: {{ history.length }}</template>
                        <DataTable
                            :value="history"
                            size="small"
                            :paginator="history.length > 20"
                            :rows="20"
                            data-testid="alert-history"
                        >
                            <template #empty>
                                <div class="p-2 text-surface-500">
                                    Not evaluated yet; the scheduler runs every few seconds.
                                </div>
                            </template>
                            <Column header="Window" class="text-nowrap pl-4">
                                <template #body="{ data }">{{ windowText(data) }}</template>
                            </Column>
                            <Column v-if="grouped" field="group_key" header="Group" />
                            <Column header="State" class="w-1">
                                <template #body="{ data }">
                                    <Tag :value="STATE_LABEL[data.state]" :severity="STATE_SEVERITY[data.state]" />
                                </template>
                            </Column>
                            <Column header="Value" class="w-1 text-right">
                                <template #body="{ data }">{{ formatValue(data.value) }}</template>
                            </Column>
                            <Column header="Notified" class="w-1 text-nowrap">
                                <template #body="{ data }">
                                    <i
                                        v-if="data.notified_at"
                                        class="pi pi-send text-primary"
                                        :title="data.notified_at"
                                    />
                                </template>
                            </Column>
                            <Column field="error" header="Error" bodyClass="text-sm text-red-600 dark:text-red-400" />
                        </DataTable>
                    </ContentBlock>
                </div>
            </DataView>
        </template>
    </Content>
    <ConfirmDialog group="alert-editor" />
</template>

<script setup>
import { ref, reactive, computed, watch, onBeforeUnmount, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DateTime } from 'luxon'
import {
    Button,
    Column,
    ConfirmDialog,
    DataTable,
    DatePicker,
    InputNumber,
    InputText,
    MultiSelect,
    Select,
    Tag,
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
import PreviewChart from '@/features/alerts/PreviewChart.vue'
import { AlertService } from '@/features/alerts/service.js'
import {
    CHANNEL_KINDS,
    INTERVALS,
    STATE_LABEL,
    STATE_SEVERITY,
    THRESHOLD_TYPES,
    describeSeries,
    isRange,
    responseProblem,
} from '@/features/alerts/useAlerts.js'
import { useGetSources } from '@/composables/sources/useSourceService'
import { DashboardService } from '@/sdk/services/dashboard'
import { AGGS, QUANTILE_LEVELS, countOnlyKind, isLogTile, isNumericType } from '@/utils/dashboards'

const Field = (props, { slots }) =>
    h('div', { class: 'flex flex-col gap-1 min-w-0' }, [
        h('label', { for: props.for, class: 'font-medium text-sm' }, props.label),
        slots.default?.(),
        props.error
            ? h('small', { class: 'text-red-600 dark:text-red-400', 'data-testid': 'alert-field-error' }, props.error)
            : props.hint
              ? h('span', { class: 'text-xs text-surface-500 dark:text-surface-400' }, props.hint)
              : null,
    ])
Field.props = ['label', 'for', 'hint', 'error']

const KINDS = [
    { value: 'search', label: 'Search', hint: 'Rows matching a query in a source', icon: 'pi pi-search' },
    { value: 'tile', label: 'Dashboard chart', hint: 'The value of a dashboard tile', icon: 'pi pi-th-large' },
]

const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const srv = new AlertService()
const dashboardSrv = new DashboardService()
const { sources } = useGetSources()

const alertId = computed(() => route.params.alertId)
const isNew = computed(() => !alertId.value)
const stored = ref(null)
const history = ref([])
const loading = ref(!!alertId.value)
const loadError = ref('')
const saving = ref(false)
const problem = ref('')
const attempted = ref(false)
const serverErrors = ref({})
const channels = ref([])
const dashboards = ref([])
const dashboard = ref(null)

const form = reactive({
    name: '',
    kind: 'search',
    source: '',
    query: '',
    raw_query: '',
    context_columns: {},
    group_by: null,
    agg: 'count',
    column: null,
    level: 0.95,
    dashboard: null,
    tile_id: null,
    series_index: 0,
    interval: '5m',
    threshold_type: 'above',
    threshold: 1,
    threshold_max: null,
    consecutive_windows: 1,
    of_windows: 1,
    channels: [],
    note: '',
    tags: '',
    schedule_offset_minutes: 0,
    schedule_start_at: null,
})

const canEdit = computed(() => isNew.value || !!stored.value?.can_edit)
const source = computed(() => (sources.value || []).find((s) => s.slug === form.source) || null)
const aggOptions = computed(() =>
    AGGS.map((a) => ({ value: a, label: a, disabled: countOnlyKind(source.value?.kind) && a !== 'count' })),
)
const columnOptions = computed(() => {
    if (!source.value) return form.column ? [form.column] : []
    return Object.entries(source.value.columns || {})
        .filter(([, col]) => form.agg === 'uniq' || isNumericType(col.type))
        .map(([name]) => name)
})
const contextText = computed(() =>
    Object.entries(form.context_columns || {})
        .map(([k, v]) => `${k}=${[].concat(v).join('|')}`)
        .join(', '),
)
// A multi-column group by (e.g. from a chart) is kept as one more option, so the Select shows it.
const groupOptions = computed(() => {
    const names = Object.entries(source.value?.columns || {})
        .filter(([, col]) => col.group_by !== false)
        .map(([name]) => name)
    return form.group_by && !names.includes(form.group_by) ? [form.group_by, ...names] : names
})
const queryTiles = computed(() =>
    (dashboard.value?.data?.tiles || []).filter(
        (t) => !['text', 'sql'].includes(t.chart?.display) && !isLogTile(t.chart?.display),
    ),
)
const tileOptions = computed(() =>
    queryTiles.value.map((t) => ({ id: t.id, label: t.title || `${t.chart.source} (${t.id})` })),
)
const tile = computed(() => queryTiles.value.find((t) => t.id === form.tile_id) || null)
const tileSeries = computed(() =>
    (tile.value?.chart.series || []).map((s, index) => ({ index, label: describeSeries(s) })),
)
const grouped = computed(() => (form.kind === 'tile' ? !!tile.value?.chart.group_by : !!form.group_by))
// Required fields, shown inline once a save was tried; server field errors come on top.
const missing = computed(() => {
    const e = {}
    if (form.kind === 'search') {
        if (!form.source) e.source = 'Choose a source'
        if (form.agg !== 'count' && !form.column) e.column = 'Choose a column'
    } else if (!form.dashboard) e.dashboard = 'Choose a dashboard'
    else if (!form.tile_id) e.tile_id = 'Choose a chart'
    if (form.threshold === null || form.threshold === undefined) e.threshold = 'Enter a threshold'
    if (isRange(form.threshold_type) && (form.threshold_max === null || form.threshold_max === undefined))
        e.threshold_max = 'Enter the upper bound'
    return e
})
const errors = computed(() => ({ ...serverErrors.value, ...(attempted.value ? missing.value : {}) }))
const kindIcon = (kind) => CHANNEL_KINDS.find((k) => k.value === kind)?.icon || 'pi pi-send'

const series = () => {
    const s = { agg: form.agg }
    if (form.agg !== 'count') s.column = form.column
    if (form.agg === 'quantile') s.level = form.level
    return s
}

const payload = () => {
    const body = {
        name: form.name.trim() || 'Untitled alert',
        kind: form.kind,
        interval: form.interval,
        threshold_type: form.threshold_type,
        threshold: form.threshold ?? 0,
        threshold_max: isRange(form.threshold_type) ? form.threshold_max : null,
        consecutive_windows: form.consecutive_windows || 1,
        of_windows: Math.max(form.of_windows || 1, form.consecutive_windows || 1),
        channels: form.channels,
        schedule_offset_minutes: form.schedule_start_at ? 0 : form.schedule_offset_minutes || 0,
        schedule_start_at: form.schedule_start_at ? form.schedule_start_at.toISOString() : null,
        note: form.note,
        tags: form.tags
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean),
    }
    if (form.kind === 'search') {
        Object.assign(body, {
            source: form.source,
            query: form.query,
            raw_query: source.value?.supportRawQuery ? form.raw_query : '',
            context_columns: form.context_columns || {},
            group_by: form.group_by || '',
            series: series(),
        })
    } else {
        Object.assign(body, { dashboard: form.dashboard, tile_id: form.tile_id, series_index: form.series_index })
    }
    return body
}

const fill = (a) => {
    Object.assign(form, {
        name: a.name,
        kind: a.kind,
        source: a.kind === 'search' ? a.source : '',
        query: a.query,
        raw_query: a.raw_query,
        context_columns: a.context_columns || {},
        group_by: a.group_by || null,
        agg: a.series?.agg || 'count',
        column: a.series?.column || null,
        level: a.series?.level || 0.95,
        dashboard: a.dashboard?.slug || null,
        tile_id: a.tile_id || null,
        series_index: a.series_index,
        interval: a.interval,
        threshold_type: a.threshold_type,
        threshold: a.threshold,
        threshold_max: a.threshold_max,
        consecutive_windows: a.consecutive_windows,
        of_windows: a.of_windows,
        channels: a.channels,
        schedule_offset_minutes: a.schedule_offset_minutes || 0,
        schedule_start_at: a.schedule_start_at ? new Date(a.schedule_start_at) : null,
        note: a.note,
        tags: (a.tags || []).join(', '),
    })
}

const loadAlert = async () => {
    const [response, hist] = await Promise.all([srv.get(alertId.value), srv.history(alertId.value)])
    if (response.result) {
        stored.value = response.data
        fill(response.data)
        history.value = hist.data || []
    }
    loadError.value = response.errors.join(', ')
    loading.value = false
}

const parseContext = (text) => {
    try {
        const value = JSON.parse(text || '{}')
        return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
    } catch {
        return {}
    }
}

const init = async () => {
    srv.channels().then((r) => (channels.value = r.data || []))
    dashboardSrv.getDashboards().then((r) => (dashboards.value = r.data || []))
    if (alertId.value) return loadAlert()
    const q = route.query
    if (q.dashboard) {
        Object.assign(form, { kind: 'tile', dashboard: q.dashboard, tile_id: q.tile || null })
        if (q.title) form.name = q.title
    } else if (q.source) {
        Object.assign(form, {
            source: q.source,
            query: q.query || '',
            raw_query: q.raw_query || '',
            context_columns: parseContext(q.context_columns),
            group_by: q.group_by || null,
            agg: q.agg || 'count',
            column: q.column || null,
            level: Number(q.level) || 0.95,
        })
        if (q.title) form.name = q.title
    }
}
init()

watch(
    () => form.dashboard,
    async (slug) => {
        dashboard.value = null
        if (!slug) return
        const response = await dashboardSrv.getDashboard(slug)
        if (response.result && form.dashboard === slug) {
            dashboard.value = response.data
            if (!tile.value && queryTiles.value.length === 1) form.tile_id = queryTiles.value[0].id
        }
    },
    { immediate: true },
)
// Until the sources load, or when the viewer cannot see the source, the stored column is kept.
watch(
    () => [form.agg, source.value],
    () => {
        if (form.agg !== 'count' && source.value && !columnOptions.value.includes(form.column))
            form.column = columnOptions.value[0] || null
    },
)

// Preview: re-evaluated shortly after any change, stale requests aborted.
const previewData = ref(null)
const previewError = ref('')
const previewLoading = ref(false)
let previewTimer = null
let previewAbort = null
const ready = computed(() =>
    form.kind === 'search'
        ? !!form.source && (form.agg === 'count' || !!form.column)
        : !!form.dashboard && !!form.tile_id,
)
const runPreview = async () => {
    if (!ready.value) return
    previewAbort?.abort()
    previewAbort = new AbortController()
    const signal = previewAbort.signal
    previewLoading.value = true
    const response = await srv.preview(payload(), signal)
    if (signal.aborted) return
    previewLoading.value = false
    if (response.result) {
        previewData.value = response.data
        previewError.value = ''
    } else {
        previewData.value = null
        previewError.value = responseProblem(response)
    }
}
watch(
    () => JSON.stringify([ready.value, payload(), loading.value]),
    () => {
        if (loading.value) return
        clearTimeout(previewTimer)
        previewTimer = setTimeout(runPreview, 500)
    },
    { immediate: true },
)
onBeforeUnmount(() => {
    clearTimeout(previewTimer)
    previewAbort?.abort()
})
const previewSummary = computed(() => {
    if (!previewData.value) return ''
    const windows = new Set()
    previewData.value.series.forEach((s) => s.would_fire.forEach((f, i) => f && windows.add(i)))
    if (!windows.size) return 'Would not have fired'
    return `Would have fired in ${windows.size} of ${previewData.value.windows.length} windows`
})

const save = async () => {
    if (saving.value) return
    attempted.value = true
    serverErrors.value = {}
    const first = Object.keys(missing.value)[0]
    if (first) {
        problem.value = 'Fill in the highlighted fields.'
        document.getElementById(first === 'tile_id' ? 'alert_tile' : `alert_${first}`)?.focus()
        return
    }
    saving.value = true
    problem.value = ''
    const response = isNew.value ? await srv.create(payload()) : await srv.update(alertId.value, payload())
    saving.value = false
    if (!response.result) {
        problem.value = responseProblem(response)
        serverErrors.value = Object.fromEntries(
            Object.entries(response.validation?.fields || {}).map(([k, v]) => [k, [].concat(v).join(' ')]),
        )
        return
    }
    response.sendToastMessages(toast)
    stored.value = response.data
    if (isNew.value) router.replace({ name: 'alert', params: { alertId: response.data.id } })
}

watch(alertId, (id, old) => {
    if (id && id !== old && (!stored.value || String(stored.value.id) !== String(id))) {
        loading.value = true
        loadAlert()
    } else if (id) {
        srv.history(id).then((r) => (history.value = r.data || []))
    }
})

const askDelete = () =>
    confirm.require({
        group: 'alert-editor',
        header: 'Delete alert',
        message: `Delete "${stored.value.name}" and its history?`,
        acceptProps: { label: 'Delete', severity: 'danger', size: 'small' },
        rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true, size: 'small' },
        accept: async () => {
            const response = await srv.remove(stored.value.id)
            response.sendToast(toast)
            if (response.result) router.push({ name: 'alerts' })
        },
    })

const relative = (iso) => DateTime.fromISO(iso).toRelative()
const windowText = (row) =>
    `${DateTime.fromMillis(row.window_start).toFormat('yyyy-MM-dd HH:mm')} – ${DateTime.fromMillis(row.window_end).toFormat('HH:mm')}`
const formatValue = (v) =>
    v === null || v === undefined ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 4 })
</script>

<style scoped>
.step-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    margin-right: 0.6rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--p-primary-contrast-color);
    background: var(--p-primary-color);
}
</style>
