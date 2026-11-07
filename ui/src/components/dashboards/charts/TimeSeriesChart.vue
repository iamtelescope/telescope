<template>
    <div ref="wrapper" class="flex flex-col h-full min-h-0">
        <div class="flex-1 min-h-0">
            <YagrChart v-if="settings" :settings="settings" :theme="theme" height="100%" />
        </div>
        <TruncatedHint :truncated="data.truncated" :count="groupsCount" />
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDark } from '@vueuse/core'

import YagrChart from '@/components/common/YagrChart.vue'
import TruncatedHint from '@/components/dashboards/charts/TruncatedHint.vue'
import { getColor } from '@/utils/colors.js'
import { getChartSettings } from '@/utils/chartSettings.js'

const props = defineProps(['data', 'display', 'timeZone', 'groupBy'])
const emit = defineEmits(['rangeSelected'])

const types = { line: 'line', stacked_area: 'area', stacked_bar: 'column' }
const isDark = useDark()
const wrapper = ref(null)
const mounted = ref(false)
const theme = computed(() => (isDark.value ? 'dark' : 'light'))

const groupsCount = computed(() => new Set(props.data.series.map((s) => s.group)).size)

const settings = computed(() => {
    if (!mounted.value) return null
    const series = props.data.series.map((s, idx) => ({
        name: s.name,
        id: `${idx}`,
        data: s.values,
        stack: 'tile',
        color: getColor(s.name),
    }))
    return getChartSettings({
        type: types[props.display],
        timestamps: props.data.timestamps,
        series: series,
        timeZone: props.timeZone,
        theme: theme.value,
        width: wrapper.value.getBoundingClientRect().width,
        nameLabel: props.groupBy || 'Series',
        valueLabel: 'Value',
        escape: true,
        onSelect: (range) => emit('rangeSelected', range),
    })
})

onMounted(() => {
    mounted.value = true
})
</script>
