<template>
    <div
        class="flex flex-col h-full w-full overflow-y-auto border-t-4"
        :style="{ borderColor: getColor(row.severity) }"
    >
        <div class="flex flex-col">
            <div
                class="sticky top-0 z-20 flex items-center gap-2 px-4 py-2 border-b border-neutral-200 dark:border-neutral-700 bg-surface-0 dark:bg-surface-900"
                data-testid="row-panel-header"
            >
                <Tag
                    v-if="source.severityColumn.length != 0"
                    :style="{
                        backgroundColor: getColor(row.severity),
                        color: getContrastColor(getColor(row.severity)),
                    }"
                    class="text-bold"
                    >{{ source.severityColumn }}: {{ row.severity }}
                </Tag>
                <span class="font-mono text-sm" data-testid="row-panel-time">{{ dateTimeString }}</span>
                <span class="flex-1"></span>
                <span v-if="count" class="text-xs text-neutral-500 dark:text-neutral-400 tabular-nums">
                    {{ index + 1 }} of {{ count }}
                </span>
                <template v-if="count">
                    <Button
                        icon="pi pi-chevron-up"
                        text
                        rounded
                        size="small"
                        severity="secondary"
                        aria-label="Previous row"
                        v-tooltip.bottom="'Previous row (Up or k)'"
                        :disabled="index <= 0"
                        @click="emit('prev')"
                        data-testid="row-prev"
                    />
                    <Button
                        icon="pi pi-chevron-down"
                        text
                        rounded
                        size="small"
                        severity="secondary"
                        aria-label="Next row"
                        v-tooltip.bottom="'Next row (Down or j)'"
                        :disabled="index >= count - 1"
                        @click="emit('next')"
                        data-testid="row-next"
                    />
                </template>
                <Button
                    icon="pi pi-times"
                    text
                    rounded
                    size="small"
                    severity="secondary"
                    aria-label="Close"
                    v-tooltip.bottom="'Close (Esc)'"
                    @click="emit('close')"
                    data-testid="row-close"
                />
            </div>
            <DetailsExtras
                v-if="detailsExtrasAvailable(source, row)"
                :source="source"
                :row="row"
                :timeZone="timeZone"
            />
            <Tabs :value="overviewAvailable(source, row) ? 'overview' : '0'">
                <TabList>
                    <Tab v-if="overviewAvailable(source, row)" value="overview">OVERVIEW</Tab>
                    <Tab value="0">FLATTENED</Tab>
                    <Tab value="1">JSON</Tab>
                    <Tab v-if="contextAvailable(source, row)" value="context">CONTEXT</Tab>
                    <Tab v-if="traceAvailable(source, row)" value="trace">TRACE</Tab>
                    <Tab v-if="infraAvailable(source, row)" value="infra">INFRASTRUCTURE</Tab>
                </TabList>
                <TabPanels :pt="{ root: { className: 'p-0' } }">
                    <TabPanel v-if="overviewAvailable(source, row)" value="overview">
                        <OverviewTab :source="source" :row="row" :timeZone="timeZone" />
                    </TabPanel>
                    <TabPanel value="0">
                        <DataTable :value="flattenRow" :row-hover="true" removableSort size="small">
                            <Column field="path" header="Field" sortable class="font-medium text-nowrap" :pt="TOP">
                                <template #body="slotProps">
                                    <div class="flex items-center gap-1">
                                        <Button
                                            size="small"
                                            text
                                            severity="secondary"
                                            :label="FlyQLOperator.EQUALS"
                                            :aria-label="`Filter ${formatPathForDisplay(slotProps.data.path)} equals this value`"
                                            v-tooltip.top="'Filter for this value'"
                                            @click="
                                                updateQuery(
                                                    FlyQLOperator.EQUALS,
                                                    formatPathForQuery(slotProps.data.path),
                                                    slotProps.data.value,
                                                )
                                            "
                                        ></Button>
                                        <Button
                                            size="small"
                                            text
                                            severity="secondary"
                                            :label="FlyQLOperator.NOT_EQUALS"
                                            :aria-label="`Exclude ${formatPathForDisplay(slotProps.data.path)} with this value`"
                                            v-tooltip.top="'Exclude this value'"
                                            @click="
                                                updateQuery(
                                                    FlyQLOperator.NOT_EQUALS,
                                                    formatPathForQuery(slotProps.data.path),
                                                    slotProps.data.value,
                                                )
                                            "
                                        ></Button>
                                        <Button
                                            v-if="explorerColumns"
                                            size="small"
                                            text
                                            :severity="isShown(slotProps.data.path) ? 'info' : 'secondary'"
                                            :icon="
                                                isShown(slotProps.data.path)
                                                    ? 'pi pi-minus-circle'
                                                    : 'pi pi-plus-circle'
                                            "
                                            :aria-label="
                                                (isShown(slotProps.data.path) ? 'Remove column ' : 'Add column ') +
                                                formatPathForDisplay(slotProps.data.path)
                                            "
                                            v-tooltip.top="
                                                isShown(slotProps.data.path) ? 'Remove column' : 'Add as column'
                                            "
                                            @click="explorerColumns.toggle(formatPathForQuery(slotProps.data.path))"
                                            :data-testid="`row-column-toggle-${formatPathForDisplay(slotProps.data.path)}`"
                                        ></Button>
                                        <span class="font-mono pl-1">{{
                                            formatPathForDisplay(slotProps.data.path)
                                        }}</span>
                                    </div>
                                </template>
                            </Column>
                            <Column field="value" header="Value" sortable :pt="TOP">
                                <template #body="slotProps">
                                    <div class="flex items-start gap-1 group/value">
                                        <pre
                                            v-if="slotProps.data.value !== null && slotProps.data.value !== ''"
                                            class="flex-1 py-1.5"
                                            style="white-space: pre-wrap; overflow-wrap: anywhere"
                                            data-testid="row-field-value"
                                            >{{ slotProps.data.value }}</pre
                                        >
                                        <span v-else class="flex-1 py-1.5">&ndash;</span>
                                        <Button
                                            v-if="slotProps.data.value !== null && slotProps.data.value !== ''"
                                            icon="pi pi-copy"
                                            size="small"
                                            text
                                            severity="secondary"
                                            class="invisible group-hover/value:visible focus:visible"
                                            :aria-label="`Copy ${formatPathForDisplay(slotProps.data.path)}`"
                                            @click="copyValue(String(slotProps.data.value))"
                                            data-testid="row-value-copy"
                                        />
                                    </div>
                                </template>
                            </Column>
                        </DataTable>
                    </TabPanel>
                    <TabPanel value="1">
                        <div class="p-4">
                            <pre style="white-space: pre-wrap; overflow-wrap: anywhere">{{ row }}</pre>
                        </div>
                    </TabPanel>
                    <TabPanel v-if="contextAvailable(source, row)" value="context">
                        <ContextTab :source="source" :row="row" :timeZone="timeZone" />
                    </TabPanel>
                    <TabPanel v-if="traceAvailable(source, row)" value="trace">
                        <TraceTab :source="source" :row="row" :timeZone="timeZone" />
                    </TabPanel>
                    <TabPanel v-if="infraAvailable(source, row)" value="infra">
                        <InfraTab :source="source" :row="row" :timeZone="timeZone" />
                    </TabPanel>
                </TabPanels>
            </Tabs>
        </div>
    </div>
