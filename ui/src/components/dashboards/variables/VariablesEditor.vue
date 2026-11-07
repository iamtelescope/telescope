<template>
    <Dialog
        :visible="visible"
        modal
        header="Dashboard variables"
        :style="{ width: '52rem' }"
        :breakpoints="{ '960px': '95vw' }"
        @update:visible="(v) => emit('update:visible', v)"
        data-testid="variables-editor"
    >
        <p class="mt-0 mb-4 text-sm text-surface-500 dark:text-surface-400">
            Use <code>$name</code> as a value in a tile query or the dashboard filter, e.g.
            <code>service = $service</code>. A multi-value variable binds as <code>in [...]</code>; an empty optional
            variable drops the condition that uses it.
        </p>
        <div v-if="!items.length" class="py-6 text-center text-surface-500 dark:text-surface-400">
            No variables yet.
        </div>
        <div
            v-for="(item, i) in items"
            :key="item.key"
            class="var-row grid gap-3 p-3 mb-3 rounded-lg"
            :data-testid="`variable-row-${i}`"
        >
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div class="flex flex-col gap-1">
                    <label class="text-sm font-medium">Name</label>
                    <InputText
                        v-model="item.name"
                        size="small"
                        placeholder="service"
                        :invalid="!!errors[i]?.name"
                        data-testid="variable-name"
                    />
                    <small v-if="errors[i]?.name" class="text-red-500">{{ errors[i].name }}</small>
                </div>
                <div class="flex flex-col gap-1">
                    <label class="text-sm font-medium">Label</label>
                    <InputText v-model="item.label" size="small" placeholder="Service" />
                </div>
                <div class="flex flex-col gap-1">
                    <label class="text-sm font-medium">Type</label>
                    <Select
                        v-model="item.type"
                        :options="VARIABLE_TYPES"
                        optionLabel="label"
                        optionValue="value"
                        size="small"
                        data-testid="variable-type"
                    />
                </div>
            </div>
            <div v-if="item.type === 'values'" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="flex flex-col gap-1">
                    <label class="text-sm font-medium">Source</label>
                    <Select
                        v-model="item.source"
                        :options="sources"
                        optionLabel="name"
                        optionValue="slug"
                        filter
                        size="small"
                        placeholder="Choose a source"
                        :invalid="!!errors[i]?.source"
                        data-testid="variable-source"
                        @update:modelValue="item.column = ''"
                    />
                    <small v-if="errors[i]?.source" class="text-red-500">{{ errors[i].source }}</small>
                </div>
                <div class="flex flex-col gap-1">
                    <label class="text-sm font-medium">Column</label>
                    <Select
                        v-model="item.column"
                        :options="columnsOf(item.source)"
                        filter
                        size="small"
                        placeholder="Values come from this column"
                        :invalid="!!errors[i]?.column"
                        data-testid="variable-column"
                    />
                    <small v-if="errors[i]?.column" class="text-red-500">{{ errors[i].column }}</small>
                </div>
            </div>
            <div v-if="item.type === 'static'" class="flex flex-col gap-1">
                <label class="text-sm font-medium">Options, one per line</label>
                <Textarea
                    v-model="item.optionsText"
                    rows="3"
                    autoResize
                    class="text-sm"
                    :invalid="!!errors[i]?.options"
                    data-testid="variable-options"
                />
                <small v-if="errors[i]?.options" class="text-red-500">{{ errors[i].options }}</small>
            </div>
            <div class="flex flex-wrap items-center gap-x-5 gap-y-2">
                <label v-if="item.type !== 'text'" class="flex items-center gap-2 text-sm">
                    <Checkbox v-model="item.multi" binary data-testid="variable-multi" /> Several values
                </label>
                <label class="flex items-center gap-2 text-sm">
                    <Checkbox v-model="item.required" binary data-testid="variable-required" /> Required
                </label>
                <span class="flex-1"></span>
                <Button
                    icon="pi pi-trash"
                    label="Remove"
                    text
                    severity="danger"
                    size="small"
                    @click="items.splice(i, 1)"
                />
            </div>
        </div>
        <Button
            label="Add variable"
            icon="pi pi-plus"
            severity="secondary"
            outlined
            size="small"
            @click="addItem"
            data-testid="variable-add"
        />
        <template #footer>
            <Button label="Cancel" severity="secondary" text size="small" @click="emit('update:visible', false)" />
            <Button label="Apply" icon="pi pi-check" size="small" @click="apply" data-testid="variables-apply" />
        </template>
    </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button, Checkbox, Dialog, InputText, Select, Textarea } from 'primevue'

import { VARIABLE_NAME_RE, VARIABLE_TYPES } from '@/utils/dashboards'

const props = defineProps({
    visible: Boolean,
    variables: { type: Array, default: () => [] },
    sources: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:visible', 'apply'])

const items = ref([])
const errors = ref({})
let seq = 0

const toItem = (v) => ({
    key: seq++,
    name: v.name || '',
    label: v.label || '',
    type: v.type || 'values',
    source: v.source || '',
    column: v.column || '',
    optionsText: (v.options || []).join('\n'),
    multi: !!v.multi,
    required: !!v.required,
    default: v.default,
})

watch(
    () => props.visible,
    (visible) => {
        if (!visible) return
        items.value = props.variables.map(toItem)
        errors.value = {}
    },
    { immediate: true },
)

const columnsOf = (slug) => Object.keys(props.sources.find((s) => s.slug === slug)?.columns || {})

const addItem = () => items.value.push(toItem({}))

const options = (item) => [...new Set(item.optionsText.split('\n').map((s) => s.trim()))].filter((s) => s !== '')

// The default stays the one saved; Save stores the bar's current values as defaults.
const toVariable = (item) => {
    const v = { name: item.name.trim(), type: item.type }
    if (item.label.trim()) v.label = item.label.trim()
    if (item.type === 'values') Object.assign(v, { source: item.source, column: item.column })
    if (item.type === 'static') v.options = options(item)
    v.multi = item.type !== 'text' && item.multi
    v.required = item.required
    let value = [].concat(item.default ?? []).filter((x) => x !== '')
    if (v.type === 'static') value = value.filter((x) => v.options.includes(x))
    if (value.length) v.default = v.multi ? value : value[0]
    return v
}

const validate = (variables) => {
    const result = {}
    const seen = new Set()
    variables.forEach((v, i) => {
        const e = {}
        if (!VARIABLE_NAME_RE.test(v.name)) e.name = 'Letters, digits and _, not starting with a digit'
        else if (seen.has(v.name)) e.name = `Duplicate variable ${v.name}`
        seen.add(v.name)
        if (v.type === 'values' && !v.source) e.source = 'Choose a source'
        if (v.type === 'values' && !v.column) e.column = 'Choose a column'
        if (v.type === 'static' && !v.options.length) e.options = 'Add at least one option'
        if (Object.keys(e).length) result[i] = e
    })
    return result
}

const apply = () => {
    const variables = items.value.map(toVariable)
    errors.value = validate(variables)
    if (Object.keys(errors.value).length) return
    emit('apply', variables)
    emit('update:visible', false)
}
</script>

<style scoped>
.var-row {
    border: 1px solid var(--p-surface-200);
    background: var(--p-surface-50);
}
.dark .var-row {
    border-color: var(--p-surface-700);
    background: var(--p-surface-800);
}
code {
    font-size: 0.8125rem;
    padding: 0 0.25rem;
    border-radius: 0.25rem;
    background: var(--p-surface-100);
}
.dark code {
    background: var(--p-surface-800);
}
</style>
