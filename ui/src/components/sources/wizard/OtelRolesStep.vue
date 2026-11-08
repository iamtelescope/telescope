<template>
    <div class="flex flex-col" data-testid="otel-roles-step">
        <div class="flex flex-col gap-4">
            <div class="flex items-center justify-between gap-3">
                <div class="flex items-center gap-2">
                    <ToggleSwitch v-model="enabled" inputId="otelEnabled" />
                    <label for="otelEnabled" class="font-medium">Use OpenTelemetry roles</label>
                </div>
                <Button
                    label="Detect again"
                    icon="pi pi-refresh"
                    severity="secondary"
                    size="small"
                    text
                    :loading="detecting"
                    @click="emit('detect')"
                />
            </div>
            <Message v-if="detectMessage" :severity="detectMessage.severity" size="small" data-testid="otel-detect-msg">
                {{ detectMessage.text }}
            </Message>

            <template v-if="enabled">
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label for="otelSignal" class="font-medium block mb-2">Signal *</label>
                        <Select
                            id="otelSignal"
                            v-model="signal"
                            :options="signalOptions"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                        />
                    </div>
                    <div v-if="signal === 'traces'">
                        <label for="otelDurationPrecision" class="font-medium block mb-2">Duration unit</label>
                        <Select
                            id="otelDurationPrecision"
                            v-model="roles.duration_precision"
                            :options="precisionOptions"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                        />
                    </div>
                </div>

                <div>
                    <div class="font-medium text-lg mb-2">Column roles</div>
                    <div class="grid grid-cols-2 gap-3">
                        <div v-for="role in columnRoles" :key="role.key" :data-testid="`otel-role-${role.key}`">
                            <label :for="`otelRole-${role.key}`" class="block mb-2">
                                <span class="font-medium">{{ role.label }}</span>
                                <span class="ml-2 text-sm font-mono text-gray-500 dark:text-neutral-400">
                                    {{ role.key }}
                                </span>
                            </label>
                            <Select
                                :id="`otelRole-${role.key}`"
                                v-model="roles[role.key]"
                                :options="columnOptions(role)"
                                optionLabel="name"
                                optionValue="name"
                                showClear
                                filter
                                class="w-full"
                                :invalid="!!roleErrors[role.key]"
                                placeholder="Not set"
                            />
                            <Message v-if="roleErrors[role.key]" severity="error" size="small" variant="simple">
                                {{ roleErrors[role.key] }}
                            </Message>
                        </div>
                    </div>
                </div>

                <div v-if="signal === 'metrics'">
                    <div class="font-medium text-lg mb-2">Metric tables</div>
                    <div class="grid grid-cols-2 gap-3">
                        <div v-for="kind in metricKinds" :key="kind.key">
                            <label :for="`otelMetric-${kind.key}`" class="font-medium block mb-2">{{
                                kind.label
                            }}</label>
                            <InputText
                                :id="`otelMetric-${kind.key}`"
                                v-model="metricTables[kind.key]"
                                class="w-full font-mono"
                                placeholder="Not set"
                                fluid
                            />
                        </div>
                    </div>
                </div>

                <div>
                    <div class="font-medium text-lg mb-2">Linked sources</div>
                    <div class="grid grid-cols-2 gap-3">
                        <div v-for="target in linkTargets" :key="target">
                            <label :for="`otelLink-${target}`" class="font-medium block mb-2">
                                {{ signalLabel(target) }} source
                            </label>
                            <Select
                                :id="`otelLink-${target}`"
                                v-model="links[target]"
                                :options="linkOptions(target)"
                                optionLabel="label"
                                optionValue="slug"
                                showClear
                                class="w-full"
                                placeholder="None"
                            />
                        </div>
                    </div>
                </div>
            </template>
        </div>
        <div class="flex justify-between mt-6 pt-4 border-t border-surface-200 dark:border-surface-700">
            <Button label="Back" severity="secondary" size="small" icon="pi pi-arrow-left" @click="emit('prev')" />
            <Button label="Next" icon="pi pi-arrow-right" size="small" iconPos="right" @click="handleNext" />
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, toRaw } from 'vue'
import { Button, InputText, Select, Message, ToggleSwitch } from 'primevue'

const props = defineProps(['modelValue', 'columnsSetupData', 'sources', 'currentSlug', 'detecting', 'detectMessage'])
const emit = defineEmits(['prev', 'next', 'detect', 'update:modelValue'])

