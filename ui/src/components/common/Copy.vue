<template>
    <UseClipboard :copiedDuring="300" v-slot="{ copy, copied, isSupported }" :source="value">
        <i
            v-if="isSupported"
            class="pi pi-copy copy-button cursor-pointer"
            @click="copy()"
            :class="{ faded: copied }"
        />
    </UseClipboard>
</template>

<script setup>
import { UseClipboard } from '@vueuse/components'

const props = defineProps(['value'])
</script>

<style scoped>
.copy-button.faded {
    opacity: 0.1;
    transition: opacity 0.1s ease;
}
</style>
