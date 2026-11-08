<template>
    <div class="flex flex-col gap-4" data-testid="raw-sql-fields">
        <div class="flex flex-col gap-1">
            <label class="font-medium">Connection</label>
            <Select
                v-model="chart.connection"
                :options="connections || []"
                optionLabel="name"
                optionValue="id"
                size="small"
                :loading="connections === null"
                placeholder="Choose a connection"
                :invalid="!!connectionError"
                data-testid="raw-sql-connection"
            />
            <ErrorText v-if="connectionError" :text="connectionError" class="text-sm" />
            <span v-else-if="connections && !connections.length" class="text-sm text-surface-500">
                Raw SQL needs the raw_sql_user role on a ClickHouse connection.
            </span>
        </div>
        <div class="flex flex-col gap-1">
            <label class="font-medium">SQL</label>
            <div
                class="border rounded-lg border-surface-300 dark:border-surface-600 overflow-hidden"
                :style="{ height: `${editorHeight}px` }"
                data-testid="raw-sql-editor"
            >
                <vue-monaco-editor
                    v-model:value="chart.sql"
                    :theme="isDark ? 'telescope-dark' : 'telescope'"
                    language="sql"
                    :options="options"
                    @mount="onMount"
                />
            </div>
            <ErrorText v-if="sqlError" :text="sqlError" class="text-sm" data-testid="raw-sql-error" />
            <span class="text-xs text-surface-500 dark:text-surface-400">
                One read-only SELECT, at most 1000 rows. {{ runKeys }} runs it.
            </span>
        </div>
        <div class="flex flex-col gap-1">
            <label class="font-medium"
                >Granularity <span class="font-normal text-surface-500">(for macros)</span></label
            >
            <Select
                v-model="chart.granularity"
                :options="granularityOptions"
                optionLabel="label"
                optionValue="value"
                size="small"
            />
        </div>
        <div class="flex flex-col gap-1 text-sm">
            <span class="font-medium">Macros</span>
            <div v-for="[name, help] in MACROS" :key="name" class="flex gap-2">
                <code class="font-mono text-xs text-primary shrink-0">{{ name }}</code>
                <span class="text-surface-500 dark:text-surface-400">{{ help }}</span>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Select } from 'primevue'
import { useDark } from '@vueuse/core'
import * as monaco from 'monaco-editor'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

import ErrorText from '@/components/common/ErrorText.vue'
import { getDefaultMonacoOptions } from '@/utils/monaco.js'
import { GRANULARITIES } from '@/utils/dashboards.js'
import { MACROS, rawSqlConnections } from '@/features/rawsql/service.js'

// `chart` is the TileEditor's form chart, edited in place.
const props = defineProps(['chart', 'validation'])
const emit = defineEmits(['submit'])

const isDark = useDark()
const connections = ref(null)
const defaults = getDefaultMonacoOptions()
const options = {
    ...defaults,
    padding: { top: 8, bottom: 8 },
    scrollbar: { ...defaults.scrollbar, vertical: 'auto' },
    lineNumbers: 'on',
    lineNumbersMinChars: 3,
    lineDecorationsWidth: 10,
    wordWrap: 'on',
}
const granularityOptions = GRANULARITIES.map((g) => ({ value: g, label: g === 'auto' ? 'Auto' : g }))
// Grows with the content, wrapped lines included, between 120 and 420 px.
const contentHeight = ref(0)
const editorHeight = computed(() => Math.min(420, Math.max(120, contentHeight.value + 12)))
const runKeys = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘+Enter' : 'Ctrl+Enter'

const flatten = (v) => (Array.isArray(v) ? v.flat(Infinity).join('; ') : v ? String(v) : null)
const sqlError = computed(() => flatten(props.validation?.fields?.sql))
const connectionError = computed(() => flatten(props.validation?.fields?.connection))

onMounted(async () => {
    const response = await rawSqlConnections()
    connections.value = response.result ? response.data : []
    if (props.chart.connection == null && connections.value.length) props.chart.connection = connections.value[0].id
})

const onMount = (editor) => {
    contentHeight.value = editor.getContentHeight()
    editor.onDidContentSizeChange((e) => (contentHeight.value = e.contentHeight))
    editor.addAction({
        id: 'submit',
        label: 'Run',
        keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
        run: () => emit('submit'),
    })
}
</script>
