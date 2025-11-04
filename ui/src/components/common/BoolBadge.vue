<template>
    <Badge
        :value="value ? trueText || 'Yes' : falseText || 'No'"
        :class="{
            'bool-badge-true': value,
            'bool-badge-false': !value,
        }"
    />
</template>

<script setup>
import { Badge } from 'primevue'

const props = defineProps(['value', 'trueText', 'falseText'])
</script>

<style scoped>
.bool-badge-true {
    background-color: #d1fae5 !important;
    color: #065f46 !important;
    border: 1px solid #a7f3d0 !important;
}

.bool-badge-false {
    background-color: #fecaca !important;
    color: #991b1b !important;
    border: 1px solid #fca5a5 !important;
}

:where(.dark, .dark *) .bool-badge-true {
    background-color: #064e3b !important;
    color: #a7f3d0 !important;
    border: 1px solid #065f46 !important;
}

:where(.dark, .dark *) .bool-badge-false {
    background-color: #7f1d1d !important;
    color: #fca5a5 !important;
    border: 1px solid #991b1b !important;
}
</style>
