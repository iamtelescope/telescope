<template>
    <BorderCard class="border-neutral-300 dark:border-neutral-600">
        <div class="flex flex-row">
            <FloatLabel variant="on" class="mr-2">
                <Select v-model="groupBy" :options="groupByOptions" placeholder="&#8211;" filter autoFilterFocus />
                <label>Group by</label>
            </FloatLabel>
            <SelectButton v-model="chartType" :defaultValue="chartDefaultType" :allowEmpty="false" :options="options"
                @change="onChartTypeSelect">
                <template #option="slotProps">
                    <font-awesome-icon :icon="`fa-solid fa-chart-${slotProps.option}`" />
                </template>
            </SelectButton>
        </div>
        <div class="flex flex-col" id="histogramm">
            <YagrChart v-if="chartSettings" :theme="theme" :settings="chartSettings" />
        </div>
    </BorderCard>
</template>
<script setup>
import { ref, onMounted, computed } from 'vue'
import { format } from "date-fns"

import SelectButton from 'primevue/selectbutton'
import FloatLabel from 'primevue/floatlabel'
import Select from 'primevue/select'

import { useDark } from '@vueuse/core'

import BorderCard from '@/components/common/BorderCard.vue'
import YagrChart from '@/components/common/YagrChart.vue'

import { getColor } from '@/utils/colors.js'

const props = defineProps(['source', 'timestamps', 'data', 'meta'])
const emit = defineEmits(['rangeSelected'])
const chartSettings = ref(null)
const chartType = ref(null)
const groupBy = ref(props.source.severityField)
const groupByOptions = ref([props.source.severityField])
const chartDefaultType = ref('column')
const options = ref(['column', 'area', 'line'])
const isDark = useDark()

const onChartTypeSelect = (e) => {
    let type = e.value ?? chartDefaultType.value
    chartType.value = type
    chartSettings.value = getChartSettings(type)
}

const theme = computed(() => {
    if (isDark.value) {
        return 'dark'
    } else {
        return 'light'
    }
})

const calcRenderOptions = (type) => {
    let options = {}
    if (type == 'column') {
        let columns = props.timestamps.length
        // left-rigth padding of graph
        let padding = 70
        // spaces between columns 
        let totalSpacing = columns + 2

        // calculate expected graph width
        let width = document.getElementById('histogramm').getBoundingClientRect().width - padding - totalSpacing

        let min = Math.floor(width / columns)
        if (min <= 0 || columns > 200) {
            min = 1
        }
        let max = 20
        let factor = 0.8
        options['size'] = [factor, max, min]
        options['radius'] = 0.2
    }
    return options
}

const calcPlotLines = () => {
    let plotLines = []

    if (props.meta.rows < props.meta.total) {
        let color = 'rgba(0, 0, 255, 0.05)'
        let plotSize = props.meta.newest_row - props.meta.oldest_row
        let totalSize = props.timestamps[props.timestamps.length - 1] - props.timestamps[0]
        let plotPercent = (plotSize * 100) / totalSize

        if (plotPercent == 0) {
            color = 'rgba(0, 0, 255, 0.2)'
        }
        plotLines = [{
            value: [props.meta.newest_row, props.meta.oldest_row],
            color: color,
        }]
    }
    return plotLines
}

const tooltipRender = (data) => {
    let html = `<div class="font-bold pb-2 dark:text-neutral-300">${format(new Date(data.x), "yyyy-MM-dd HH:mm:ss.SSS")}</div><table class='p-0 m-0 w-full'>`
    let rows = []
    for (const item of data.scales[0].rows.sort((a, b) => b.originalValue - a.originalValue)) {
        html += '<tr>'
        html += `<td class="p-0 border-0"><i style="color:${item.color};" class="pi pi-circle-fill"></i></td>`
        html += `<td class="p-0 border-0">${item.name}</td>`
        html += `<td class="p-0 border-0 text-right"> ${item.dataValue}</td>`
        html += '</tr>'
    }
    html += '</table>'
    return html
}

const getChartSettings = (type) => {
    let stacking = true
    if (type == 'line') {
        stacking = false
    }
    const series = []
    let num = 0
    for (const [key, value] of Object.entries(props.data)) {
        let item = {
            name: key,
            data: value,
            stack: 'severity',
            id: key,
            color: getColor(key),
        }
        num += 1
        series.push(item)
    }
    return {
        timeline: props.timestamps,
        timeMultiplier: 1,
        legend: {
            show: true,
        },
        scales: {
            y: {
                stacking: stacking,
            },
        },
        tooltip: {
            sum: true,
            render: tooltipRender,
        },
        chart: {
            appearance: {
                drawOrder: ['plotLines', 'axes', 'series'],
                theme: theme.value,
            },
            series: {
                type: type,
                renderOptions: calcRenderOptions(type),
                lineWidth: 1,
                width: 1,
            },
        },
        axes: {
            x: {
                plotLines: calcPlotLines(),
                values: [
                    // tick incr default year month day hour min sec mode
                    [3600 * 24 * 365 * 1000, "{YYYY} {MMM}", null, null, null, null, null, null, 1],
                    [3600 * 24 * 28 * 1000, "{MMM}", null, null, null, null, null, null, 1],
                    [3600 * 24 * 1000, "{MMM} {DD}", null, null, null, null, null, null, 1],
                    [3600 * 1000, "{HH}:{mm}", null, null, null, null, null, null, 1],
                    [60 * 1000, "{HH}:{mm}", null, null, null, null, null, null, 1],
                    [1 * 1000, "{HH}:{mm}:{ss}", null, null, null, null, null, null, 1],
                    [0.001 * 1000, "{HH}:{mm}:{ss}.{fff}", null, null, null, null, null, null, 1],
                ],
            }
        },
        hooks: {
            onSelect: [(e) => emit('rangeSelected', { from: e.from, to: e.to })],
        },
        series: series,
    }
}

onMounted(() => {
    chartSettings.value = getChartSettings('column')
})

</script>