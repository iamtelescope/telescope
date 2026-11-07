<template>
    <div class="flex flex-wrap gap-2 px-4 pb-2" data-testid="row-copy-actions">
        <Button
            label="Copy JSON"
            icon="pi pi-copy"
            size="small"
            severity="secondary"
            outlined
            data-testid="row-copy-json"
            @click="copyText(JSON.stringify(row.data, null, 2), 'Row JSON copied')"
        />
        <Button
            label="Copy link"
            icon="pi pi-link"
            size="small"
            severity="secondary"
            outlined
            data-testid="row-copy-link"
            @click="copyText(link, 'Link copied')"
        />
    </div>
</template>

<script>
import { isEnriched } from '@/components/explorer/results/sections/rowpanel.js'

// Row.vue renders this only when available(source, row) is true.
export function available(source, row) {
    return isEnriched(source) && !!row
}
</script>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useClipboard } from '@vueuse/core'
import { Button, useToast } from 'primevue'

import { rowLinkQuery } from '@/components/explorer/results/sections/rowpanel.js'

const props = defineProps(['source', 'row', 'timeZone'])

const router = useRouter()
const toast = useToast()
// legacy: copy through execCommand on plain-http hosts, where navigator.clipboard is missing.
const { copy } = useClipboard({ legacy: true })

// The explorer within a second of the row, narrowed to its trace and span ids when it has them.
const link = computed(() => {
    const { from, to, query } = rowLinkQuery(props.source, props.row)
    const q = { from, to, timeZone: props.timeZone }
    if (query) q.query = query
    const href = router.resolve({ name: 'explore', params: { sourceSlug: props.source.slug }, query: q }).href
    return new URL(href, window.location.origin).href
})

const copyText = async (text, detail) => {
    try {
        await copy(text)
        toast.add({ severity: 'success', summary: 'Copied', detail, life: 2000 })
    } catch {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to copy to clipboard', life: 6000 })
    }
}
</script>
