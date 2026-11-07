<template>
    <div v-if="variables.length" class="flex flex-wrap items-center gap-2 mt-2" data-testid="variable-bar">
        <div
            v-for="v in variables"
            :key="v.name"
            class="var-control flex items-stretch min-w-0"
            :class="{ 'var-control--missing': missing.includes(v.name) }"
            :data-testid="`variable-${v.name}`"
        >
            <label
                :for="`var-input-${v.name}`"
                class="var-label flex items-center px-2.5 text-sm font-medium whitespace-nowrap"
                :title="`$${v.name}`"
            >
                {{ v.label || v.name }}<span v-if="v.required" class="ml-0.5 text-red-500" aria-hidden="true">*</span>
            </label>
            <MultiSelect
                v-if="v.type !== 'text' && v.multi"
                :inputId="`var-input-${v.name}`"
                :modelValue="values[v.name]"
                :options="optionsFor(v)"
                :loading="loading[v.name]"
                filter
                autoFilterFocus
                resetFilterOnHide
                :maxSelectedLabels="2"
                selectedItemsLabel="{0} selected"
                placeholder="Any"
                size="small"
                class="var-input"
                :aria-label="v.label || v.name"
                @show="loadOptions(v)"
                @update:modelValue="(value) => emit('change', v, value)"
            />
            <Select
                v-else-if="v.type !== 'text'"
                :inputId="`var-input-${v.name}`"
                :modelValue="values[v.name] || null"
                :options="optionsFor(v)"
                :loading="loading[v.name]"
                filter
                resetFilterOnHide
                showClear
                placeholder="Any"
                size="small"
                class="var-input"
                :aria-label="v.label || v.name"
                @show="loadOptions(v)"
                @update:modelValue="(value) => emit('change', v, value ?? '')"
            />
            <InputText
                v-else
                :id="`var-input-${v.name}`"
                v-model="texts[v.name]"
                size="small"
                class="var-input var-text"
                placeholder="Any"
                :aria-label="v.label || v.name"
                @keydown.enter="applyText(v)"
                @blur="applyText(v)"
            />
        </div>
        <span v-if="missing.length" class="text-sm text-red-600 dark:text-red-400" data-testid="variable-missing">
            Choose a value for {{ missing.map((n) => labelOf(n)).join(', ') }}
        </span>
    </div>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { InputText, MultiSelect, Select } from 'primevue'

import { SourceService } from '@/sdk/services/source.js'

const props = defineProps({
    variables: { type: Array, default: () => [] },
    values: { type: Object, default: () => ({}) },
    range: { type: Object, required: true },
    missing: { type: Array, default: () => [] },
})
const emit = defineEmits(['change'])

const srv = new SourceService()
const fetched = reactive({})
const loading = reactive({})
const texts = reactive({})

watch(
    () => props.values,
    (values) => {
        for (const v of props.variables) if (v.type === 'text') texts[v.name] = values[v.name] || ''
    },
    { immediate: true, deep: true },
)

// Value lists follow the dashboard time range, so drop them when it changes.
watch(
    () => [props.range.from, props.range.to],
    () => Object.keys(fetched).forEach((k) => delete fetched[k]),
)

const labelOf = (name) => props.variables.find((v) => v.name === name)?.label || name

const optionsFor = (v) => {
    const base = v.type === 'static' ? v.options || [] : fetched[v.name] || []
    const selected = [].concat(props.values[v.name] || []).filter((x) => x !== '' && !base.includes(x))
    return [...selected, ...base]
}

const loadOptions = async (v) => {
    if (v.type !== 'values' || fetched[v.name] || loading[v.name]) return
    loading[v.name] = true
    try {
        const response = await srv.autocomplete(v.source, {
            column: v.column,
            value: '',
            from: props.range.from,
            to: props.range.to,
        })
        fetched[v.name] = response.result ? response.data.items || [] : []
    } catch {
        fetched[v.name] = []
    }
    loading[v.name] = false
}

const applyText = (v) => {
    const value = (texts[v.name] || '').trim()
    if (value !== (props.values[v.name] || '')) emit('change', v, value)
}
</script>

<style scoped>
.var-control {
    border: 1px solid var(--p-surface-300);
    border-radius: var(--p-border-radius-md);
    background: var(--p-surface-0);
    overflow: hidden;
}
.dark .var-control {
    border-color: var(--p-surface-700);
    background: var(--p-surface-900);
}
.var-control--missing {
    border-color: var(--p-red-400);
}
.var-label {
    color: var(--p-text-muted-color);
    background: var(--p-surface-50);
    border-right: 1px solid var(--p-surface-300);
}
.dark .var-label {
    background: var(--p-surface-800);
    border-right-color: var(--p-surface-700);
}
.var-input {
    border: 0;
    box-shadow: none;
    background: transparent;
    min-width: 9rem;
    max-width: 20rem;
}
.var-text {
    width: 12rem;
}
</style>
