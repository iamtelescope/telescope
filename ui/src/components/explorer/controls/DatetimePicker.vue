<template>
    <Button icon="pi pi-calendar" class="mr-2" :label="daterangelabel" text size="small" @click="toggleRangeSelect" />
    <Popover ref="dropdown" :pt="{ content: { class: 'pr-0' } }">
        <div class="flex w-full">
            <div class="flex flex-col mr-3">
                <div class="flex flex-col">
                    <label for="From" class="font-medium block">From</label>
                    <input
                        ref="fromInputRef"
                        type="text"
                        v-model="fromInputText"
                        @input="onFromInputUpdate"
                        @blur="onFromInputBlur"
                        :class="[
                            'telescope-input-small',
                            { 'telescope-input-invalid': !fromInputValid }
                        ]"
                        placeholder="From"
                    />
                    <ErrorText v-if="!fromInputValid" :text="fromInputValidError" />
                </div>
                <div class="flex flex-col mt-2">
                    <label for="To" class="font-medium block">To</label>
                    <input
                        ref="toInputRef"
                        type="text"
                        v-model="toInputText"
                        @input="onToInputUpdate"
                        @blur="onToInputBlur"
                        :class="[
                            'telescope-input-small',
                            { 'telescope-input-invalid': !toInputValid }
                        ]"
                        placeholder="To"
                    />
                    <ErrorText v-if="!toInputValid" :text="toInputValidError" />
                </div>
                <div class="flex flex-col mt-2">
                    <label for="Timezone" class="font-medium block">Timezone</label>
                    <Select
                        v-model="selectedZone"
                        :options="zones"
                        optionLabel="name"
                        placeholder="Timezone"
                        class="w-full md:w-56"
                        size="small"
                        filter
                        autoFilterFocus
                        disabled
                    />
                </div>
                <Button label="Apply" severity="primary" size="small" class="mt-4" @click="handleApply" />
            </div>
            <div class="border-r border-l pt-0 pb-0 p-2">
                <DatePicker
                    v-model="dates"
                    selectionMode="range"
                    :pt="{ panel: { style: 'border: none; padding: 0px;' } }"
                    :maxDate="DateTime.now().plus({ days: 1 }).startOf('day').toJSDate()"
                    :manualInput="false"
                    :selectOtherMonths="true"
                    inline
                    @date-select="onDateSelect"
                />
            </div>
            <div class="flex flex-col">
                <Listbox
                    :options="ranges"
                    v-model="selectedRelative"
                    optionLabel="label"
                    @change="handleSelectRelative"
                    fluid
                    scroll-height="21rem"
                    :pt="{
                        root: { style: { border: 'none', minWidth: '200px' } },
                        list: { style: { padding: '0', boxShadow: 'none' } },
                    }"
                />
            </div>
        </div>
    </Popover>
</template>

<script setup>
import { ref, computed, onMounted, onUpdated, watch } from 'vue'

import { DateTime } from 'luxon'

import Popover from 'primevue/popover'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Listbox from 'primevue/listbox'
import Select from 'primevue/select'

import ErrorText from '@/components/common/ErrorText.vue'
import {
    getRelativeOption,
    getRelativeOptions,
    getDatetimeRangeText,
    dateIsValid,
    dateTimeFormat,
    humanRelatedTimeRegex,
} from '@/utils/datetimeranges.js'
import { tzOptions } from '@/utils/timezones.js'

const props = defineProps(['from', 'to'])
const emit = defineEmits(['rangeSelect'])
const dropdown = ref()
const fromInputRef = ref()
const toInputRef = ref()
const zones = ref(tzOptions)
const selectedZone = ref({ name: 'UTC', code: 'UTC' })
const dates = ref(props.from.dateObj && props.to.dateObj ? [props.from.dateObj, props.to.dateObj] : [])

const from = computed(() => props.from.value)
const to = computed(() => props.to.value)

const fromInputText = ref(props.from.strValue)
const toInputText = ref(props.to.strValue)
const fromInputManually = ref(false)
const toInputManually = ref(false)
const fromInputValid = ref(true)

const fromInputValidError = ref('')
const toInputValidError = ref('')
const toInputValid = ref(true)
const ranges = ref(getRelativeOptions())
const selectedRelative = ref(getRelativeOption(props.from.strValue, props.to.strValue))

const debounce = (func, delay) => {
    let timeoutId
    return (...args) => {
        clearTimeout(timeoutId)
        timeoutId = setTimeout(() => func.apply(null, args), delay)
    }
}

const debouncedApplyTimeChanges = debounce(() => {
    applyTimeChanges()
}, 500)

const onFromInputUpdate = () => {
    fromInputManually.value = true
}

const onToInputUpdate = () => {
    toInputManually.value = true
}

const onFromInputBlur = () => {
    if (fromInputManually.value) {
        applyTimeChanges()
    }
}

const onToInputBlur = () => {
    if (toInputManually.value) {
        applyTimeChanges()
    }
}

