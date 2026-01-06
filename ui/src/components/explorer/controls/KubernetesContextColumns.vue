<template>
    <div class="flex flex-col gap-2 pt-2">
        <!-- Row 1: Context selector, Namespace selector, Pod selectors, FlyQL toggle -->
        <div class="flex flex-wrap items-end gap-2">
            <!-- Context MultiSelect -->
            <FloatLabel variant="on" class="w-[180px]">
                <MultiSelect
                    id="contexts"
                    v-model="selectedContexts"
                    :options="contextOptions"
                    :maxSelectedLabels="2"
                    filter
                    filterPlaceholder="Search..."
                    class="w-full text-sm"
                    @change="onContextsChange"
                />
                <label for="contexts">Contexts</label>
            </FloatLabel>

            <!-- Namespace MultiSelect -->
            <FloatLabel variant="on" class="w-[200px]">
                <MultiSelect
                    id="namespaces"
                    v-model="selectedNamespaces"
                    :options="namespaceOptions"
                    :maxSelectedLabels="2"
                    filter
                    filterPlaceholder="Search..."
                    class="w-full text-sm"
                    @change="onNamespacesChange"
                />
                <label for="namespaces">Namespaces</label>
            </FloatLabel>

            <!-- Pod Label Selector -->
            <FloatLabel variant="on" class="flex-1 min-w-[150px]">
                <InputText
                    id="pods_label_selector"
                    v-model="podsLabelSelector"
                    class="w-full font-mono text-sm"
                    @input="onPodsLabelSelectorChange"
                />
                <label for="pods_label_selector">Pod Label Selector</label>
            </FloatLabel>

            <!-- Pod Field Selector -->
            <FloatLabel variant="on" class="flex-1 min-w-[150px]">
                <InputText
                    id="pods_field_selector"
                    v-model="podsFieldSelector"
                    class="w-full font-mono text-sm"
                    @input="onPodsFieldSelectorChange"
                />
                <label for="pods_field_selector">Pod Field Selector</label>
            </FloatLabel>

            <!-- FlyQL Pods Filter Toggle -->
            <div class="flex items-center gap-2 pb-2">
                <ToggleSwitch v-model="showFlyqlFilter" @change="onFlyqlToggleChange" />
                <span class="text-sm text-gray-600 dark:text-gray-400">Pod FlyQL selector</span>
            </div>

            <!-- View Pods Button -->
            <Button label="View Pods" icon="pi pi-eye" size="small" severity="secondary" @click="onViewPods" />
        </div>

        <!-- Row 2: FlyQL Editor (conditionally shown) -->
        <IftaLabel v-if="showFlyqlFilter">
            <div
                id="pods_flyql_filter"
                :style="{ height: `${editorHeight}px` }"
                class="editor border rounded-lg border-neutral-300 pl-2 pr-2 dark:border-neutral-600 w-full"
                :class="{ 'border-sky-800 dark:border-sky-700': editorFocused }"
            >
                <vue-monaco-editor
                    v-model:value="podsFlyqlFilter"
                    theme="telescope"
                    language="flyql"
                    :options="getDefaultMonacoOptions()"
                    @mount="handleMount"
                    @change="onPodsFlyqlFilterChange"
                />
            </div>
            <label for="pods_flyql_filter">Pod FlyQL Filter</label>
        </IftaLabel>

        <!-- Pods Preview Dialog -->
        <Dialog v-model:visible="showPodsDialog" :modal="true" :style="{ width: '90vw' }" @show="loadPods">
            <template #header>
                <span class="font-semibold text-lg">
                    Matched Pods
                    <span v-if="podsLoading" class="inline-flex"><Loader small /></span>
                    <span v-else>[{{ pods.length }}]</span>
                </span>
            </template>
            <div v-if="podsLoading" class="flex items-center justify-center py-8">
                <i class="pi pi-spin pi-spinner text-4xl text-gray-400"></i>
            </div>
            <div v-else-if="podsError" class="text-red-500 mb-4">{{ podsError }}</div>
            <div v-else-if="pods.length === 0" class="text-gray-500">No pods found matching the criteria.</div>
            <DataTable v-else :value="pods" size="small" scrollable scrollHeight="60vh">
                <Column field="context" header="Context" sortable style="min-width: 120px" />
                <Column field="namespace" header="Namespace" sortable style="min-width: 120px" />
                <Column field="pod_name" header="Pod" sortable style="min-width: 200px" />
                <Column field="containers" header="Containers" style="min-width: 150px">
                    <template #body="{ data }">
                        <div class="font-mono text-sm">
                            <div v-for="container in data.containers" :key="container">{{ container }}</div>
                        </div>
                    </template>
                </Column>
                <Column field="status" header="Status" sortable style="min-width: 100px">
                    <template #body="{ data }">
                        <span
                            :class="{
                                'text-green-600 dark:text-green-400': data.status === 'Running',
                                'text-yellow-600 dark:text-yellow-400': data.status === 'Pending',
                                'text-red-600 dark:text-red-400': data.status === 'Failed',
                            }"
                        >
                            {{ data.status }}
                        </span>
                    </template>
                </Column>
                <Column header="Labels" style="min-width: 80px">
                    <template #body="{ data }">
                        <i
                            v-if="data.labels && Object.keys(data.labels).length > 0"
                            class="pi pi-tags cursor-pointer text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                            @click="(e) => showLabelsPopover(e, data.labels)"
                        ></i>
                        <span v-else class="text-gray-400">-</span>
                    </template>
                </Column>
                <Column header="Annotations" style="min-width: 80px">
                    <template #body="{ data }">
                        <i
                            v-if="data.annotations && Object.keys(data.annotations).length > 0"
                            class="pi pi-file-edit cursor-pointer text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                            @click="(e) => showAnnotationsPopover(e, data.annotations)"
                        ></i>
                        <span v-else class="text-gray-400">-</span>
                    </template>
                </Column>
            </DataTable>
            <Popover ref="labelsPopover">
                <div class="max-w-md max-h-64 overflow-auto p-2">
                    <div v-for="(value, key) in popoverData" :key="key" class="text-sm mb-1">
                        <span class="font-semibold">{{ key }}:</span>
                        <span class="ml-1 text-gray-600 dark:text-gray-400 break-all">{{ value }}</span>
                    </div>
                </div>
            </Popover>
            <Popover ref="annotationsPopover">
                <div class="max-w-md max-h-64 overflow-auto p-2">
                    <div v-for="(value, key) in popoverData" :key="key" class="text-sm mb-1">
                        <span class="font-semibold">{{ key }}:</span>
                        <span class="ml-1 text-gray-600 dark:text-gray-400 break-all">{{ value }}</span>
                    </div>
                </div>
            </Popover>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
    MultiSelect,
    InputText,
    ToggleSwitch,
    IftaLabel,
    FloatLabel,
    Button,
    Dialog,
    DataTable,
    Column,
    Popover,
} from 'primevue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { getDefaultMonacoOptions } from '@/utils/monaco.js'
import { SourceService } from '@/sdk/services/source.js'
import Loader from '@/components/common/Loader.vue'
import * as monaco from 'monaco-editor'