</template>
<script setup>
import { computed, inject } from 'vue'
import { useClipboard } from '@vueuse/core'
import { useToast } from 'primevue'

import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import { Operator as FlyQLOperator } from 'flyql'
import { useSourceControlsStore } from '@/stores/sourceControls'

import { getColor, getContrastColor } from '@/utils/colors.js'
import Tag from 'primevue/tag'
import { DateTime } from 'luxon'
import ContextTab, { available as contextAvailable } from '@/components/explorer/results/tabs/ContextTab.vue'
import TraceTab, { available as traceAvailable } from '@/components/explorer/results/tabs/TraceTab.vue'
import OverviewTab, { available as overviewAvailable } from '@/components/explorer/results/sections/OverviewTab.vue'
import InfraTab, { available as infraAvailable } from '@/components/explorer/results/sections/InfraTab.vue'
import DetailsExtras, {
    available as detailsExtrasAvailable,
} from '@/components/explorer/results/tabs/DetailsExtras.vue'

const sourceControlsStore = useSourceControlsStore()

const props = defineProps(['source', 'row', 'timeZone', 'index', 'count'])
const emit = defineEmits(['prev', 'next', 'close'])
// Provided by the explorer only: dashboard tiles have no columns to edit.
const explorerColumns = inject('explorerColumns', null)
const toast = useToast()
const { copy } = useClipboard({ legacy: true })

// Field and value cells start at the top, so a value's first line sits level with its field name.
const TOP = { bodyCell: { style: 'vertical-align: top' } }

const isShown = (path) => explorerColumns?.has(formatPathForQuery(path))

const copyValue = async (text) => {
    try {
        await copy(text)
        toast.add({ severity: 'success', summary: 'Copied', detail: 'Value copied to clipboard', life: 2000 })
    } catch {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to copy to clipboard', life: 6000 })
    }
}

const dateTimeString = computed(() => {
    const dateTime = DateTime.fromMillis(props.row.time.unixtime, { zone: props.timeZone }).toFormat(
        'yyyy-MM-dd HH:mm:ss',
    )
    // Milliseconds, as in the table, unless the time has sub-millisecond digits.
    const us = String(props.row.time.microseconds ?? '').padStart(6, '0')
    return `${dateTime}.${us.endsWith('000') ? us.slice(0, 3) : us} ${props.timeZone}`
})

const formatPathForQuery = (pathArray) => {
    return pathArray
        .map((segment) => {
            if (segment.includes('.')) {
                return `"${segment.replace(/"/g, '\\"')}"`
            }
            return segment
        })
        .join('.')
}

const formatPathForDisplay = (pathArray) => {
    return pathArray.join('.')
}

const updateQuery = (operator, field, value) => {
    sourceControlsStore.addQueryExpression(field, operator, value)
}

function flat_json(result, value, path) {
    if (typeof value === 'object') {
        if (value) {
            for (const [k, v] of Object.entries(value)) {
                let p = [...path]
                p.push(k)
                flat_json(result, v, p)
            }
        } else {
            if (value === null) {
                result.push({ path: path, value: value })
            }
        }
    } else {
        result.push({ path: path, value: value })
    }
    return result
}

const flattenRow = computed(() => {
    return flat_json([], props.row.data, [])
})
</script>
