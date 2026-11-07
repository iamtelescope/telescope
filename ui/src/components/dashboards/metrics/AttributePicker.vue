<template>
    <div class="flex flex-col gap-2" data-testid="metric-attributes">
        <Select
            v-model="key"
            :options="keys.data.value"
            optionLabel="path"
            optionValue="path"
            filter
            size="small"
            :disabled="!metric?.name"
            :placeholder="keys.error.value || 'Attribute'"
            emptyMessage="No attributes"
            data-testid="metric-attribute-key"
        >
            <template #option="{ option }">
                <span class="font-mono text-sm">
                    <span class="text-surface-500">{{ option.column }}.</span>{{ option.key }}
                </span>
            </template>
        </Select>
        <div v-if="key" class="flex flex-col gap-1">
            <div class="flex items-center justify-between">
                <span class="text-sm text-surface-500">Values</span>
                <Button
                    label="Group by"
                    icon="pi pi-objects-column"
                    text
                    size="small"
                    class="py-0"
                    data-testid="metric-attribute-group"
                    @click="emit('group', key)"
                />
            </div>
            <span v-if="values.loading.value" class="text-sm text-surface-500">Loading…</span>
            <div v-else class="flex flex-wrap gap-1 max-h-40 overflow-y-auto">
                <button
                    v-for="value in values.data.value"
                    :key="value"
                    type="button"
                    class="px-2 py-0.5 rounded border border-surface-200 dark:border-surface-700 text-xs font-mono hover:bg-surface-100 dark:hover:bg-surface-800"
                    v-tooltip.top="'Filter on this value'"
                    data-testid="metric-attribute-value"
                    @click="emit('filter', attributeFilter(key, value))"
                >
                    {{ value === '' ? '(empty)' : value }}
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button, Select } from 'primevue'

import { attributeFilter, useAttributeValues, useMetricAttributes } from '@/components/dashboards/metrics/metrics'

// Browse a metric's attribute keys and values; emits a group-by path or a FlyQL filter.
const props = defineProps(['source', 'range', 'metric'])
const emit = defineEmits(['group', 'filter'])

const keys = useMetricAttributes()
const values = useAttributeValues()
const key = ref(null)

const body = (extra = {}) => ({
    from: props.range.from,
    to: props.range.to,
    name: props.metric.name,
    type: props.metric.type,
    ...extra,
})

watch(
    () => [props.source, props.metric?.name, props.metric?.type, props.range?.from, props.range?.to],
    () => {
        if (props.source && props.metric?.name) keys.load(props.source, body())
    },
    { immediate: true },
)
watch(
    () => [key.value, keys.data.value],
    () => {
        if (key.value && !keys.data.value.some((k) => k.path === key.value)) key.value = null
        if (key.value) values.load(props.source, body({ key: key.value }))
    },
)
</script>