const sourceService = new SourceService()

const props = defineProps(['source', 'contextColumns', 'contextColumnsData'])
const emit = defineEmits(['columnChanged'])

// Helper to ensure array
const ensureArray = (val) => {
    if (!val) return []
    if (Array.isArray(val)) return val
    if (typeof val === 'string') return val.split(',').filter((v) => v)
    return []
}

// Form values
const selectedContexts = ref(ensureArray(props.contextColumns?.contexts))
const selectedNamespaces = ref(ensureArray(props.contextColumns?.namespaces))
const podsFieldSelector = ref(props.contextColumns?.pods_field_selector || '')
const podsLabelSelector = ref(props.contextColumns?.pods_label_selector || '')
const podsFlyqlFilter = ref(props.contextColumns?.pods_flyql_filter || '')
const showFlyqlFilter = ref(!!props.contextColumns?.pods_flyql_filter)

// Editor state
const editorFocused = ref(false)

// Pods preview state
const showPodsDialog = ref(false)
const pods = ref([])
const podsLoading = ref(false)
const podsError = ref(null)

// Popover state
const labelsPopover = ref(null)
const annotationsPopover = ref(null)
const popoverData = ref({})

// Computed: context options from prop data
const contextOptions = computed(() => {
    return props.contextColumnsData?.contexts || []
})

// Computed: namespace options from prop data
const namespaceOptions = computed(() => {
    return props.contextColumnsData?.namespaces || []
})

// Editor height calculation
const editorHeight = computed(() => {
    const lines = (podsFlyqlFilter.value.match(/\n/g) || '').length + 1
    return 24 + lines * 20
})

const completionProvider = ref(null)

