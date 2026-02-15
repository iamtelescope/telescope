<template>
    <div class="flex flex-col">
        <div class="flex justify-between items-center">
            <label class="font-medium text-lg">Severity extraction rules</label>
            <Button label="Add Rule" icon="pi pi-plus" size="small" text @click="addRule" />
        </div>
        <span class="text-gray-500 dark:text-gray-300 block">
            Extract severity from the "body" field (applied before JSON parsing)
        </span>
        <div v-if="localRules.extract.length === 0" class="text-gray-500 dark:text-gray-300 italic">
            No extraction rules defined. Click "Add Rule" to create one.
        </div>
        <div
            v-for="(rule, index) in localRules.extract"
            :key="index"
            class="border dark:border-neutral-600 rounded p-3 flex flex-col gap-3 mt-2"
        >
            <div class="flex justify-between items-center">
                <span class="font-medium">Rule {{ index + 1 }}</span>
                <Button
                    icon="pi pi-trash"
                    severity="danger"
                    text
                    size="small"
                    @click="removeRule(index)"
                    aria-label="Remove rule"
                />
            </div>

            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label :for="`rule-type-${index}`" class="font-medium text-lg block mb-1">Rule Type *</label>
                    <Select
                        :id="`rule-type-${index}`"
                        v-model="rule.type"
                        :options="ruleTypes"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        @change="onRuleTypeChange(index)"
                    />
                </div>
            </div>
            <div v-if="rule.type === 'json'" class="flex flex-col gap-2">
                <label class="font-medium text-lg">Path *</label>
                <div class="flex gap-2">
                    <InputText
                        v-model="rule.pathInput"
                        placeholder="e.g., log,level"
                        class="flex-1"
                        @input="updateJsonPath(index)"
                    />
                </div>
                <span class="text-gray-500 dark:text-gray-300">
                    Comma-separated path to nested field (e.g., "log,level")
                </span>
            </div>
            <div v-if="rule.type === 'regex'" class="flex flex-col gap-2">
                <div>
                    <label :for="`rule-pattern-${index}`" class="font-medium text-lg block mb-1">Regex Pattern *</label>
                    <InputText
                        :id="`rule-pattern-${index}`"
                        v-model="rule.pattern"
                        placeholder="e.g., \[(\w+)\]"
                        class="w-full"
                        @input="emitUpdate"
                    />
                    <span class="text-gray-500 dark:text-gray-300"
                        >Regular expression to match severity in log message</span
                    >
                </div>
                <div>
                    <label :for="`rule-group-${index}`" class="font-medium text-lg block mb-1">Capture Group</label>
                    <InputNumber
                        :id="`rule-group-${index}`"
                        v-model="rule.group"
                        :min="0"
                        :max="10"
                        class="w-full"
                        @input="emitUpdate"
                    />
                    <span class="text-gray-500 dark:text-gray-300">
                        Capture group to extract (0 = full match, 1+ = capture groups)
                    </span>
                </div>
                <div class="flex items-center gap-2">
                    <ToggleSwitch
                        v-model="rule.case_insensitive"
                        :inputId="`extract-case-${index}`"
                        @change="emitUpdate"
                    />
                    <label :for="`extract-case-${index}`">Case-insensitive</label>
                </div>
            </div>
        </div>
        <div class="mt-4">
            <div class="flex justify-between items-center mb-2">
                <label class="font-medium text-lg">Severity remapping (optional)</label>
                <Button label="Add Mapping" icon="pi pi-plus" size="small" text @click="addRemapEntry" />
            </div>
            <span class="text-gray-500 dark:text-gray-300 block">
                Map extracted values to normalized severity levels using regex patterns
            </span>
            <div v-if="remapRules.length === 0" class="text-gray-500 dark:text-gray-300 italic">
                No remappings defined. Extracted values will be used as-is.
            </div>
            <div
                v-for="(rule, index) in remapRules"
                :key="`remap-${index}`"
                class="border dark:border-neutral-600 rounded p-3 mb-2 mt-2"
            >
                <div class="flex gap-2 mb-2">
                    <InputText v-model="rule.pattern" placeholder="Pattern (e.g., warn.* or error)" class="flex-1" />
                    <span class="self-center">→</span>
                    <Select v-model="rule.value" :options="severityLevels" placeholder="Select severity" class="flex-1">
                        <template #option="slotProps">
                            <div class="flex items-center gap-1">
                                <div
                                    class="w-3 h-3 rounded"
                                    :style="{ backgroundColor: getColor(slotProps.option) }"
                                ></div>
                                <span>{{ slotProps.option }}</span>
                            </div>
                        </template>
                        <template #value="slotProps">
                            <div class="flex items-center gap-2">
                                <div
                                    v-if="slotProps.value"
                                    class="w-3 h-3 rounded"
                                    :style="{ backgroundColor: getColor(slotProps.value) }"
                                ></div>
                                <span>{{ slotProps.value || slotProps.placeholder }}</span>
                            </div>
                        </template>
                    </Select>
                    <Button
                        icon="pi pi-trash"
                        severity="danger"
                        text
                        size="small"
                        @click="removeRemapEntry(index)"
                        aria-label="Remove mapping"
                    />
                </div>
                <div class="flex items-center gap-2">
                    <ToggleSwitch v-model="rule.case_insensitive" :inputId="`remap-case-${index}`" />
                    <label :for="`remap-case-${index}`">Case-insensitive</label>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button, InputText, Select, InputNumber, ToggleSwitch } from 'primevue'
