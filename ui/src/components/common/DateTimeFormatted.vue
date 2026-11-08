<template>
    <span v-if="!dt" class="text-surface-400">—</span>
    <time v-else :datetime="dt.toISO()" v-tooltip.top="tooltip">{{ text }}</time>
</template>

<script setup>
import { computed } from 'vue'
import { formatDateTime, formatRelative, toDateTime } from '@/components/common/datetime'

// relative: show "5 minutes ago" and keep the full date in the tooltip.
const props = defineProps({
    value: { type: [String, Number, Date, Object], default: null },
    relative: { type: Boolean, default: false },
})

const dt = computed(() => toDateTime(props.value))
const text = computed(() => (props.relative ? formatRelative(dt.value) : formatDateTime(dt.value)))
const tooltip = computed(() =>
    props.relative
        ? formatDateTime(dt.value)
        : `${formatRelative(dt.value)} · ${formatDateTime(dt.value, { zone: 'UTC' })}`,
)
</script>
