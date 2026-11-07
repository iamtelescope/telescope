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
        <div class="flex flex-col" id="histogramm" data-testid="explorer-histogram">
            <YagrChart v-if="chartSettings" :theme="theme" :settings="chartSettings" />
        </div>
    </div>
</template>
<script setup>
import { ref, onMounted, computed, watch } from 'vue'

import { SelectButton } from 'primevue'

import { useDark } from '@vueuse/core'

import YagrChart from '@/components/common/YagrChart.vue'

import { getColor } from '@/utils/colors.js'
import { getChartSettings as buildChartSettings } from '@/utils/chartSettings.js'

const props = defineProps(['source', 'stats', 'rows', 'timeZone', 'groupByLabel'])
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

const calcPlotLines = () => {
    let plotLines = []
    if (props.rows && props.rows.length > 1 && props.stats) {
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

const getChartSettings = (type) => {
    // Guard against undefined stats
    if (!props.stats || !props.stats.data) {
        return null
    }

    const series = []
    for (const [key, value] of Object.entries(props.stats.data)) {
        series.push({
            name: key,
            data: value,
            stack: 'severity',
            id: key,
            color: getColor(key),
        })
    }
    return buildChartSettings({
        type: type,
        timestamps: props.stats.timestamps,
        series: series,
        timeZone: props.timeZone,
        theme: theme.value,
        width: document.getElementById('histogramm').getBoundingClientRect().width,
        nameLabel: props.groupByLabel || 'Name',
        plotLines: calcPlotLines(),
        onSelect: (range) => emit('rangeSelected', range),
    })
}

onMounted(() => {
    chartSettings.value = getChartSettings(chartType.value)
})

watch(props, () => {
    chartSettings.value = getChartSettings(chartType.value)
})
</script>
