<template>
    <div>
        <div class="flex flex-row">
            <SelectButton
                v-model="chartType"
                :defaultValue="chartDefaultType"
                :allowEmpty="false"
                :options="chartTypeOptions"
                @change="onChartTypeSelect"
            >
                <template #option="slotProps">
                    <font-awesome-icon :icon="`fa-solid fa-chart-${slotProps.option}`" />
                </template>
            </SelectButton>
            <div class="flex items-center pl-4">
                <span class="text-gray-500">group by:</span>
                <span class="pl-2 font-medium">{{ groupByLabel || '–' }}</span>
            </div>
        </div>
        <div class="flex flex-col" id="histogramm">
            <YagrChart v-if="chartSettings" :theme="theme" :settings="chartSettings" />
        </div>
    </div>
</template>
<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { format } from 'date-fns'
import uPlot from 'uplot'

import { SelectButton } from 'primevue'

import { useDark } from '@vueuse/core'

import YagrChart from '@/components/common/YagrChart.vue'

import { getColor } from '@/utils/colors.js'

const props = defineProps(['source', 'stats', 'rows', 'groupByLabel'])
const emit = defineEmits(['rangeSelected'])
const chartSettings = ref(null)
const chartDefaultType = ref('column')
const chartTypeOptions = ref(['column', 'area', 'line'])
const isDark = useDark()
const selectedChartType = ref(null)

const onChartTypeSelect = (e) => {
    let type = e.value ?? chartDefaultType.value
    selectedChartType.value = type
    chartSettings.value = getChartSettings(type)
}

const chartType = computed(() => {
    return selectedChartType.value ?? chartDefaultType.value
})

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
        let max = 15

        let columns = props.stats.timestamps.length
        if (columns < 150) {
            columns = 150
        }

        // left-rigth padding of graph
        let padding = 70
        // spaces between columns
        let totalSpacing = columns + 2

        // calculate expected graph width
        let width = document.getElementById('histogramm').getBoundingClientRect().width - padding - totalSpacing

        let min = Math.floor(width / columns / 2)
        if (min <= 0 || columns > 200) {
            min = 1
        }
        if (min > max) {
            min = max
        }
        let factor = 0.3
        options['size'] = [factor, max, min]
        options['radius'] = 0.2
    }
    return options
}

const calcPlotLines = () => {
    let plotLines = []
    if (props.rows && props.rows.length > 1) {
        let oldest_row = props.rows[props.rows.length - 1].time.unixtime
        let newest_row = props.rows[0].time.unixtime
        if (props.rows.length < props.stats.total) {
            let color = 'rgba(0, 0, 255, 0.2)'
            let plotSize = newest_row - oldest_row
            let totalSize = props.stats.timestamps[props.stats.timestamps.length - 1] - props.stats.timestamps[0]
            let plotPercent = (plotSize * 100) / totalSize

            if (plotPercent == 0) {
                color = 'rgba(0, 0, 255, 0.2)'
            }
            plotLines = [
                {
                    value: [newest_row, oldest_row],
                    color: color,
                },
            ]
        }
    }
    return plotLines
}

const tooltipRender = (data) => {
    let html = `<div class="font-medium pb-2 dark:text-neutral-300">${format(uPlot.tzDate(new Date(data.x), 'UTC'), 'yyyy-MM-dd HH:mm:ss')}</div><table class='p-0 m-0 w-full'>`
    let label = props.groupByLabel
    if (!label) {
        label = 'Name'
    }
    html += `<tr class="pb-2"><th></th><th class="text-left pb-2 pr-2 dark:text-neutral-300">${label}</th><th class="text-right pb-2 dark:text-neutral-300">Count</th></tr>`
    let i = 0
    for (const item of data.scales[0].rows.sort((a, b) => b.originalValue - a.originalValue)) {
        if (item.dataValue == 0 && i > 25) {
            continue
        }
        html += '<tr>'
        html += `<td class="p-0 border-0 pr-2"><i style="color:${item.color};" class="pi pi-circle-fill"></i></td>`
        html += `<td class="p-0 border-0 pr-2">${item.name}</td>`
        html += `<td class="p-0 border-0 text-right"> ${item.dataValue}</td>`
        html += '</tr>'
        i++
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

    for (const [key, value] of Object.entries(props.stats.data)) {
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
        timeline: props.stats.timestamps,
        timeMultiplier: 1,
        legend: {
            show: true,
        },
        adaptive: true,
        height: 800,
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
                    [3600 * 24 * 365 * 1000, '{YYYY} {MMM}', null, null, null, null, null, null, 1],
                    [3600 * 24 * 28 * 1000, '{MMM}', null, null, null, null, null, null, 1],
                    [3600 * 24 * 1000, '{MMM} {DD}', null, null, null, null, null, null, 1],
                    [3600 * 1000, '{HH}:{mm}', null, null, null, null, null, null, 1],
                    [60 * 1000, '{HH}:{mm}', null, null, null, null, null, null, 1],
                    [1 * 1000, '{HH}:{mm}:{ss}', null, null, null, null, null, null, 1],
                    [0.001 * 1000, '{HH}:{mm}:{ss}.{fff}', null, null, null, null, null, null, 1],
                ],
            },
        },
        hooks: {
            onSelect: [(e) => emit('rangeSelected', { from: e.from, to: e.to })],
        },
        series: series,
        editUplotOptions: (opts) => {
            opts.tzDate = (ts) => uPlot.tzDate(new Date(ts), 'Etc/UTC')
            return opts
        },
    }
}

onMounted(() => {
    chartSettings.value = getChartSettings(chartType.value)
})

watch(props, () => {
    chartSettings.value = getChartSettings(chartType.value)
})
</script>
