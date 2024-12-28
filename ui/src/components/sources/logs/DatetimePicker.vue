<template>
    <Button icon="pi pi-calendar" class="mr-2" :label="daterangelabel" text size="small" @click="toggleRangeSelect" />
    <Popover ref="dropdown" :pt="{ content: { class: 'pr-0' } }">
        <div class="flex w-full">``
            <div class="flex flex-col mr-3">
                <label for="From" class="font-bold block mb-2">From</label>
                <InputText label="From" v-model="fromInputText" />
                <br>
                <label for="To" class="font-bold block mb-2">To</label>
                <InputText label="To" v-model="toInputText" /><br>
                <label for="Timezone" class="font-bold block mb-2">Timezone</label>
                <Select v-model="selectedZone" :options="zones" optionLabel="name" placeholder="Timezone"
                    class="w-full md:w-56" filter autoFilterFocus /><br>
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
                    fluid :pt="{ root: { style: { border: 'none', minWidth:'200px' } }, list: { style: { padding: '0', boxShadow: 'none' } } }" />
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

import { getRelativeOption, getRelativeOptions, getDateIfTimestamp, getDatetimeRangeText, fmt } from '@/utils/datetimeranges.js'
import { tzOptions } from '@/utils/timezones.js'

const route = useRoute()

const props = defineProps(['from', 'to'])
const emit = defineEmits(['rangeSelect'])
const dropdown = ref()
const zones = ref(tzOptions)
const selectedZone = ref({ 'name': 'UTC', 'code': 'UTC' })
const dates = ref([])

const from = ref(route.query.from ?? 'now-5m')
const to = ref(route.query.to ?? 'now')

const fromInputText = ref('')
const toInputText = ref('')
const ranges = ref(getRelativeOptions())
const selectedRelative = ref(getRelativeOption(from.value, to.value))

const initValues = () => {
    if (props.from) {
        from.value = props.from
    }
    if (props.to) {
        to.value = props.to
    }
    let fromResult = getDateIfTimestamp(from.value)
    let toResult = getDateIfTimestamp(to.value)

    if (fromResult.parsed && toResult.parsed) {
        dates.value = [fromResult.date, toResult.date]
        fromInputText.value = fmt(fromResult.date)
        toInputText.value = fmt(toResult.date)
    } else {
        if (from.value instanceof Date && to.value instanceof Date) {
            dates.value = [from.value, to.value]
            fromInputText.value = fmt(from.value)
            toInputText.value = fmt(to.value)
        } else {
            fromInputText.value = from.value
            toInputText.value = to.value
        }
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
    emit('rangeSelect', {
        from: from.value,
        to: to.value,
    })
    dropdown.value.toggle()
}

const handleSelectRelative = (event) => {
    if (event.value) {
        from.value = event.value.from
        to.value = event.value.to
        fromInputText.value = event.value.from
        toInputText.value = event.value.to
        dates.value = []
    }
    emit('rangeSelect', {
        from: from.value,
        to: to.value,
    })
}

const onDateSelect = () => {
    if (dates.value[0] && dates.value[1]) {
        from.value = dates.value[0]
        to.value = dates.value[1]
        fromInputText.value = fmt(dates.value[0])
        toInputText.value = fmt(dates.value[1])
        selectedRelative.value = null
    }
}

const toggleRangeSelect = (event) => {
    dropdown.value.toggle(event)
}
</script>
<style scoped>
.custom-panel {
    border: none;
}
</style>