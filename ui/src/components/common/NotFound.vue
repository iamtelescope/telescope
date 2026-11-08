<template>
    <div class="flex items-center justify-center min-h-screen px-8" data-testid="not-found">
        <EmptyState
            :icon="Compass"
            title="Page not found"
            :description="`Nothing lives at ${$route.fullPath}. The link may be old, or the item was renamed or deleted.`"
        >
            <Button as="router-link" to="/" label="Go to Logs" icon="pi pi-home" size="small" />
            <Button
                label="Search"
                icon="pi pi-search"
                size="small"
                severity="secondary"
                outlined
                @click="shell.paletteOpen = true"
            />
        </EmptyState>
    </div>
</template>

<script setup>
import { Button } from 'primevue'
import { Compass } from 'lucide-vue-next'
import EmptyState from '@/components/common/EmptyState.vue'
import { shell } from '@/components/common/shell'
</script>
