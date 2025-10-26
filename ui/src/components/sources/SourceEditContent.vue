<template>
    <DataView :loadings="[connectionsLoading]" :errors="[connectionsError]">
        <SourceWizard :source="source" :connections="connections" />
    </DataView>
</template>

<script setup>
import { useGetUsableConnections } from '@/composables/connections/useConnectionService'
import DataView from '@/components/common/DataView.vue'
import SourceWizard from '@/components/sources/wizard/SourceWizard.vue'

// This component only loads when user has edit permission on the source
// So connections will only be fetched for authorized users
defineProps({
    source: {
        type: Object,
        required: true,
    },
})

const { connections, error: connectionsError, loading: connectionsLoading } = useGetUsableConnections()
</script>
