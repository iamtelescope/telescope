<template>
    <Button
        size="small"
        :severity="alert.silenced ? 'warn' : 'secondary'"
        outlined
        :icon="alert.silenced ? 'pi pi-volume-off' : 'pi pi-volume-up'"
        :label="compact ? undefined : alert.silenced ? `Silenced until ${until}` : 'Silence'"
        :aria-label="alert.silenced ? 'Silenced' : 'Silence'"
        v-tooltip.top="compact && alert.silenced ? `Silenced until ${until} by ${alert.silenced.by?.username}` : null"
        :loading="busy"
        :data-testid="`alert-silence-${alert.id}`"
        @click="(e) => menu.toggle(e)"
    />
    <Menu ref="menu" :model="items" :popup="true" />
</template>

<script setup>
// Silence for a preset time, as HyperDX AlertsPage "Ack", for those who may edit; history keeps being written.
import { ref, computed } from 'vue'
import { DateTime } from 'luxon'
import { Button, Menu, useToast } from 'primevue'

import { AlertService } from '@/features/alerts/service.js'

const props = defineProps({ alert: Object, compact: Boolean })
const emit = defineEmits(['changed'])
const srv = new AlertService()
const toast = useToast()
const menu = ref()
const busy = ref(false)
const PRESETS = [
    ['30 minutes', { minutes: 30 }],
    ['1 hour', { hours: 1 }],
    ['4 hours', { hours: 4 }],
    ['1 day', { days: 1 }],
    ['1 week', { weeks: 1 }],
]

const until = computed(() =>
    props.alert.silenced ? DateTime.fromISO(props.alert.silenced.until).toFormat('MMM d, HH:mm') : '',
)
const run = async (call) => {
    busy.value = true
    const response = await call()
    busy.value = false
    response.sendToast(toast)
    if (response.result) emit('changed', response.data)
}
const items = computed(() => [
    ...PRESETS.map(([label, duration]) => ({
        label: `For ${label}`,
        command: () => run(() => srv.silence(props.alert.id, DateTime.now().plus(duration).toISO())),
    })),
    ...(props.alert.silenced
        ? [
              { separator: true },
              { label: 'Unsilence', icon: 'pi pi-volume-up', command: () => run(() => srv.unsilence(props.alert.id)) },
          ]
        : []),
])
</script>
