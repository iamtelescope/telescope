<template>
    <div
        class="flex flex-row items-center dark:border-neutral-700"
        :class="{ 'border-b': showBorder, 'pb-2 pt-2': !noPadding }"
    >
        <div class="font-medium max-w-190 min-w-190" :class="nameClass">
            {{ name }}
        </div>
        <div v-if="value" class="datarow-value w-full">
            {{ value }}
        </div>
        <div v-else>
            <slot></slot>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'

import { getDefaultIfUndefined } from '@/utils/utils'

const props = defineProps(['name', 'value', 'showBorder', 'nameClass', 'noPadding'])
const showBorder = ref(getDefaultIfUndefined(props.showBorder, true))
</script>
