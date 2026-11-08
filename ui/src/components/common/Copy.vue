<template>
    <UseClipboard :copiedDuring="1200" v-slot="{ copy, copied, isSupported }" :source="value">
        <button
            v-if="isSupported"
            type="button"
            class="copy-button inline-flex items-center align-middle rounded text-surface-500 hover:text-primary dark:text-surface-400"
            :aria-label="copied ? 'Copied' : label"
            v-tooltip.top="copied ? 'Copied' : label"
            @click.stop="copy()"
        >
            <i :class="copied ? 'pi pi-check text-green-600 dark:text-green-400' : 'pi pi-copy'" aria-hidden="true"></i>
        </button>
    </UseClipboard>
</template>

<script setup>
import { UseClipboard } from '@vueuse/components'

defineProps({
    value: { default: '' },
    label: { type: String, default: 'Copy to clipboard' },
})
</script>