// Role lists mirror backend/telescope_otel/roles.py.
const ROLES = {
    logs: [
        ['timestamp', 'Timestamp', 'time'],
        ['body', 'Body'],
        ['severity_text', 'Severity text'],
        ['severity_number', 'Severity number'],
        ['service', 'Service name'],
        ['trace_id', 'Trace ID'],
        ['span_id', 'Span ID'],
        ['resource_attrs', 'Resource attributes', 'map'],
        ['attrs', 'Log attributes', 'map'],
        ['scope', 'Scope name'],
    ],
    traces: [
        ['timestamp', 'Timestamp', 'time'],
        ['trace_id', 'Trace ID'],
        ['span_id', 'Span ID'],
        ['parent_span_id', 'Parent span ID'],
        ['span_name', 'Span name'],
        ['span_kind', 'Span kind'],
        ['duration', 'Duration'],
        ['status_code', 'Status code'],
        ['status_message', 'Status message'],
        ['service', 'Service name'],
        ['resource_attrs', 'Resource attributes', 'map'],
        ['attrs', 'Span attributes', 'map'],
        ['events', 'Span events', 'nested'],
        ['links', 'Span links', 'nested'],
    ],
    metrics: [
        ['timestamp', 'Timestamp', 'time'],
        ['start_time', 'Start time', 'time'],
        ['metric_name', 'Metric name'],
        ['metric_unit', 'Metric unit'],
        ['value', 'Value'],
        ['service', 'Service name'],
        ['resource_attrs', 'Resource attributes', 'map'],
        ['attrs', 'Attributes', 'map'],
        ['scope', 'Scope name'],
    ],
}
const signalOptions = [
    { value: 'logs', label: 'Logs' },
    { value: 'traces', label: 'Traces' },
    { value: 'metrics', label: 'Metrics' },
]
const precisionOptions = [
    { value: 9, label: 'Nanoseconds' },
    { value: 6, label: 'Microseconds' },
    { value: 3, label: 'Milliseconds' },
    { value: 0, label: 'Seconds' },
]
const metricKinds = [
    { key: 'gauge', label: 'Gauge' },
    { key: 'sum', label: 'Sum' },
    { key: 'histogram', label: 'Histogram' },
    { key: 'exponential_histogram', label: 'Exponential histogram' },
    { key: 'summary', label: 'Summary' },
]

let lastEmitted = null
const initial = props.modelValue || {}
const enabled = ref(initial.enabled ?? false)
const signal = ref(initial.signal || 'logs')
const roles = ref({ ...(initial.roles || {}) })
const links = ref({ ...(initial.links || {}) })
const metricTables = ref({ ...(initial.metric_tables || {}) })

watch(
    () => props.modelValue,
    (value) => {
        if (!value || toRaw(value) === lastEmitted) return
        enabled.value = value.enabled ?? false
        signal.value = value.signal || 'logs'
        roles.value = { ...(value.roles || {}) }
        links.value = { ...(value.links || {}) }
        metricTables.value = { ...(value.metric_tables || {}) }
    },
)

const signalLabel = (value) => signalOptions.find((s) => s.value === value)?.label || value
const columnRoles = computed(() => ROLES[signal.value].map(([key, label, kind]) => ({ key, label, kind })))
const linkTargets = computed(() => signalOptions.map((s) => s.value).filter((s) => s !== signal.value))
const columns = computed(() => (props.columnsSetupData?.columns || []).filter((c) => c.name))

const nestedNames = computed(() => {
    const names = new Set()
    for (const c of columns.value) {
        const dot = c.name.indexOf('.')
        if (dot > 0 && c.type?.startsWith('Array(')) names.add(c.name.slice(0, dot))
    }
    return [...names].map((name) => ({ name }))
})

const columnOptions = (role) => {
    if (role.kind === 'nested') return nestedNames.value
    if (role.kind === 'map') return columns.value.filter((c) => c.type?.includes('Map('))
    if (role.kind === 'time') return columns.value.filter((c) => /datetime|int64/i.test(c.type || ''))
    return columns.value
}

const columnExists = (name) => columns.value.some((c) => c.name === name || c.name.startsWith(name + '.'))

const roleErrors = computed(() => {
    const errors = {}
    for (const role of columnRoles.value) {
        const value = roles.value[role.key]
        if (value && !columnExists(value)) errors[role.key] = `column ${value} not found`
    }
    return errors
})

const linkOptions = (target) =>
    (props.sources || [])
        .filter((s) => s.otelSignal === target && s.slug !== props.currentSlug)
        .map((s) => ({ slug: s.slug, label: `${s.name} (${s.slug})` }))

const pickSet = (obj, keys) =>
    Object.fromEntries(keys.filter((k) => obj[k] !== '' && obj[k] != null).map((k) => [k, obj[k]]))

const emitValue = () => {
    const roleKeys = columnRoles.value.map((r) => r.key)
    if (signal.value === 'traces') roleKeys.push('duration_precision')
    lastEmitted = {
        enabled: enabled.value,
        signal: signal.value,
        roles: pickSet(roles.value, roleKeys),
        links: pickSet(links.value, linkTargets.value),
        metric_tables:
            signal.value === 'metrics'
                ? pickSet(
                      metricTables.value,
                      metricKinds.map((k) => k.key),
                  )
                : null,
        // Keep the row panel's highlighted keys (P3.4), which this step does not edit.
        ...(initial.highlighted ? { highlighted: initial.highlighted } : {}),
    }
    emit('update:modelValue', lastEmitted)
}
watch([enabled, signal, roles, links, metricTables], emitValue, { deep: true })

const handleNext = () => {
    if (enabled.value && Object.keys(roleErrors.value).length > 0) return
    emitValue()
    emit('next')
}
</script>
