<template>
    <div style="height: 200px;">
        <div id="yaggrChart" class="w-full h-full"></div>
    </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

import Yagr from '@gravity-ui/yagr'

const props = defineProps(['settings', 'theme'])
const chart = ref(null)

onMounted(() => {
    chart.value = new Yagr(yaggrChart, props.settings)
})

watch(props, () => {
    console.log(props.settings.chart.appearance)
    chart.value.dispose()
    chart.value = new Yagr(yaggrChart, props.settings)
    chart.value.setTheme(props.theme)

})
</script>