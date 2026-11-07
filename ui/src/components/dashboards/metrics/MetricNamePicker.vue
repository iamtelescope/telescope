<template>
    <Select
        :modelValue="selected"
        :options="options"
        optionLabel="name"
        optionValue="key"
        filter
        filterFields="name"
        size="small"
        :placeholder="names.error.value || (names.loading.value ? 'Loading metrics…' : 'Metric')"
        :invalid="invalid || !!names.error.value"
        :emptyMessage="names.loading.value ? 'Loading…' : 'No metrics in this time range'"
        data-testid="metric-name"
        @update:modelValue="onChange"
    >
        <template #option="{ option }">
            <div class="flex items-center justify-between gap-3 w-full min-w-0" :title="option.description">
                <span class="truncate font-mono text-sm">{{ option.name }}</span>
                <Tag :value="METRIC_TYPE_LABELS[option.type]" severity="secondary" class="shrink-0 text-xs" />
            </div>
        </template>
    </Select>
</template>

<script setup>
import { computed, watch } from 'vue'
import { Select, Tag } from 'primevue'

import { METRIC_TYPE_LABELS, useMetricNames } from '@/components/dashboards/metrics/metrics'

// `modelValue` is {name, type}; the choice also reports the metric's unit.
const props = defineProps(['source', 'range', 'modelValue', 'invalid'])
const emit = defineEmits(['update:modelValue'])

const names = useMetricNames()
const keyOf = (m) => `${m.name}|${m.type}`
const options = computed(() => names.data.value.map((m) => ({ ...m, key: keyOf(m) })))
const selected = computed(() => (props.modelValue?.name ? keyOf(props.modelValue) : null))

const onChange = (key) => {
    const metric = options.value.find((m) => m.key === key)
    if (metric) emit('update:modelValue', { name: metric.name, type: metric.type, unit: metric.unit })
}

watch(
    () => [props.source, props.range?.from, props.range?.to],
    () => props.source && names.load(props.source, { from: props.range.from, to: props.range.to }),
    { immediate: true },
)
</script>