const handleMount = (editor) => {
    editor.updateOptions({
        placeholder: 'metadata.name ~ "api" and not metadata.name ~ "worker"',
    })
    editor.onDidFocusEditorText(() => {
        editorFocused.value = true
    })
    editor.onDidBlurEditorText(() => {
        editorFocused.value = false
    })

    completionProvider.value = monaco.languages.registerCompletionItemProvider('flyql', {
        provideCompletionItems: (model, position) => {
            const word = model.getWordUntilPosition(position)
            const range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn,
            }

            const suggestions = [
                {
                    label: 'apiVersion',
                    kind: monaco.languages.CompletionItemKind.Field,
                    insertText: 'apiVersion',
                    range: range,
                },
                {
                    label: 'kind',
                    kind: monaco.languages.CompletionItemKind.Field,
                    insertText: 'kind',
                    range: range,
                },
                {
                    label: 'metadata',
                    kind: monaco.languages.CompletionItemKind.Field,
                    insertText: 'metadata',
                    range: range,
                },
                {
                    label: 'spec',
                    kind: monaco.languages.CompletionItemKind.Field,
                    insertText: 'spec',
                    range: range,
                },
                {
                    label: 'status',
                    kind: monaco.languages.CompletionItemKind.Field,
                    insertText: 'status',
                    range: range,
                },
            ]

            return { suggestions }
        },
    })
}

// View pods handler - just opens the dialog
const onViewPods = () => {
    pods.value = []
    podsError.value = null
    podsLoading.value = true
    showPodsDialog.value = true
}

const loadPods = async () => {
    podsLoading.value = true
    podsError.value = null

    try {
        const response = await sourceService.getContextColumnData(props.source.slug, {
            column: 'pods',
            params: {
                contexts: selectedContexts.value,
                namespaces: selectedNamespaces.value,
                pods_label_selector: podsLabelSelector.value,
                pods_field_selector: podsFieldSelector.value,
                pods_flyql_filter: podsFlyqlFilter.value,
            },
        })

        if (response.validation && !response.validation.result) {
            const errors = []

            if (response.validation.fields) {
                Object.entries(response.validation.fields).forEach(([field, messages]) => {
                    if (Array.isArray(messages)) {
                        messages.forEach((msg) => errors.push(`${field}: ${msg}`))
                    }
                })
            }

            if (response.validation.columns) {
                Object.entries(response.validation.columns).forEach(([field, messages]) => {
                    if (Array.isArray(messages)) {
                        messages.forEach((msg) => errors.push(`${field}: ${msg}`))
                    }
                })
            }

            if (response.validation.non_column && Array.isArray(response.validation.non_column)) {
                errors.push(...response.validation.non_column)
            }

            podsError.value = errors.length > 0 ? errors.join(', ') : 'Validation failed'
        } else if (response.result) {
            pods.value = response.data?.data || []
        } else {
            podsError.value = response.error || 'Failed to fetch pods'
        }
    } catch (err) {
        podsError.value = err.message || 'Failed to fetch pods'
    } finally {
        podsLoading.value = false
    }
}

// Popover handlers
const showLabelsPopover = (event, labels) => {
    popoverData.value = labels
    labelsPopover.value.toggle(event)
}

const showAnnotationsPopover = (event, annotations) => {
    popoverData.value = annotations
    annotationsPopover.value.toggle(event)
}

// Event handlers
const onContextsChange = () => {
    emit('columnChanged', {
        name: 'contexts',
        value: selectedContexts.value,
    })
}

const onNamespacesChange = () => {
    emit('columnChanged', {
        name: 'namespaces',
        value: selectedNamespaces.value,
    })
}

const onPodsFieldSelectorChange = () => {
    emit('columnChanged', {
        name: 'pods_field_selector',
        value: podsFieldSelector.value,
    })
}

const onPodsLabelSelectorChange = () => {
    emit('columnChanged', {
        name: 'pods_label_selector',
        value: podsLabelSelector.value,
    })
}

const onPodsFlyqlFilterChange = () => {
    emit('columnChanged', {
        name: 'pods_flyql_filter',
        value: podsFlyqlFilter.value,
    })
}

const onFlyqlToggleChange = () => {
    if (!showFlyqlFilter.value) {
        podsFlyqlFilter.value = ''
        emit('columnChanged', {
            name: 'pods_flyql_filter',
            value: '',
        })
    }
}

// Watch for external changes
watch(
    () => props.contextColumns,
    (newVal) => {
        if (newVal) {
            selectedContexts.value = ensureArray(newVal.contexts)
            selectedNamespaces.value = ensureArray(newVal.namespaces)
            podsFieldSelector.value = newVal.pods_field_selector || ''
            podsLabelSelector.value = newVal.pods_label_selector || ''
            podsFlyqlFilter.value = newVal.pods_flyql_filter || ''
            if (newVal.pods_flyql_filter) {
                showFlyqlFilter.value = true
            }
        }
    },
    { deep: true },
)
</script>