import { getColor } from '@/utils/colors.js'

const severityLevels = ['UNKNOWN', 'FATAL', 'ERROR', 'CRITICAL', 'WARN', 'INFO', 'DEBUG', 'TRACE']

const props = defineProps({
    modelValue: {
        type: Object,
        default: () => ({ extract: [], remap: {} }),
    },
})

const emit = defineEmits(['update:modelValue'])

const ruleTypes = [
    { label: 'Field', value: 'json' },
    { label: 'Regex', value: 'regex' },
]

const localRules = ref({
    extract: (props.modelValue?.extract || []).map((rule) => ({
        ...rule,
        pathInput: rule.path ? rule.path.join(',') : '',
    })),
})

const initializeRemapRules = () => {
    const remap = props.modelValue?.remap
    if (!remap) return []

    if (Array.isArray(remap)) {
        return remap.map((rule) => ({
            pattern: rule.pattern || '',
            value: rule.value || '',
            case_insensitive: rule.case_insensitive || false,
        }))
    } else {
        return Object.entries(remap).map(([pattern, value]) => ({
            pattern,
            value,
            case_insensitive: false,
        }))
    }
}

const remapRules = ref(initializeRemapRules())
const isInternalUpdate = ref(false)

const addRule = () => {
    localRules.value.extract.push({
        type: 'json',
        path: [],
        pathInput: '',
    })
    emitUpdate()
}

const removeRule = (index) => {
    localRules.value.extract.splice(index, 1)
    emitUpdate()
}

const onRuleTypeChange = (index) => {
    const rule = localRules.value.extract[index]
    if (rule.type === 'json') {
        delete rule.pattern
        delete rule.group
        delete rule.case_insensitive
        rule.path = []
        rule.pathInput = ''
    } else if (rule.type === 'regex') {
        delete rule.path
        delete rule.pathInput
        rule.pattern = ''
        rule.group = 0
        rule.case_insensitive = false
    }
    emitUpdate()
}

const updateJsonPath = (index) => {
    const rule = localRules.value.extract[index]
    if (rule.pathInput && rule.pathInput.trim()) {
        rule.path = rule.pathInput
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
    } else {
        rule.path = []
    }
    emitUpdate()
}

const addRemapEntry = () => {
    remapRules.value.push({ pattern: '', value: '', case_insensitive: false })
}

const removeRemapEntry = (index) => {
    remapRules.value.splice(index, 1)
    emitUpdate()
}

const emitUpdate = () => {
    const cleanRemap = remapRules.value
        .filter((rule) => rule.pattern || rule.value)
        .map((rule) => ({
            pattern: rule.pattern || '',
            value: rule.value || '',
            case_insensitive: rule.case_insensitive || false,
        }))

    const cleanRules = {
        extract: localRules.value.extract.map((rule) => {
            const cleanRule = { type: rule.type }
            if (rule.type === 'json') {
                cleanRule.path = rule.path
            } else if (rule.type === 'regex') {
                cleanRule.pattern = rule.pattern
                if (rule.group !== undefined && rule.group !== null) {
                    cleanRule.group = rule.group
                }
                if (rule.case_insensitive) {
                    cleanRule.case_insensitive = rule.case_insensitive
                }
            }
            return cleanRule
        }),
        remap: cleanRemap,
    }

    isInternalUpdate.value = true
    emit('update:modelValue', cleanRules)
}

watch(
    remapRules,
    () => {
        emitUpdate()
    },
    { deep: true, flush: 'post' },
)

watch(
    () => props.modelValue,
    (newVal) => {
        if (isInternalUpdate.value) {
            isInternalUpdate.value = false
            return
        }

        if (newVal && newVal !== localRules.value) {
            localRules.value = {
                extract: (newVal.extract || []).map((rule) => ({
                    ...rule,
                    pathInput: rule.path ? rule.path.join(',') : '',
                })),
            }

            const remap = newVal.remap
            if (Array.isArray(remap)) {
                remapRules.value = remap.map((rule) => ({
                    pattern: rule.pattern || '',
                    value: rule.value || '',
                    case_insensitive: rule.case_insensitive || false,
                }))
            } else if (remap && typeof remap === 'object') {
                remapRules.value = Object.entries(remap).map(([pattern, value]) => ({
                    pattern,
                    value,
                    case_insensitive: false,
                }))
            } else {
                remapRules.value = []
            }
        }
    },
    { deep: true, immediate: false },
)
</script>