const applyTimeChanges = () => {
    let fromValid = true
    let toValid = true
    let manualFrom = null
    let manualTo = null

    if (fromInputManually.value) {
        const [parsedFrom, fromIsValid] = dateIsValid(fromInputText.value)
        fromValid = fromIsValid
        if (fromIsValid) {
            manualFrom = parsedFrom
            fromInputValidError.value = ''
        } else {
            fromInputValidError.value = `Invalid date: expect ${dateTimeFormat} or regex ${humanRelatedTimeRegex.toString()}`
        }
        fromInputValid.value = fromValid
    }

    if (toInputManually.value) {
        const [parsedTo, toIsValid] = dateIsValid(toInputText.value)
        toValid = toIsValid
        if (toIsValid) {
            manualTo = parsedTo
            toInputValidError.value = ''
        } else {
            toInputValidError.value = `Invalid date: expect ${dateTimeFormat} or regex ${humanRelatedTimeRegex.toString()}`
        }
        toInputValid.value = toValid
    }

    if (fromValid && toValid) {
        let newFrom = fromInputManually.value && manualFrom ? manualFrom : from.value
        let newTo = toInputManually.value && manualTo ? manualTo : to.value

        emit('rangeSelect', {
            from: newFrom,
            to: newTo,
        })

        fromInputManually.value = false
        toInputManually.value = false
    }
}


const initValues = () => {
    if (!fromInputManually.value) {
        fromInputText.value = props.from.strValue
    }
    if (!toInputManually.value) {
        toInputText.value = props.to.strValue
    }

    if (props.from.dateObj && props.to.dateObj) {
        dates.value = [props.from.dateObj.toJSDate(), props.to.dateObj.toJSDate()]
    }
}

onMounted(() => {
    initValues()
})

watch(
    () => [props.from, props.to],
    () => {
        if (!fromInputManually.value && !toInputManually.value) {
            initValues()
        }
    },
    { deep: true }
)

const daterangelabel = computed(() => {
    return getDatetimeRangeText(props.from.strValue, props.to.strValue) + ` [${selectedZone.value.name}]`
})

const handleApply = () => {
    let isValid = true
    let manualFrom = null
    let manualTo = null

    if (fromInputManually.value) {
        const [parsedFrom, fromIsValid] = dateIsValid(fromInputText.value)
        fromInputValid.value = fromIsValid
        if (fromIsValid) {
            manualFrom = parsedFrom
        } else {
            fromInputValidError.value = `Invalid date: expect ${dateTimeFormat}  or regex ${humanRelatedTimeRegex.toString()}`
        }
    }
    if (toInputManually.value) {
        const [parsedTo, toIsValid] = dateIsValid(toInputText.value)
        toInputValid.value = toIsValid
        if (toIsValid) {
            manualTo = parsedTo
        } else {
            toInputValidError.value = `Invalid date: expect date ${dateTimeFormat} or regex ${humanRelatedTimeRegex.toString()}`
        }
    }
    if (fromInputValid.value && toInputValid.value) {
        if (fromInputManually.value) {
            from.value = manualFrom
        }
        if (toInputManually.value) {
            to.value = manualTo
        }
    } else {
        isValid = false
    }

    if (isValid) {
        emit('rangeSelect', {
            from: from.value,
            to: to.value,
        })
        dropdown.value.toggle()
    }
}

const handleSelectRelative = (event) => {
    if (event.value) {
        fromInputManually.value = false
        toInputManually.value = false
        dates.value = []
        emit('rangeSelect', {
            from: event.value.from,
            to: event.value.to,
        })
    }
}

const onDateSelect = () => {
    if (dates.value[0] && dates.value[1]) {
        fromInputManually.value = false
        toInputManually.value = false
        selectedRelative.value = null

        let fromDate = dates.value[0]
        let toDate = dates.value[1]

        if (fromDate.toDateString() === toDate.toDateString()) {
            fromDate = new Date(fromDate.getFullYear(), fromDate.getMonth(), fromDate.getDate(), 0, 0, 0, 0)
            toDate = new Date(fromDate.getFullYear(), fromDate.getMonth(), fromDate.getDate(), 23, 59, 59, 999)
        }

        emit('rangeSelect', {
            from: fromDate,
            to: toDate,
        })
    }
}

const toggleRangeSelect = (event) => {
    dropdown.value.toggle(event)
}
</script>

<style scoped>
.telescope-input-small {
    @apply w-full text-sm border rounded-md focus:outline-none transition-colors;
    
    padding: 0.375rem 0.75rem; /* py-1.5 px-3 */
    font-size: 0.875rem; /* text-sm */
    line-height: 1.25rem;
    
    border-color: var(--p-content-border-color, #d4d4d8);
    background-color: var(--p-content-background, #ffffff);
    color: var(--p-text-color, #18181b);
}

.telescope-input-small:focus {
    border-color: var(--p-primary-color, #385dab);
    box-shadow: 0 0 0 1px var(--p-primary-color, #385dab);
}

.telescope-input-small.telescope-input-invalid {
    border-color: #ef4444;
}

.telescope-input-small.telescope-input-invalid:focus {
    border-color: #ef4444;
    box-shadow: 0 0 0 1px #ef4444;
}

:global(.dark) .telescope-input-small {
    border-color: var(--p-content-border-color, #3f3f46);
    background-color: var(--p-content-background, #27272a);
    color: var(--p-text-color, #d7d7d7);
}
</style>

