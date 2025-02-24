<template>
    <Button icon="pi pi-calendar" class="mr-2" :label="daterangelabel" text size="small" @click="toggleRangeSelect" />
    <Popover ref="dropdown" :pt="{ content: { class: 'pr-0' } }">
        <div class="flex w-full">
            <div class="flex flex-col mr-3">
                <label for="From" class="font-bold block mb-2">From</label>
                <InputText label="From" v-model="fromInputText" @update:model-value="onFromInputUpdate"
                    :invalid="!fromInputValid" />
                <ErrorText v-if="!fromInputValid" :text="fromInputValidError" />
                <br>
                <label for="To" class="font-bold block mb-2">To</label>
                <InputText label="To" v-model="toInputText" @update:model-value="onToInputUpdate"
                    :invalid="!toInputValid" />
                <ErrorText v-if="!toInputValid" :text="toInputValidError" />
                <br>
                <label for="Timezone" class="font-bold block mb-2">Timezone</label>
                <Select v-model="selectedZone" :options="zones" optionLabel="name" placeholder="Timezone"
                    class="w-full md:w-56" filter autoFilterFocus disabled /><br>
                <Button label="Apply" severity="primary" @click="handleApply" />
            </div>
            <div class="border-r border-l pt-0 pb-0 p-2">
                <DatePicker v-model="dates" selectionMode="range"
                    :pt="{ panel: { style: 'border: none; padding: 0px;' } }"
                    :maxDate="DateTime.now().plus({ days: 1 }).startOf('day').toJSDate()" :manualInput="false"
                    :selectOtherMonths="true" inline @date-select="onDateSelect" />
            </div>
            <div class="flex flex-col">
                <Listbox :options="ranges" v-model="selectedRelative" optionLabel="label" @change="handleSelectRelative"
                    fluid scroll-height="21rem"
                    :pt="{ root: { style: { border: 'none', minWidth: '200px' } }, list: { style: { padding: '0', boxShadow: 'none' } } }" />
            </div>
        </div>
    </Popover>
</template>

<script setup>
import { ref, computed, onMounted, onUpdated } from 'vue'
import { useRoute } from 'vue-router'

import { DateTime } from "luxon"

import Popover from 'primevue/popover'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Listbox from 'primevue/listbox'
import Select from 'primevue/select'

import { useSourceControlsStore } from '@/stores/sourceControls'
import ErrorText from '@/components/common/ErrorText.vue'
import { getRelativeOption, getRelativeOptions, getDateIfTimestamp, getDatetimeRangeText, fmt, dateIsValid, dateTimeFormat, humanRelatedTimeRegex, getStrDateOrStrRelative } from '@/utils/datetimeranges.js'
import { tzOptions } from '@/utils/timezones.js'


const route = useRoute()

const props = defineProps(['from', 'to'])
const emit = defineEmits(['rangeSelect'])

const sourceControlsStore = useSourceControlsStore()

const dropdown = ref()
const zones = ref(tzOptions)
const selectedZone = ref({ 'name': 'UTC', 'code': 'UTC' })
const dates = ref([])

const from = ref(route.query.from ?? 'now-5m')
const to = ref(route.query.to ?? 'now')

const fromInputText = ref('')
const toInputText = ref('')
const fromInputManually = ref(false)
const toInputManually = ref(false)
const fromInputValid = ref(true)
const fromInputValidError = ref('')
const toInputValidError = ref('')
const toInputValid = ref(true)
const ranges = ref(getRelativeOptions())
const selectedRelative = ref(getRelativeOption(from.value, to.value))


const onFromInputUpdate = () => {
    fromInputManually.value = true
}

const onToInputUpdate = () => {
    toInputManually.value = true
}

const initValues = () => {
    if (props.from) {
        from.value = props.from
    }
    if (props.to) {
        to.value = props.to
    }
    fromInputText.value = getStrDateOrStrRelative(from.value)
    toInputText.value = getStrDateOrStrRelative(to.value)
    let fromResult = getDateIfTimestamp(from.value)
    let toResult = getDateIfTimestamp(to.value)

    if (fromResult.parsed && toResult.parsed) {
        dates.value = [fromResult.date, toResult.date]
    }
    emit('rangeSelect', {
        from: from.value,
        to: to.value,
    })
}

onMounted(() => {
    initValues()
})

onUpdated(() => {
    initValues()
})

const daterangelabel = computed(() => {
    return getDatetimeRangeText(from.value, to.value)
})

const getUtcTimestamp = (value) => {
    const dateInBrowserTimezone = DateTime.fromJSDate(new Date(value))
    const dateInSelectedTimezone = dateInBrowserTimezone.setZone(selectedZone.value.code, { keepLocalTime: true })
    return dateInSelectedTimezone.toUTC().toMillis()
}

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
        from.value = event.value.from
        to.value = event.value.to
        fromInputText.value = event.value.from
        toInputText.value = event.value.to
        fromInputManually.value = false
        toInputManually.value = false
        dates.value = []
    }
    emit('rangeSelect', {
        from: from.value,
        to: to.value,
    })
}

const onDateSelect = () => {
    if (dates.value[0] && dates.value[1]) {

        fromInputText.value = fmt(dates.value[0])
        toInputText.value = fmt(dates.value[1])
        fromInputManually.value = false
        toInputManually.value = false
        selectedRelative.value = null
        emit('rangeSelect', {
            from: dates.value[0],
            to: dates.value[1],
        })
    }
}

const toggleRangeSelect = (event) => {
    dropdown.value.toggle(event)
}
</script>