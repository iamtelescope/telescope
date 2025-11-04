<template>
    <div class="flex flex-row items-center dark:border-neutral-700" :class="[{ 'border-b': showBorder }, paddings]">
        <div class="font-medium max-w-[190px] min-w-[190px] pl-4" :class="nameClass" v-if="name">
            {{ name }}
        </div>
        <div v-if="value" class="w-full font-thin" :class="valueClass">
            <span v-if="isDatetime">
                <DateTimeFormatted :value="value" />
            </span>
            <span v-else>{{ value }}</span>
            <Copy class="pl-2" :value="value" v-if="copy" />
        </div>
        <div v-else>
            <slot></slot>
        </div>
    </div>
</template>
<script setup>
import { computed, ref } from 'vue'
import Copy from '@/components/common/Copy.vue'
import DateTimeFormatted from '@/components/common/DateTimeFormatted.vue'

import { getDefaultIfUndefined } from '@/utils/utils'

const props = defineProps(['name', 'value', 'showBorder', 'nameClass', 'valueClass', 'size', 'copy', 'isDatetime'])

const copy = ref(getDefaultIfUndefined(props.copy, true))

const showBorder = ref(getDefaultIfUndefined(props.showBorder, true))

const paddings = computed(() => {
    let size = props.size || 'normal'
    if (size === 'small') {
        return 'pt-1 pb-1'
    } else if (size === 'normal') {
        return 'pt-2 pb-2'
    } else if (size === 'large') {
        return 'pt-3 pb-3'
    } else {
        return 'pt-0 pb-0'
    }
})
</script>
