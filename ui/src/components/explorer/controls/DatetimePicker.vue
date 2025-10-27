<template>
    <Button icon="pi pi-calendar" class="mr-2" :label="rangeLabel" text size="small" @click="toggleDropdown" />
    <Popover ref="dropdown" :pt="{ content: { class: 'pr-0' } }">
        <div class="flex w-full">
            <div class="flex flex-col mr-3">
                <div class="flex flex-col">
                    <label for="From" class="font-medium block">From</label>
                    <InputText
                        size="small"
                        label="From"
                        v-model="inputFrom.text"
                        @update:model-value="() => inputFrom.manualOverride = true"
                        :invalid="inputFrom.error !== null"
                    />
                    <ErrorText v-if="inputFrom.error" :text="inputFrom.error" />
                </div>
                <div class="flex flex-col mt-2">
                    <label for="To" class="font-medium block">To</label>
                    <InputText
                        size="small"
                        label="To"
                        v-model="inputTo.text"
                        @update:model-value="() => inputTo.manualOverride = true"
                        :invalid="inputTo.error !== null"
                    />
                    <ErrorText v-if="inputTo.error" :text="inputTo.error" />
                </div>
                <div class="flex flex-col mt-2">
                    <label for="Timezone" class="font-medium block">Timezone</label>
                    <Select
                        v-model="selectedTimeZone"
                        :options="timeZones"
                        placeholder="Timezone"
                        class="w-full md:w-56"
                        size="small"
                        filter
                    />
                </div>
                <Button label="Apply" severity="primary" size="small" class="mt-4" @click="handleSelectManual" />
            </div>
            <div class="border-r border-l pt-0 pb-0 p-2">
                <DatePicker
                    v-model="selectedDates"
                    selectionMode="range"
                    :pt="{ panel: { style: 'border: none; padding: 0px;' } }"
                    :maxDate="DateTime.now().plus({ days: 1 }).startOf('day').toJSDate()"
                    :manualInput="false"
                    :selectOtherMonths="true"
                    inline
                    @date-select="handleSelectDate"
                />
            </div>
            <div class="flex flex-col">
                <Listbox
                    :options="relativeTimeRanges"
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
import { ref, computed, watch } from 'vue'

import { DateTime } from 'luxon'

import Popover from 'primevue/popover'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Listbox from 'primevue/listbox'
import Select from 'primevue/select'

import ErrorText from '@/components/common/ErrorText.vue'
import {
    getDateTimeString,
    getNiceRangeText,
    moveTimestampToTimeZone,
    relativeTimeRanges,
    tryGetRelativeOption,
    tryParseDateTimeString,
} from '@/utils/datetimeranges.js'

const props = defineProps(['from', 'to', 'timeZone'])
const emit = defineEmits(['rangeSelect'])

const dropdown = ref()

const timeZones = Intl.supportedValuesOf('timeZone')

const inputFrom = ref({})
const inputTo = ref({})
const selectedTimeZone = ref('')

const selectedDates = ref([])

const selectedRelative = ref(null)


const initFromProps = () => {
    const initInputField = (targetDate) => {
        return {
            text: getDateTimeString(targetDate, props.timeZone),
            manualOverride: false,
            error: null
        }
    }

    inputFrom.value = initInputField(props.from)
    inputTo.value = initInputField(props.to)

    selectedTimeZone.value = props.timeZone
    
    if (typeof(props.from) === 'number' && typeof(props.to) === 'number')
        selectedDates.value = [props.from, props.to].map(timestamp => {
            const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'
            return new Date(moveTimestampToTimeZone(timestamp, props.timeZone, localTz))
        })
    else
        selectedDates.value = null

    selectedRelative.value = tryGetRelativeOption(props.from, props.to)
}

initFromProps()
watch(props, initFromProps, { deep: true })

const rangeLabel = computed(() => getNiceRangeText(props.from, props.to, props.timeZone) + ` [${props.timeZone}]`)

const toggleDropdown = (event) => dropdown.value.toggle(event)



const handleSelectManual = () => {
    const tryParseInput = (input, defaultVal) => {
        if (!input.manualOverride)
            return moveTimestampToTimeZone(defaultVal, props.timeZone, selectedTimeZone.value)

        const parsedTime = tryParseDateTimeString(input.text, selectedTimeZone.value)

        if (parsedTime)
            input.error = null
        else
            input.error = 'Invalid date: Expected absolute or relative time'

        return parsedTime
    }

    const parsedFrom = tryParseInput(inputFrom.value, props.from)
    const parsedTo = tryParseInput(inputTo.value, props.to)

    if (!parsedFrom || !parsedTo)
        return

    emit('rangeSelect', {
        from: parsedFrom,
        to: parsedTo,
        timeZone: selectedTimeZone.value
    })
}

const handleSelectDate = () => {
    if (selectedDates.value[0] && selectedDates.value[1]) {
        const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'

        const endOfDay = new Date(selectedDates.value[1].valueOf())
        endOfDay.setDate(endOfDay.getDate() + 1)
        endOfDay.setMilliseconds(endOfDay.getMilliseconds() - 1)
        
        emit('rangeSelect', {
            from: moveTimestampToTimeZone(selectedDates.value[0].valueOf(), localTz, props.timeZone),
            to: moveTimestampToTimeZone(endOfDay.valueOf(), localTz, props.timeZone),
            timeZone: props.timeZone
        })
    }
}

const handleSelectRelative = (event) => {
    if (event.value) {
        emit('rangeSelect', {
            from: event.value.from,
            to: event.value.to,
            timeZone: props.timeZone
        })
    }
}
</script>
