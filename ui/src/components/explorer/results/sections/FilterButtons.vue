<template>
    <span class="inline-flex gap-0.5">
        <Button
            icon="pi pi-search-plus"
            text
            rounded
            size="small"
            severity="secondary"
            class="!w-6 !h-6 !p-0"
            :aria-label="`Filter ${label}`"
            v-tooltip.top="'Add to filter'"
            @click="add(FlyQLOperator.EQUALS)"
        />
        <Button
            icon="pi pi-search-minus"
            text
            rounded
            size="small"
            severity="secondary"
            class="!w-6 !h-6 !p-0"
            :aria-label="`Exclude ${label}`"
            v-tooltip.top="'Exclude'"
            @click="add(FlyQLOperator.NOT_EQUALS)"
        />
    </span>
</template>

<script setup>
import { Button } from 'primevue'
import { Operator as FlyQLOperator } from 'flyql'

import { useSourceControlsStore } from '@/stores/sourceControls'
import { queryField } from '@/components/explorer/results/sections/rowpanel.js'

const props = defineProps({ path: Array, value: null, label: String })
const store = useSourceControlsStore()

const add = (operator) => store.addQueryExpression(queryField(props.path), operator, props.value)
</script>
