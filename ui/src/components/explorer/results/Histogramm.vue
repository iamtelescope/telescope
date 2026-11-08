<template>
    <div>
        <div class="flex flex-row">
            <SelectButton
                v-model="chartType"
                :defaultValue="chartDefaultType"
                :allowEmpty="false"
                :options="chartTypeOptions"
                @change="onChartTypeSelect"
                aria-label="Chart type"
            >
                <template #option="slotProps">
                    <font-awesome-icon
                        :icon="`fa-solid fa-chart-${slotProps.option}`"
                        :aria-label="`${slotProps.option} chart`"
                        :title="`${slotProps.option[0].toUpperCase()}${slotProps.option.slice(1)} chart`"
                    />
                </template>
            </SelectButton>
            <div class="flex items-center pl-4">
                <span class="text-gray-500 dark:text-gray-400">group by:</span>
                <span class="pl-2 font-medium">{{ groupByLabel || '–' }}</span>
            </div>
            <div class="flex-1"></div>
            <div class="flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
                <span v-if="hasRowsShade" class="inline-flex items-center gap-1" data-testid="histogram-rows-legend">
                    <span class="inline-block w-3 h-3 rounded-sm" :style="{ backgroundColor: shadeColor }"></span>
                    rows listed below
                </span>
                <span class="hidden md:inline"
                    ><i class="pi pi-arrows-h text-[10px]"></i> drag across the chart to zoom</span
                >
                <Button
                    v-if="canUndoZoom"
                    label="Undo zoom"
                    icon="pi pi-undo"
                    size="small"
                    text
                    @click="emit('undoZoom')"
                    data-testid="histogram-undo-zoom"
                />
            </div>
        </div>
        <div class="flex flex-col" id="histogramm" data-testid="explorer-histogram">
            <YagrChart v-if="chartSettings" :theme="theme" :settings="chartSettings" />
        </div>
    </div>
</template>
<script setup>
import { ref, onMounted, computed, watch } from 'vue'

import { SelectButton, Button } from 'primevue'

import { useDark } from '@vueuse/core'

import YagrChart from '@/components/common/YagrChart.vue'

import { getColor } from '@/utils/colors.js'
import { getChartSettings as buildChartSettings } from '@/utils/chartSettings.js'
import { useMarkers, markerPlotLines } from '@/composables/useMarkers.js'

const props = defineProps(['source', 'stats', 'rows', 'timeZone', 'groupByLabel', 'canUndoZoom'])
const emit = defineEmits(['rangeSelected', 'undoZoom'])

const chartSettings = ref(null)
const chartDefaultType = ref('column')
const chartTypeOptions = ref(['column', 'area', 'line'])
const isDark = useDark()
const selectedChartType = ref(null)
const markers = useMarkers(() => ({
    source: props.source,
    from: props.stats?.timestamps?.[0],
    to: props.stats?.timestamps?.[props.stats.timestamps.length - 1],
}))

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

// Neutral shading for the span of the listed rows, visible on both themes.
const shadeColor = computed(() => (isDark.value ? 'rgba(148, 163, 184, 0.22)' : 'rgba(71, 85, 105, 0.14)'))
const hasRowsShade = computed(
    () => props.rows && props.rows.length > 1 && props.stats && props.rows.length < props.stats.total,
)

const calcPlotLines = () => {
    let plotLines = []
    if (props.rows && props.rows.length > 1 && props.stats) {
        let oldest_row = props.rows[props.rows.length - 1].time.unixtime
        let newest_row = props.rows[0].time.unixtime
        if (props.rows.length < props.stats.total) {
            plotLines = [{ value: [newest_row, oldest_row], color: shadeColor.value }]
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
        plotLines: [...calcPlotLines(), ...markerPlotLines(markers.value)],
        onSelect: (range) => emit('rangeSelected', range),
    })
}

onMounted(() => {
    chartSettings.value = getChartSettings(chartType.value)
})

watch([props, markers], () => {
    chartSettings.value = getChartSettings(chartType.value)
})
</script>
