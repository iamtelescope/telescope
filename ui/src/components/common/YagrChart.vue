<template>
    <div :style="{ height: typeof height === 'number' ? `${height}px` : height }">
        <div ref="root" class="w-full h-full"></div>
    </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

import Yagr from '@gravity-ui/yagr'

const props = defineProps({
    settings: Object,
    theme: String,
    height: { type: [Number, String], default: 200 },
})
const root = ref(null)
let chart = null

// Yagr's adaptive size already observes the root element and reflows on resize.
onMounted(() => {
    chart = new Yagr(root.value, props.settings)
})

watch(props, () => {
    chart.dispose()
    chart = new Yagr(root.value, props.settings)
    chart.setTheme(props.theme)
})

onBeforeUnmount(() => {
    chart?.dispose()
    chart = null
})
</script>
