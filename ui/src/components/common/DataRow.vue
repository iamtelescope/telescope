<template>
    <div class="flex flex-row items-center" :class="{ bordered: showBorder, 'pb-2 pt-2': !noPadding }">
        <div class="datarow-name font-bold max-w-190 min-w-190" :class="nameClass">
            {{ name }}
        </div>
        <div v-if="value" class="datarow-value w-full">
            {{ value }}
        </div>
        <div v-else><slot></slot></div>
    </div>
</template>
<script setup>
import { ref} from 'vue'

import { getDefaultIfUndefined } from '@/utils/utils';

const props = defineProps(['name', 'value', 'showBorder', 'nameClass', 'noPadding'])
const showBorder = ref(getDefaultIfUndefined(props.showBorder, true))
const padded = ref(getDefaultIfUndefined(props.noPadding, false))
</script>

<style scoped>
.bordered {
    border-bottom: 1px solid #e2e8f0;
}
</style>